"""Responsive, keyboard and spoken-review checks in headless Chromium."""
from __future__ import annotations

import json
import re
import socket
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from playwright.sync_api import expect, sync_playwright

from backend import logger, main, state

VIEWPORTS = [(390, 844), (768, 1024), (1440, 900)]
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def app_url(tmp_path_factory):
    """Serve the real app on an ephemeral port and shut it down after the browser tests."""
    logs = tmp_path_factory.mktemp("a11y")
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(logger, "LOG_FILE", logs / "pipeline.jsonl")
        patch.setattr(logger, "CONV_FILE", logs / "turns.jsonl")
        patch.setattr(state, "_OTP_SESSIONS", {})
        patch.setattr(state, "_REQUEST_HISTORY", list(state.list_request_history()))
        patch.setattr(main, "cloud_llm", lambda: None)
        patch.setattr(main, "_read_env_value", lambda name, default="": default)
        patch.setattr(main, "probe_local_llm", lambda: {
            "available": False, "provider": "offline-tanglish-engine",
            "active_model": "deterministic-tanglish-v1", "models": [],
        })
        patch.setattr("backend.agent_workflow.chat_backends", lambda mode: ())
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
            server = uvicorn.Server(uvicorn.Config(main.app, log_level="error", timeout_graceful_shutdown=3))
            thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
            thread.start()
            try:
                deadline = time.monotonic() + 5
                while thread.is_alive() and not server.started and time.monotonic() < deadline:
                    time.sleep(.025)
                assert server.started, "The local app did not start"
                yield f"http://127.0.0.1:{port}"
            finally:
                server.should_exit = True
                thread.join(timeout=5)
                assert not thread.is_alive(), "The local app did not shut down"


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as playwright:
        instance = playwright.chromium.launch()
        try:
            yield instance
        finally:
            instance.close()


@pytest.fixture
def open_page(browser):
    pages = []

    def make(url, width=390, height=844, setup=None):
        page = browser.new_page(viewport={"width": width, "height": height}, reduced_motion="reduce")
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda entry: errors.append(entry.text) if entry.type == "error" else None)
        pages.append((page, errors))
        if setup:
            setup(page)
        response = page.goto(url)
        if response:
            assert response.ok
        return page

    yield make
    for page, _ in pages:
        page.close()
    assert [error for _, errors in pages for error in errors] == []


def contrast_ratio(locator):
    return locator.evaluate("""element => {
        const luminance = color => {
            const rgb = color.match(/\\d+/g).slice(0, 3).map(Number);
            const linear = rgb.map(channel => {
                const value = channel / 255;
                return value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4;
            });
            return .2126 * linear[0] + .7152 * linear[1] + .0722 * linear[2];
        };
        const style = getComputedStyle(element);
        const values = [luminance(style.color), luminance(style.backgroundColor)];
        return (Math.max(...values) + .05) / (Math.min(...values) + .05);
    }""")


def assert_layout(page, width):
    assert page.evaluate("document.documentElement.scrollWidth") == width
    orb = page.get_by_role("button", name=re.compile("பேசுங்க.*Speak"))
    bounds = orb.bounding_box()
    assert bounds["width"] >= 140 and bounds["height"] >= 140
    assert contrast_ratio(orb) >= 4.5
    for button in page.locator(".call-dock button").all():
        assert button.bounding_box()["height"] >= 56
        assert contrast_ratio(button) >= 4.5

    composer = page.locator("#secondaryControls")
    assert composer.is_visible() == (width >= 640)
    left = page.locator("#orbStage").bounding_box()
    right = page.locator(".transcript-stage").bounding_box()
    if width >= 768:
        assert left["x"] + left["width"] <= right["x"]
    else:
        assert left["y"] + left["height"] <= right["y"]


@pytest.mark.parametrize("width,height", VIEWPORTS)
def test_a11y_viewports(app_url, open_page, width, height):
    page = open_page(app_url, width, height)
    expect(page.locator("#engineModePill")).to_have_text("Mode: Offline FSM (No Key Set)")
    expect(page.locator("#voiceKeyNotice")).to_have_attribute("aria-live", "polite")
    expect(page.locator("#agentThread")).to_have_attribute("aria-live", "polite")
    expect(page.locator("#clarityAnnouncement")).to_have_attribute("aria-live", "assertive")
    expect(page.locator("#safetyAlert")).to_have_attribute("aria-live", "assertive")
    assert "wispr" not in page.content().lower()
    assert_layout(page, width)

    theme = page.get_by_role("button", name="Dark mode")
    theme.focus()
    assert theme.evaluate("el => getComputedStyle(el).outlineWidth") == "3px"
    page.keyboard.press("Enter")
    assert theme.get_attribute("aria-pressed") == "true"
    assert page.locator("body").evaluate("el => getComputedStyle(el).backgroundColor") == "rgb(11, 18, 32)"
    assert_layout(page, width)

    if width < 640:
        toggle = page.get_by_role("button", name="Type / Photo (Optional)")
        toggle.click()
        expect(toggle).to_have_attribute("aria-expanded", "true")
    page.locator("#autoSpeakToggleBtn").click()
    page.locator("#voiceInput").fill("Anna Nagar Tower Park streetlight eriyala")
    page.locator("#runAgentBtn").click()
    review_button = page.locator("#hitlApproveBtn")
    review_button.click()
    expect(page.locator("#clarityModalTitle")).to_be_focused()
    for button in page.locator(".clarity-content button:visible").all():
        assert button.bounding_box()["height"] >= 44
    assert page.evaluate("document.documentElement.scrollWidth") == width
    page.keyboard.press("Escape")
    expect(review_button).to_be_focused()


@pytest.mark.parametrize("width,height", VIEWPORTS)
def test_file_preview(open_page, width, height):
    page = open_page((ROOT / "index.html").as_uri(), width, height)
    assert_layout(page, width)


@pytest.mark.parametrize("mode,label", [("local_gpu", "Local Gemma-4"), ("cloud_api", "Cloud API")])
def test_engine_pill_uses_health_mode(app_url, open_page, mode, label):
    def setup(page):
        page.route("**/api/health", lambda route: route.fulfill(json={
            "engine_mode": mode, "optional_keys": {"SARVAM_API_KEY": "configured"},
        }))

    page = open_page(app_url, setup=setup)
    expect(page.locator("#engineModePill")).to_have_text(f"Mode: {label}")
    expect(page.locator("#voiceKeyNotice")).to_be_hidden()


@pytest.mark.parametrize("confirmation_mode", ["modal", "two-turn"])
def test_open_review_keeps_microphone_running_and_accepts_spoken_seal(app_url, open_page, confirmation_mode):
    def setup(page):
        page.add_init_script("""(() => {
            Object.defineProperty(navigator, "mediaDevices", { value: undefined });
            window.webkitSpeechRecognition = window.SpeechRecognition = class {
                constructor() { window.testRecognizer = this; this.active = false; }
                start() { this.active = true; this.onstart?.(); }
                stop() { this.active = false; }
                hear(text) {
                    this.onspeechstart?.();
                    const result = [{ transcript: text, confidence: 1 }];
                    result.isFinal = true;
                    this.onresult({ resultIndex: 0, results: [result] });
                }
            };
        })();""")

    page = open_page(app_url, setup=setup)
    page.locator("#secondaryToggle").click()
    page.locator("#autoSpeakToggleBtn").click()
    page.locator("#startCallBtn").click()
    street = "Anna Nagar Tower Park" if confirmation_mode == "modal" else "Anna Arch IIIrd Ave"
    page.evaluate("phrase => testRecognizer.hear(phrase)", street + " streetlight eriyala")
    page.locator("#hitlApproveBtn").click()
    expect(page.locator("#clarityModalTitle")).to_be_focused()
    assert page.evaluate("testRecognizer.active")
    expect(page.locator("#muteMicBtn")).to_have_attribute("aria-pressed", "false")
    page.locator("#otpSendBtn").click()
    page.locator("#otpVerifyBtn").click()
    expect(page.locator("#otpStatusLabel")).to_contain_text("Verified")
    if confirmation_mode == "modal":
        page.locator("#modalOkBtn").click()
    page.locator("#voiceInput").fill("Confirm")
    page.locator("#runAgentBtn").click()
    expect(page.locator("#dispatchSection")).to_be_hidden()
    if confirmation_mode == "two-turn":
        page.evaluate("testRecognizer.hear('Confirm, Confirm')")
        expect(page.locator("#toastText")).to_have_text("Say one confirmation per turn.")
        expect(page.locator("#dispatchSection")).to_be_hidden()
        page.evaluate("testRecognizer.hear('Confirm')")
        expect(page.locator("#agentThread")).to_contain_text("First confirmation received.")
        expect(page.locator("#dispatchSection")).to_be_hidden()
    page.evaluate("testRecognizer.hear('Confirm')")
    expect(page.locator("#dispatchSection")).to_be_visible()


def test_workflow_renders_display_text_and_sends_tamil_to_speech(app_url, open_page):
    def setup(page):
        page.route("**/api/tts", lambda route: route.fulfill(status=204))
        page.add_init_script("""(() => {
            speechSynthesis.speak = utterance => setTimeout(() => utterance.onend?.(), 0);
        })();""")

    page = open_page(app_url, setup=setup)
    page.locator("#secondaryToggle").click()
    page.locator("#voiceInput").fill("Anna Nagar Tower Park streetlight eriyala")
    with page.expect_response("**/api/workflow/turn") as response, page.expect_request("**/api/tts") as speech:
        page.locator("#runAgentBtn").click()
    workflow = response.value.json()
    assert workflow["tts_text"] != workflow["display_text"]
    expect(page.locator("#agentThread")).to_contain_text(workflow["display_text"])
    assert speech.value.post_data_json["text"] == workflow["tts_text"]
    page.locator("#voiceInput").fill("gas leak")
    page.locator("#runAgentBtn").click()
    expect(page.locator("#safetyAlert a")).to_have_attribute("href", "tel:1906")
    expect(page.locator("#dispatchSection")).to_be_hidden()


def install_test_recognizer(page):
    page.add_init_script("""(() => {
        Object.defineProperty(navigator, 'mediaDevices', {value: undefined});
        window.SpeechRecognition = class {
            constructor() { window.testRecognizer = this; }
            start() {}
            stop() {}
            hear(text, final = true) {
                const result = [{transcript: text, confidence: 1}];
                result.isFinal = final;
                this.onresult({resultIndex: 0, results: [result]});
            }
        };
    })();""")


@pytest.mark.parametrize("pending", ["workflow/turn", "tts"])
def test_recognized_interruption_aborts_pending_fetch(app_url, open_page, pending):
    def init(page):
        install_test_recognizer(page)
        page.add_init_script("""(() => {
            const pending = __PENDING__;
            window.voiceRequests = [];
            const realFetch = window.fetch.bind(window);
            window.fetch = (url, options = {}) => {
                if (url === '/api/tts' && (pending !== 'tts' || !window.holdTts || voiceRequests.length)) {
                    return Promise.resolve(new Response(null, {status: 204}));
                }
                if (url !== '/api/' + pending || voiceRequests.length) return realFetch(url, options);
                const record = {aborted: false};
                voiceRequests.push(record);
                return new Promise((resolve, reject) => {
                    options.signal?.addEventListener('abort', () => {
                        record.aborted = true;
                        reject(options.signal.reason);
                    }, {once: true});
                });
            };
            speechSynthesis.speak = utterance => setTimeout(() => utterance.onend?.(), 0);
        })();""".replace("__PENDING__", json.dumps(pending)))

    page = open_page(app_url, setup=init)
    page.locator("#startCallBtn").click()
    page.evaluate("""() => {
        window.holdTts = true;
        testRecognizer.hear('Tower Park streetlight eriyala');
    }""")
    page.wait_for_function("voiceRequests.length === 1")
    page.evaluate("testRecognizer.hear('seri ok')")
    assert not page.evaluate("voiceRequests[0].aborted")
    assert page.evaluate("""() => {
        const start = performance.now();
        testRecognizer.hear('wait Anna Arch', false);
        return voiceRequests[0].aborted && performance.now() - start < 150;
    }""")
    page.evaluate("testRecognizer.hear('wait Anna Arch streetlight eriyala')")
    expect(page.locator("#agentThread")).to_contain_text("Ward 102")


def test_short_webspeech_fragment_waits_for_complete_utterance(app_url, open_page):
    page = open_page(app_url, setup=install_test_recognizer)
    page.locator("#secondaryToggle").click()
    page.locator("#autoSpeakToggleBtn").click()
    page.locator("#startCallBtn").click()
    page.clock.install()
    page.evaluate("testRecognizer.hear('ஸ்ட்ர', false)")
    page.clock.run_for(1750)
    expect(page.locator("#agentThread")).not_to_contain_text("ஸ்ட்ர")
    with page.expect_request("**/api/workflow/turn") as request:
        page.evaluate("testRecognizer.hear('ஸ்ட்ரீட் லைட் எரியல')")
    assert request.value.post_data_json["utterance"] == "ஸ்ட்ரீட் லைட் எரியல"


@pytest.mark.parametrize("preview", [False, True], ids=["http", "file"])
def test_transliterated_complaint_keeps_issue_until_ward_is_verified(app_url, open_page, preview):
    url = (ROOT / "index.html").as_uri() if preview else app_url
    page = open_page(url)
    page.locator("#secondaryToggle").click()
    page.locator("#autoSpeakToggleBtn").click()

    def submit(text):
        page.locator("#voiceInput").fill(text)
        page.locator("#runAgentBtn").click()

    submit("இல்ல இல்ல ஸ்ட்ரீட் லைட் வந்து தெளிவா எரியல")
    expect(page.locator("#particularsStrip")).to_contain_text("Streetlight")
    expect(page.locator("#hitlApproveBtn")).to_be_hidden()
    submit("நான் வந்து சோழிங்கநல்லூர் தாண்டி நாவலூர்ல இருக்கேன், மெரினா மாலை ஆப்போசிட்ல")
    expect(page.locator("#particularsStrip")).to_contain_text("மெரினா மாலை")
    expect(page.locator("#agentThread")).to_contain_text("verify its ward")
    expect(page.locator("#hitlApproveBtn")).to_be_hidden()
    submit("இல்ல, அண்ணா ஆர்ச் பக்கத்துல")
    expect(page.locator("#particularsStrip")).to_contain_text("Ward 102")
    expect(page.locator("#hitlApproveBtn")).to_be_visible()


@pytest.mark.parametrize("preview", [False, True], ids=["http", "file"])
@pytest.mark.parametrize("native_tamil", [False, True], ids=["missing-voice", "unusable-voice"])
def test_tamil_speech_without_a_working_tamil_voice(app_url, open_page, preview, native_tamil):
    def setup(page):
        install_test_recognizer(page)
        page.add_init_script("""(() => {
            const voices = [{lang: 'en-US', name: 'Desktop English'}];
            if (HAS_TAMIL) voices.push({lang: 'ta-IN', name: 'Unavailable Tamil'});
            speechSynthesis.getVoices = () => voices;
            window.SpeechSynthesisUtterance = class {
                constructor(text) { this.text = text; }
            };
            speechSynthesis.speak = utterance => setTimeout(() => {
                if (utterance.lang.startsWith('ta')) utterance.onerror?.({error: 'language-unavailable'});
                else utterance.onend?.();
            }, 0);
            window.playedVoiceClips = [];
            const play = HTMLMediaElement.prototype.play;
            HTMLMediaElement.prototype.play = function () {
                const asset = this.src.includes('/assets/voice/') ? new URL(this.src).pathname.split('/').pop() : null;
                return play.call(this).then(() => {
                    if (asset) playedVoiceClips.push(asset);
                });
            };
        })();""".replace("HAS_TAMIL", json.dumps(native_tamil)))
        if not preview:
            page.route("**/api/tts", lambda route: route.fulfill(status=204))

    page = open_page((ROOT / "index.html").as_uri() if preview else app_url, setup=setup)
    page.locator("#startCallBtn").click()
    page.wait_for_function("playedVoiceClips.includes('greeting.mp3')", timeout=2000)
    page.evaluate("testRecognizer.hear('சாரி நீங்க பேசுறது கேக்கல')")
    page.wait_for_function("playedVoiceClips.includes('triage.mp3')", timeout=2000)
    page.locator("#secondaryToggle").click()
    page.get_by_role("button", name="EN", exact=True).click()
    page.evaluate("playedVoiceClips.length = 0")
    page.locator("#quickVoiceTestBtn").click()
    page.wait_for_function("playedVoiceClips.includes('greeting.mp3')", timeout=2000)

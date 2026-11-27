import { useEffect, useRef, useState } from "react";
import { Mic, MicOff, Volume2, ShieldCheck, Send, CheckCircle2, RotateCcw } from "lucide-react";
import { RiverOrb, type OrbState } from "../components/RiverOrb";
import { LiveWaveform } from "../components/LiveWaveform";

interface HealthInfo {
  status: string;
  voice_mode: string;
  engine_mode: string;
  store_backend: string;
  vercel_region: string;
  sarvam_stt: boolean;
  sarvam_tts: boolean;
  pregenerated_prompts: number;
}

interface VoiceOption {
  id: string;
  label: string;
  lang?: string;
}

interface TurnResponse {
  fsm_state: string;
  state_code: string;
  model: string;
  latency_ms: number;
  vad?: { action?: string; kind?: string };
  aadhaar_blocked?: boolean;
  pii_masked?: boolean;
  complaint_version?: number;
  text_contract?: { raw_asr?: string; normalized_text?: string };
  analysis?: Record<string, unknown>;
  slots?: Record<string, unknown>;
  cooldown?: Record<string, unknown>;
  preview_packet?: PreviewPacket | null;
  reply?: string;
  display_text?: string;
  tts_text?: string;
  clauses?: string[];
  tool_trace?: Array<Record<string, unknown>>;
}

interface PreviewPacket {
  preview_id: string;
  schema: string;
  complaint_version: number;
  ready_for_portal: boolean;
  missing_fields: string[];
  outbound_gov_requests: boolean;
  notice_en: string;
  notice_ta: string;
  fields: Record<string, unknown>;
}

const BACKCHANNEL_RE = /^(mm+|mmm+|hmm+|seri|sari|aama|ama|ok|okay|haan|ஆமா|சரி)$/i;

const SAMPLE_PROMPTS = [
  "Anna Nagar-la streetlight eriyala",
  "Tower Park back side, Fifth Avenue",
  "Illa, Tower Park illa, Anna Arch pakkam",
  "Navalur Marina Mall opposite-la water stagnation",
  "உறுதி / Confirm",
];

export default function VoiceAgentPage() {
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const [consentGranted, setConsentGranted] = useState<boolean>(true);
  const [orbState, setOrbState] = useState<OrbState>("idle");
  const [listening, setListening] = useState<boolean>(false);
  const [speaking, setSpeaking] = useState<boolean>(false);
  const [inputText, setInputText] = useState<string>("");
  const [voices, setVoices] = useState<VoiceOption[]>([
    { id: "ta-IN-PallaviNeural", label: "Pallavi (ta-IN Neural)" },
    { id: "bulbul:v2", label: "Sarvam Bulbul v2 (ta-IN)" },
  ]);
  const [selectedVoice, setSelectedVoice] = useState<string>("ta-IN-PallaviNeural");
  const [lastTurn, setLastTurn] = useState<TurnResponse | null>(null);
  const [messages, setMessages] = useState<Array<{ role: "user" | "agent"; text: string; meta?: string }>>([]);
  const [clientTtfaMs, setClientTtfaMs] = useState<number | null>(null);

  // OTP + HITL state
  const [phoneMasked, setPhoneMasked] = useState<string>("98XXXXXX10");
  const [otpSessionId, setOtpSessionId] = useState<string>("");
  const [otpDemoHint, setOtpDemoHint] = useState<string>("");
  const [otpCode, setOtpCode] = useState<string>("");
  const [otpVerified, setOtpVerified] = useState<boolean>(false);
  const [modalOk, setModalOk] = useState<boolean>(false);
  const [hitlApproved, setHitlApproved] = useState<boolean>(false);
  const [hitlStatus, setHitlStatus] = useState<string>("");
  const [previewPacket, setPreviewPacket] = useState<PreviewPacket | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const ttsAbortRef = useRef<AbortController | null>(null);
  const recRef = useRef<any>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then((d) => setHealth(d))
      .catch(() => null);

    fetch("/api/tts/voices")
      .then((r) => r.json())
      .then((d) => {
        const list = Array.isArray(d) ? d : d?.voices;
        if (Array.isArray(list) && list.length > 0) {
          setVoices(list);
          setSelectedVoice(list[0].id);
        }
      })
      .catch(() => null);
  }, []);

  function stopPlayback() {
    if (ttsAbortRef.current) {
      ttsAbortRef.current.abort();
      ttsAbortRef.current = null;
    }
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
    }
    setSpeaking(false);
    setOrbState((prev) => (prev === "talking" ? "idle" : prev));
  }

  async function speakText(text: string, turnStartMs?: number) {
    if (!text.trim()) return;
    stopPlayback();
    const ctrl = new AbortController();
    ttsAbortRef.current = ctrl;
    setSpeaking(true);
    setOrbState("talking");

    try {
      const res = await fetch("/api/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, voice: selectedVoice, lang: "ta-IN" }),
        signal: ctrl.signal,
      });
      if (res.status === 204 || !res.ok) {
        setSpeaking(false);
        setOrbState("idle");
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onplay = () => {
        if (turnStartMs) {
          setClientTtfaMs(Math.round(performance.now() - turnStartMs));
        }
      };
      audio.onended = () => {
        URL.revokeObjectURL(url);
        setSpeaking(false);
        setOrbState("idle");
      };
      audio.onerror = () => {
        URL.revokeObjectURL(url);
        setSpeaking(false);
        setOrbState("idle");
      };
      await audio.play();
    } catch {
      setSpeaking(false);
      setOrbState("idle");
    }
  }

  async function submitTurn(rawText: string) {
    const trimmed = rawText.trim();
    if (!trimmed) return;

    // Backchannel immunity during agent speech
    if (speaking && BACKCHANNEL_RE.test(trimmed)) {
      if (audioRef.current) {
        audioRef.current.volume = 0.35;
        setTimeout(() => {
          if (audioRef.current) audioRef.current.volume = 1.0;
        }, 350);
      }
      setMessages((m) => [...m, { role: "user", text: trimmed, meta: "Backchannel (kept playing)" }]);
      return;
    }

    // Real barge-in: stop audio immediately
    if (speaking) {
      stopPlayback();
    }

    const t0 = performance.now();
    setOrbState("thinking");
    setMessages((m) => [...m, { role: "user", text: trimmed }]);
    setInputText("");

    try {
      const res = await fetch("/api/workflow/turn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          utterance: trimmed,
          session_id: "browser",
          state_code: "tn",
          dpdp_consented: consentGranted,
          otp_verified: otpVerified,
        }),
      });
      const data: TurnResponse = await res.json();
      setLastTurn(data);
      if (data.preview_packet) {
        setPreviewPacket(data.preview_packet);
      }
      const replyText = data.display_text || data.reply || "";
      setMessages((m) => [
        ...m,
        {
          role: "agent",
          text: replyText,
          meta: `${data.fsm_state} · v${data.complaint_version ?? 1} · ${Math.round(data.latency_ms ?? 0)} ms`,
        },
      ]);

      const urgency = (data.analysis as any)?.urgency_tier;
      if (urgency === "P1") {
        setOrbState("urgent");
      }
      const speechTarget = data.tts_text || replyText;
      await speakText(speechTarget, t0);
    } catch (err) {
      setOrbState("idle");
      setMessages((m) => [...m, { role: "agent", text: `Error: ${String(err)}` }]);
    }
  }

  function toggleMic() {
    if (listening && recRef.current) {
      recRef.current.stop();
      setListening(false);
      setOrbState("idle");
      return;
    }
    if (!consentGranted) {
      setMessages((m) => [
        ...m,
        { role: "agent", text: "Please grant DPDP voice consent before starting microphone capture." },
      ]);
      return;
    }
    const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRec) {
      setMessages((m) => [
        ...m,
        { role: "agent", text: "Browser SpeechRecognition unavailable; use the Tanglish text box or sample chips." },
      ]);
      return;
    }
    if (speaking) stopPlayback();

    const rec = new SpeechRec();
    rec.lang = "ta-IN";
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onstart = () => {
      setListening(true);
      setOrbState("listening");
    };
    rec.onresult = (ev: any) => {
      const transcript = ev?.results?.[0]?.[0]?.transcript || "";
      setListening(false);
      if (transcript) {
        submitTurn(transcript);
      } else {
        setOrbState("idle");
      }
    };
    rec.onerror = () => {
      setListening(false);
      setOrbState("idle");
    };
    rec.onend = () => {
      setListening(false);
    };
    recRef.current = rec;
    rec.start();
  }

  async function handleSendOtp() {
    const res = await fetch("/api/otp/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone_masked: phoneMasked }),
    });
    const data = await res.json();
    setOtpSessionId(data.otp_session_id || "");
    setOtpDemoHint(data.demo_code || data.code || "Check SMS");
  }

  async function handleVerifyOtp() {
    const res = await fetch("/api/otp/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ otp_session_id: otpSessionId, code: otpCode }),
    });
    const data = await res.json();
    setOtpVerified(Boolean(data.verified));
  }

  async function handleHitlSeal() {
    const slots = (lastTurn?.slots || {}) as Record<string, unknown>;
    const res = await fetch("/api/hitl/seal", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mode: "modal_plus_voice",
        spoken_phrase: "உறுதி / Confirm",
        modal_ok: modalOk,
        otp_session_id: otpSessionId,
        ward: String(slots.ward || "Ward 103"),
        service_id: String(slots.service_id || "streetlight"),
        urgency_tier: String((lastTurn?.analysis as any)?.urgency?.tier || "STANDARD"),
      }),
    });
    const data = await res.json();
    const ok = Boolean(data.sealed || data.approved || data.status === "sealed");
    setHitlApproved(ok);
    setHitlStatus(data.message || (ok ? "HITL Dual-Confirm Sealed" : "Confirmation incomplete"));
  }

  async function handleGeneratePreview() {
    const slots = (lastTurn?.slots || {}) as Record<string, unknown>;
    const landmarkObj = (lastTurn?.analysis as any)?.landmark || {
      name: String(slots.landmark || "Anna Arch pakkam"),
      ward: String(slots.ward || ""),
    };
    const res = await fetch("/api/portal/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        service_id: String(slots.service_id || "streetlight_eb"),
        landmark: landmarkObj,
        summary_text: lastTurn?.display_text || "Streetlight complaint preview",
        urgency_tier: String((lastTurn?.analysis as any)?.urgency?.tier || "STANDARD"),
        complaint_version: lastTurn?.complaint_version || 1,
        otp_verified: otpVerified,
        hitl_approved: hitlApproved,
        attachment_size_kb: 0,
      }),
    });
    const data: PreviewPacket = await res.json();
    setPreviewPacket(data);
  }

  const slots = (lastTurn?.slots || {}) as Record<string, unknown>;

  return (
    <div className="nk-grid-2">
      {/* Left Column: River Orb + Controls */}
      <section className="nk-card" style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
        <div style={{ width: "100%", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <span className="nk-pill" title="Runtime Engine Mode">
            {health ? `${health.engine_mode} · ${health.store_backend}` : "Loading engine..."}
          </span>
          <label style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: "0.82rem", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={consentGranted}
              onChange={(e) => {
                const next = e.target.checked;
                setConsentGranted(next);
                if (!next) {
                  stopPlayback();
                  submitTurn("consent withdraw");
                }
              }}
            />
            DPDP Consent
          </label>
        </div>

        <RiverOrb agentState={orbState} onClick={toggleMic} />
        <LiveWaveform active={listening} speaking={speaking} />

        <div className="nk-dock">
          <button type="button" className={`nk-btn ${listening ? "danger" : "primary"}`} onClick={toggleMic}>
            {listening ? <MicOff size={18} /> : <Mic size={18} />}
            {listening ? "Stop" : "Speak"}
          </button>
          <button type="button" className="nk-btn" onClick={stopPlayback} disabled={!speaking}>
            <RotateCcw size={16} />
            Barge-in
          </button>
          <button
            type="button"
            className="nk-btn"
            onClick={() => speakText("வணக்கம்! நான் நம்ம குரல். உங்கள் புகாரைச் சொல்லுங்கள்.")}
          >
            <Volume2 size={16} />
            Test Voice
          </button>
        </div>

        <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: 8 }}>
          <label htmlFor="voice-select" style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--ink-2)" }}>
            TTS Voice ({health?.sarvam_tts ? "Sarvam Bulbul + Edge" : "Edge-TTS / Offline"})
          </label>
          <select
            id="voice-select"
            className="nk-select"
            value={selectedVoice}
            onChange={(e) => setSelectedVoice(e.target.value)}
          >
            {voices.map((v) => (
              <option key={v.id} value={v.id}>
                {v.label}
              </option>
            ))}
          </select>
        </div>

        {clientTtfaMs !== null && (
          <div className="mono" style={{ fontSize: "0.8rem", color: clientTtfaMs < 500 ? "var(--emerald)" : "var(--amber)" }}>
            Client TTFA: {clientTtfaMs} ms {clientTtfaMs < 500 ? "(< 500 ms target met)" : ""}
          </div>
        )}
      </section>

      {/* Right Column: Conversation, Slots, OTP/HITL & Preview Packet */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <section className="nk-card">
          <h2 style={{ margin: "0 0 10px", fontSize: "1.05rem" }}>Tanglish Civic Intake</h2>
          <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
            <input
              aria-label="Civic complaint input"
              className="nk-input"
              style={{ flex: 1 }}
              placeholder="e.g. Anna Nagar-la streetlight eriyala..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") submitTurn(inputText);
              }}
            />
            <button type="button" className="nk-btn primary" onClick={() => submitTurn(inputText)}>
              <Send size={16} />
              Send
            </button>
          </div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
            {SAMPLE_PROMPTS.map((p) => (
              <button
                key={p}
                type="button"
                className="nk-pill"
                style={{ cursor: "pointer" }}
                onClick={() => submitTurn(p)}
              >
                {p}
              </button>
            ))}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: 260, overflowY: "auto" }}>
            {messages.length === 0 && (
              <p style={{ margin: 0, color: "var(--ink-3)", fontSize: "0.9rem" }}>
                Tap Speak or pick a Tanglish prompt above to start the intake workflow.
              </p>
            )}
            {messages.map((m, idx) => (
              <div
                key={idx}
                style={{
                  padding: "8px 12px",
                  borderRadius: 10,
                  background: m.role === "user" ? "var(--surface-2)" : "var(--bg)",
                  border: "1px solid var(--border)",
                }}
              >
                <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--ink-3)" }}>
                  {m.role === "user" ? "Citizen" : "NammaKural"} {m.meta ? `· ${m.meta}` : ""}
                </div>
                <div>{m.text}</div>
              </div>
            ))}
          </div>
        </section>

        {/* Extracted Slots & Text Contract */}
        {lastTurn && (
          <section className="nk-card">
            <h2 style={{ margin: "0 0 8px", fontSize: "1.05rem" }}>
              Complaint State (v{lastTurn.complaint_version ?? 1} · {lastTurn.fsm_state})
            </h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 8, fontSize: "0.86rem" }}>
              <div><strong>Service:</strong> {String(slots.service_id || "—")}</div>
              <div><strong>Landmark:</strong> {String(slots.landmark || "—")}</div>
              <div><strong>Ward:</strong> {String(slots.ward || "—")}</div>
              <div><strong>Agency:</strong> {String(slots.agency || "—")}</div>
            </div>
            {lastTurn.text_contract && (
              <div className="mono" style={{ marginTop: 8, fontSize: "0.78rem", color: "var(--ink-2)" }}>
                raw_asr: {lastTurn.text_contract.raw_asr} | normalized: {lastTurn.text_contract.normalized_text}
              </div>
            )}
          </section>
        )}

        {/* OTP + Dual-Confirm HITL + GCC Pre-Submit Packet */}
        <section className="nk-card">
          <h2 style={{ margin: "0 0 10px", fontSize: "1.05rem", display: "flex", alignItems: "center", gap: 6 }}>
            <ShieldCheck size={18} />
            OTP &amp; Dual-Confirm HITL Gate
          </h2>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", marginBottom: 10 }}>
            <input
              aria-label="Masked phone number"
              className="nk-input"
              style={{ width: 150 }}
              value={phoneMasked}
              onChange={(e) => setPhoneMasked(e.target.value)}
            />
            <button type="button" className="nk-btn" onClick={handleSendOtp}>
              Send OTP
            </button>
            {otpDemoHint && <span className="nk-pill mono">OTP: {otpDemoHint}</span>}
            <input
              aria-label="OTP code"
              className="nk-input"
              style={{ width: 110 }}
              placeholder="Code"
              value={otpCode}
              onChange={(e) => setOtpCode(e.target.value)}
            />
            <button type="button" className="nk-btn primary" onClick={handleVerifyOtp} disabled={!otpSessionId}>
              Verify OTP
            </button>
            {otpVerified && <span className="nk-pill" style={{ color: "var(--emerald)" }}>OTP Verified</span>}
          </div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
            <label style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: "0.88rem" }}>
              <input type="checkbox" checked={modalOk} onChange={(e) => setModalOk(e.target.checked)} />
              Final Clarity Popup OK
            </label>
            <button type="button" className="nk-btn emerald" onClick={handleHitlSeal}>
              <CheckCircle2 size={16} />
              Seal HITL (&quot;உறுதி / Confirm&quot;)
            </button>
            <button type="button" className="nk-btn" onClick={handleGeneratePreview}>
              Build GCC Preview Packet
            </button>
            {hitlStatus && <span className="nk-pill">{hitlStatus}</span>}
          </div>

          {previewPacket && (
            <div style={{ marginTop: 12, padding: 12, borderRadius: 10, border: "1px solid var(--emerald)", background: "var(--bg)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
                <strong className="mono">{previewPacket.preview_id}</strong>
                <span className="nk-pill">
                  {previewPacket.ready_for_portal ? "Ready for Portal (Dry-Run)" : `Missing: ${previewPacket.missing_fields.join(", ")}`}
                </span>
              </div>
              <p style={{ margin: "6px 0 4px", fontSize: "0.86rem" }}>{previewPacket.notice_ta}</p>
              <p style={{ margin: "0 0 8px", fontSize: "0.84rem", color: "var(--ink-2)" }}>{previewPacket.notice_en}</p>
              <pre className="mono" style={{ margin: 0, fontSize: "0.75rem", overflowX: "auto" }}>
                {JSON.stringify(previewPacket.fields, null, 2)}
              </pre>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

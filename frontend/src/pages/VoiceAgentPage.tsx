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
  livekit_ready?: boolean;
  agent_version?: string;
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
  const [sessionId, setSessionId] = useState<string>(() => `nk-${Date.now().toString(36)}`);
  const [orbState, setOrbState] = useState<OrbState>("idle");
  const [callActive, setCallActive] = useState<boolean>(false);
  const [muted, setMuted] = useState<boolean>(false);
  const [listening, setListening] = useState<boolean>(false);
  const [speaking, setSpeaking] = useState<boolean>(false);
  const [inputText, setInputText] = useState<string>("");
  const [voices, setVoices] = useState<VoiceOption[]>([
    { id: "auto", label: "Auto · Sarvam Bulbul v3 (ta-IN)" },
    { id: "ta-IN-PallaviNeural", label: "Pallavi (ta-IN Neural)" },
  ]);
  const [selectedVoice, setSelectedVoice] = useState<string>("auto");
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
  const mediaRecRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const vadTimerRef = useRef<number | null>(null);
  const callActiveRef = useRef<boolean>(false);
  const mutedRef = useRef<boolean>(false);
  const playbackGenRef = useRef<number>(0);
  const messagesRef = useRef<Array<{ role: "user" | "agent"; text: string; meta?: string }>>([]);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then((d) => setHealth(d))
      .catch(() => null);

    fetch("/api/tts/voices")
      .then((r) => r.json())
      .then((d) => {
        const raw = d?.voices ?? d;
        if (Array.isArray(raw) && raw.length > 0) {
          setVoices(raw);
          setSelectedVoice(raw[0].id);
        } else if (raw && typeof raw === "object") {
          const list: VoiceOption[] = [
            { id: "auto", label: "Auto · Sarvam Bulbul v3 (ta-IN)" },
            ...Object.entries(raw).map(([id, meta]: [string, any]) => ({
              id,
              label: String(meta?.label || meta?.name || id),
              lang: meta?.lang,
            })),
          ];
          setVoices(list);
          setSelectedVoice("auto");
        }
      })
      .catch(() => null);
  }, []);

  const chatEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesRef.current = messages;
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function stopMicCapture() {
    if (vadTimerRef.current !== null) {
      window.clearInterval(vadTimerRef.current);
      vadTimerRef.current = null;
    }
    if (recRef.current) {
      try {
        recRef.current.onend = null;
        recRef.current.stop();
      } catch {
        // ignore
      }
      recRef.current = null;
    }
    if (mediaRecRef.current && mediaRecRef.current.state !== "inactive") {
      try {
        mediaRecRef.current.stop();
      } catch {
        // ignore
      }
    }
    mediaRecRef.current = null;
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setListening(false);
  }

  function stopPlayback() {
    playbackGenRef.current += 1;
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

  function endCall() {
    callActiveRef.current = false;
    setCallActive(false);
    stopMicCapture();
    stopPlayback();
    setOrbState("idle");
  }

  async function speakText(text: string, turnStartMs?: number, cachedAssetUrl?: string) {
    if (!text.trim() && !cachedAssetUrl) {
      if (callActiveRef.current) startListeningTurn();
      return;
    }
    stopPlayback();
    const myGen = playbackGenRef.current;
    const ctrl = new AbortController();
    ttsAbortRef.current = ctrl;
    setSpeaking(true);
    setOrbState("talking");

    const resumeIfCallActive = () => {
      if (myGen !== playbackGenRef.current) return;
      setSpeaking(false);
      setOrbState("idle");
      if (callActiveRef.current) {
        window.setTimeout(() => {
          if (callActiveRef.current && myGen === playbackGenRef.current) {
            startListeningTurn();
          }
        }, 120);
      }
    };

    try {
      let url = cachedAssetUrl || "";
      let revokeAfter = false;
      if (!url) {
        const canMse = typeof MediaSource !== "undefined" && MediaSource.isTypeSupported("audio/mpeg");
        if (canMse) {
          const res = await fetch("/api/tts/stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, voice: selectedVoice, lang: "ta-IN" }),
            signal: ctrl.signal,
          });
          if (myGen !== playbackGenRef.current) return;
          if (res.ok && res.body) {
            const ms = new MediaSource();
            const msUrl = URL.createObjectURL(ms);
            const audio = new Audio(msUrl);
            audioRef.current = audio;
            audio.onplay = () => {
              if (myGen !== playbackGenRef.current) {
                audio.pause();
                return;
              }
              if (turnStartMs) {
                const ttfa = Math.round(performance.now() - turnStartMs);
                setClientTtfaMs(ttfa);
                fetch("/api/client-log", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ stage: "client.ttfa", message: "Browser streaming audio started", data: { latency_ms: ttfa, streamed: true } }),
                }).catch(() => null);
              }
            };
            audio.onended = () => {
              URL.revokeObjectURL(msUrl);
              resumeIfCallActive();
            };
            audio.onerror = () => {
              URL.revokeObjectURL(msUrl);
              resumeIfCallActive();
            };

            ms.addEventListener("sourceopen", async () => {
              try {
                const sb = ms.addSourceBuffer("audio/mpeg");
                const reader = res.body!.getReader();
                let started = false;
                while (true) {
                  const { done, value } = await reader.read();
                  if (myGen !== playbackGenRef.current) {
                    reader.cancel().catch(() => null);
                    return;
                  }
                  if (done) {
                    if (ms.readyState === "open") ms.endOfStream();
                    break;
                  }
                  if (value && value.byteLength > 0) {
                    if (sb.updating) {
                      await new Promise<void>((resolve) => sb.addEventListener("updateend", () => resolve(), { once: true }));
                    }
                    sb.appendBuffer(value);
                    await new Promise<void>((resolve) => sb.addEventListener("updateend", () => resolve(), { once: true }));
                    if (!started) {
                      started = true;
                      audio.play().catch(() => null);
                    }
                  }
                }
              } catch {
                resumeIfCallActive();
              }
            });
            return;
          }
        }

        const res = await fetch("/api/tts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, voice: selectedVoice, lang: "ta-IN" }),
          signal: ctrl.signal,
        });
        if (myGen !== playbackGenRef.current) return;
        if (res.status === 204 || !res.ok) {
          resumeIfCallActive();
          return;
        }
        const blob = await res.blob();
        if (myGen !== playbackGenRef.current) return;
        url = URL.createObjectURL(blob);
        revokeAfter = true;
      }

      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onplay = () => {
        if (myGen !== playbackGenRef.current) {
          audio.pause();
          return;
        }
        if (turnStartMs) {
          const ttfa = Math.round(performance.now() - turnStartMs);
          setClientTtfaMs(ttfa);
          fetch("/api/client-log", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              stage: "client.ttfa",
              message: "Browser audio playback started",
              data: { latency_ms: ttfa, cached: Boolean(cachedAssetUrl) },
            }),
          }).catch(() => null);
        }
      };
      audio.onended = () => {
        if (revokeAfter) URL.revokeObjectURL(url);
        resumeIfCallActive();
      };
      audio.onerror = () => {
        if (revokeAfter) URL.revokeObjectURL(url);
        resumeIfCallActive();
      };
      await audio.play();
    } catch {
      resumeIfCallActive();
    }
  }

  async function submitTurn(rawText: string) {
    const trimmed = rawText.trim();
    if (!trimmed) {
      if (callActiveRef.current) startListeningTurn();
      return;
    }

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
    const recentHistory = messagesRef.current.slice(-6).map((m) => ({ role: m.role, text: m.text }));
    setMessages((m) => [...m, { role: "user", text: trimmed }]);
    setInputText("");

    try {
      const res = await fetch("/api/workflow/turn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          utterance: trimmed,
          session_id: sessionId,
          state_code: "tn",
          dpdp_consented: consentGranted,
          otp_verified: otpVerified,
          history: recentHistory,
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

      const urgency = (data.analysis as any)?.urgency?.tier || (data.analysis as any)?.urgency_tier;
      if (urgency === "CRITICAL_SAFETY" || urgency === "LIFE_SAFETY" || urgency === "P1") {
        setOrbState("urgent");
      }
      const speechTarget = data.tts_text || replyText;
      await speakText(speechTarget, t0);
    } catch (err) {
      setOrbState("idle");
      setMessages((m) => [...m, { role: "agent", text: `Error: ${String(err)}` }]);
    }
  }

  async function startSarvamMicTurn(): Promise<boolean> {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      return false;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      if (!callActiveRef.current) {
        stream.getTracks().forEach((t) => t.stop());
        return true;
      }
      streamRef.current = stream;
      const chunks: BlobPart[] = [];
      const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : "audio/webm";
      const mr = new MediaRecorder(stream, { mimeType: mime });
      mediaRecRef.current = mr;

      const audioCtx = new AudioContext();
      const src = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 512;
      src.connect(analyser);
      const buf = new Float32Array(analyser.fftSize);
      let heardSpeech = false;
      let lastSpeechMs = performance.now();
      const startedMs = lastSpeechMs;

      mr.ondataavailable = (ev) => {
        if (ev.data && ev.data.size > 0) chunks.push(ev.data);
      };
      mr.onstop = async () => {
        if (vadTimerRef.current !== null) {
          window.clearInterval(vadTimerRef.current);
          vadTimerRef.current = null;
        }
        stream.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        audioCtx.close().catch(() => null);
        setListening(false);
        if (!heardSpeech || chunks.length === 0) {
          if (callActiveRef.current) startListeningTurn();
          else setOrbState("idle");
          return;
        }
        const blob = new Blob(chunks, { type: mime });
        const form = new FormData();
        form.append("audio", blob, "speech.webm");
        try {
          setOrbState("thinking");
          const sttRes = await fetch("/api/stt?lang=ta-IN", { method: "POST", body: form });
          const sttJson = await sttRes.json();
          const transcript = String(sttJson.transcript || "").trim();
          if (transcript) {
            await submitTurn(transcript);
          } else if (callActiveRef.current) {
            startListeningTurn();
          } else {
            setOrbState("idle");
          }
        } catch {
          if (callActiveRef.current) startListeningTurn();
          else setOrbState("idle");
        }
      };

      mr.start(250);
      setListening(true);
      setOrbState("listening");

      vadTimerRef.current = window.setInterval(() => {
        if (mutedRef.current) return;
        analyser.getFloatTimeDomainData(buf);
        let sum = 0;
        for (let i = 0; i < buf.length; i += 1) sum += buf[i] * buf[i];
        const rms = Math.sqrt(sum / buf.length);
        const now = performance.now();
        if (rms > 0.022) {
          heardSpeech = true;
          lastSpeechMs = now;
        } else if (heardSpeech && now - lastSpeechMs > 850) {
          if (mr.state !== "inactive") mr.stop();
        } else if (!heardSpeech && now - startedMs > 12000) {
          if (mr.state !== "inactive") mr.stop();
        }
      }, 90);
      return true;
    } catch {
      return false;
    }
  }

  async function startListeningTurn() {
    if (!callActiveRef.current || !consentGranted || mutedRef.current) return;
    stopMicCapture();
    if (health?.sarvam_stt) {
      const ok = await startSarvamMicTurn();
      if (ok) return;
    }

    const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRec) {
      callActiveRef.current = false;
      setCallActive(false);
      setMessages((m) => [
        ...m,
        { role: "agent", text: "Browser SpeechRecognition unavailable; use the Tanglish text box or sample chips." },
      ]);
      return;
    }
    const rec = new SpeechRec();
    rec.lang = "ta-IN";
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    let gotResult = false;
    rec.onstart = () => {
      setListening(true);
      setOrbState("listening");
    };
    rec.onresult = (ev: any) => {
      const transcript = ev?.results?.[0]?.[0]?.transcript || "";
      gotResult = Boolean(transcript);
      setListening(false);
      if (transcript) {
        submitTurn(transcript);
      } else if (callActiveRef.current) {
        startListeningTurn();
      } else {
        setOrbState("idle");
      }
    };
    rec.onerror = () => {
      setListening(false);
      if (callActiveRef.current && !gotResult) {
        window.setTimeout(() => {
          if (callActiveRef.current) startListeningTurn();
        }, 300);
      } else {
        setOrbState("idle");
      }
    };
    rec.onend = () => {
      setListening(false);
    };
    recRef.current = rec;
    rec.start();
  }

  function toggleMute() {
    const next = !mutedRef.current;
    mutedRef.current = next;
    setMuted(next);
    if (streamRef.current) {
      streamRef.current.getAudioTracks().forEach((t) => {
        t.enabled = !next;
      });
    }
    if (next) {
      if (recRef.current) {
        try {
          recRef.current.stop();
        } catch {
          // ignore
        }
      }
      setListening(false);
      if (!speaking) setOrbState("idle");
    } else if (callActiveRef.current && !speaking) {
      startListeningTurn();
    }
  }

  function toggleMic() {
    if (callActiveRef.current || listening) {
      endCall();
      return;
    }
    if (!consentGranted) {
      setMessages((m) => [
        ...m,
        { role: "agent", text: "Please grant DPDP voice consent before starting microphone capture." },
      ]);
      return;
    }
    if (speaking) stopPlayback();
    callActiveRef.current = true;
    setCallActive(true);
    startListeningTurn();
  }

  async function handleSendOtp() {
    const res = await fetch("/api/otp/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone_masked: phoneMasked }),
    });
    const data = await res.json();
    setOtpSessionId(data.otp_session_id || "");
    setOtpDemoHint(data.demo_otp_hint || data.demo_code || data.code || "Check SMS");
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
    const analysis = (lastTurn?.analysis || {}) as Record<string, any>;
    const res = await fetch("/api/hitl/seal", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mode: "modal_plus_voice",
        spoken_phrase: "உறுதி / Confirm",
        modal_ok: modalOk,
        otp_session_id: otpSessionId,
        ward: String(analysis.landmark?.ward || slots.ward || "Ward 103"),
        service_id: String(analysis.service_id || slots.issue || "streetlight_eb"),
        urgency_tier: String(analysis.urgency?.tier || "STANDARD"),
        complaint_revision: String(lastTurn?.complaint_version ?? 1),
      }),
    });
    const data = await res.json();
    const ok = Boolean(data.sealed || data.approved || data.status === "sealed");
    setHitlApproved(ok);
    setHitlStatus(
      data.reason ||
        data.message ||
        (ok ? `HITL Sealed (${data.ticket_id || "ready"})` : "Confirmation incomplete")
    );
  }

  async function handleGeneratePreview() {
    const slots = (lastTurn?.slots || {}) as Record<string, unknown>;
    const analysis = (lastTurn?.analysis || {}) as Record<string, any>;
    const landmarkObj = analysis.landmark || {
      name: String(slots.landmark || "Anna Arch pakkam"),
      ward: String(slots.ward || ""),
    };
    const res = await fetch("/api/portal/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        service_id: String(analysis.service_id || slots.issue || "streetlight_eb"),
        landmark: landmarkObj,
        summary_text: lastTurn?.display_text || "Streetlight complaint preview",
        urgency_tier: String(analysis.urgency?.tier || "STANDARD"),
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
  const analysis = (lastTurn?.analysis || {}) as Record<string, any>;

  return (
    <div className="nk-studio">
      {/* Left Column: Hero RiverOrb + Voice Controls (Orb untouched) */}
      <section className="nk-hero-card">
        <div style={{ width: "100%", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <span className="nk-pill accent" title="Runtime Engine Mode">
            {health
              ? `${health.engine_mode} · ${health.store_backend}${health.livekit_ready ? " · livekit" : ""}`
              : "Connecting..."}
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <button
              type="button"
              className="nk-pill"
              style={{ cursor: "pointer" }}
              onClick={() => {
                endCall();
                setSessionId(`nk-${Date.now().toString(36)}`);
                setMessages([]);
                setLastTurn(null);
                setPreviewPacket(null);
                setOtpVerified(false);
                setHitlApproved(false);
                setHitlStatus("");
              }}
            >
              New Call
            </button>
            <label style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: "0.78rem", color: "var(--ink-2)", cursor: "pointer" }}>
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
              Consent
            </label>
          </div>
        </div>

        <RiverOrb agentState={orbState} onClick={toggleMic} />
        <LiveWaveform active={listening} speaking={speaking} />

        <div className="nk-dock">
          <button type="button" className={`nk-btn ${callActive || listening ? "danger" : "primary"}`} onClick={toggleMic}>
            {callActive || listening ? <MicOff size={17} /> : <Mic size={17} />}
            {callActive || listening ? "End Call" : "Start Call"}
          </button>
          <button
            type="button"
            className={`nk-btn ${muted ? "danger" : ""}`}
            aria-pressed={muted}
            onClick={toggleMute}
          >
            {muted ? <MicOff size={15} /> : <Mic size={15} />}
            {muted ? "Unmute" : "Mute"}
          </button>
          <button type="button" className="nk-btn" onClick={stopPlayback} disabled={!speaking}>
            <RotateCcw size={15} />
            Barge-in
          </button>
          <button
            type="button"
            className="nk-btn"
            onClick={() => speakText("வணக்கம்! நான் நம்ம குரல். உங்கள் புகாரைச் சொல்லுங்கள்.")}
          >
            <Volume2 size={15} />
            Test Voice
          </button>
        </div>

        <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: 6 }}>
          <label htmlFor="voice-select" style={{ fontSize: "0.78rem", fontWeight: 600, color: "var(--ink-3)" }}>
            Voice ({health?.sarvam_tts ? "Sarvam Bulbul v3 + Edge" : "Edge-TTS / Offline"})
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
          <div className={`nk-pill ${clientTtfaMs < 500 ? "emerald" : ""}`} style={{ fontVariantNumeric: "tabular-nums" }}>
            TTFA: {clientTtfaMs} ms {clientTtfaMs < 500 ? "(< 500 ms)" : ""}
          </div>
        )}
      </section>

      {/* Right Column: Natural Conversation Stream + Progressive Civic Actions */}
      <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        <section className="nk-card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <h2 style={{ margin: 0, fontSize: "1.06rem" }}>Live Conversation</h2>
            <span className="nk-pill mono" style={{ fontSize: "0.72rem" }}>session: {sessionId}</span>
          </div>

          <div className="nk-chat-stream" aria-live="polite" aria-label="Conversation transcript">
            {messages.length === 0 && (
              <div style={{ padding: "24px 12px", textAlign: "center", color: "var(--ink-3)", fontSize: "0.92rem" }}>
                Tap <strong>Start Call</strong> or type in Tamil / Tanglish below to begin a natural conversation.
              </div>
            )}
            {messages.map((m, idx) => (
              <div key={idx} className={`nk-bubble ${m.role}`}>
                <div className="nk-bubble-meta">
                  {m.role === "user" ? "You" : "NammaKural"} {m.meta ? `· ${m.meta}` : ""}
                </div>
                <div>{m.text}</div>
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <input
              aria-label="Civic complaint input"
              className="nk-input"
              style={{ flex: "1 1 200px", minWidth: 0 }}
              placeholder="Speak or type in Tamil / Tanglish (e.g. Anna Nagar-la streetlight eriyala)..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") submitTurn(inputText);
              }}
            />
            <button type="button" className="nk-btn primary" onClick={() => submitTurn(inputText)}>
              <Send size={15} />
              Send
            </button>
          </div>

          <details>
            <summary style={{ cursor: "pointer", fontSize: "0.84rem", fontWeight: 600, color: "var(--ink-2)", padding: "6px 0" }}>
              Sample Tanglish / Tamil Prompts
            </summary>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
              {SAMPLE_PROMPTS.map((p) => (
                <button
                  key={p}
                  type="button"
                  className="nk-pill"
                  onClick={() => submitTurn(p)}
                >
                  {p}
                </button>
              ))}
            </div>
          </details>
        </section>

        {/* Extracted Slots Summary */}
        {lastTurn && (
          <section className="nk-card" style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
              <span className="nk-pill accent">{lastTurn.fsm_state} · v{lastTurn.complaint_version ?? 1}</span>
              <span className="nk-pill">Service: {String(analysis.service_id || slots.issue || "—")}</span>
              <span className="nk-pill">Place: {String(analysis.landmark_text || slots.landmark || "—")}</span>
              <span className={`nk-pill ${analysis.landmark?.ward ? "emerald" : ""}`}>
                Ward: {String(analysis.landmark?.ward || "Pending")}
              </span>
            </div>
            <span style={{ fontSize: "0.78rem", color: "var(--ink-3)" }}>
              {String(analysis.urgency?.badge_en || "")}
            </span>
          </section>
        )}

        {/* Progressive OTP + Dual-Confirm HITL Gate + GCC Preview */}
        <section
          className="nk-card"
          aria-live="assertive"
          style={{ borderColor: lastTurn?.fsm_state === "HITL_SEAL" ? "var(--emerald)" : "var(--border)" }}
        >
          <h2 style={{ margin: "0 0 12px", fontSize: "1rem", display: "flex", alignItems: "center", gap: 7 }}>
            <ShieldCheck size={18} />
            Citizen Verification &amp; GCC Pre-Submit Packet
          </h2>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", marginBottom: 12 }}>
            <input
              aria-label="Masked phone number"
              className="nk-input"
              style={{ width: 145 }}
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
              style={{ width: 100 }}
              placeholder="Code"
              value={otpCode}
              onChange={(e) => setOtpCode(e.target.value)}
            />
            <button type="button" className="nk-btn primary" onClick={handleVerifyOtp} disabled={!otpSessionId}>
              Verify
            </button>
            {otpVerified && <span className="nk-pill emerald">OTP Verified</span>}
          </div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
            <label style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: "0.86rem", cursor: "pointer" }}>
              <input type="checkbox" checked={modalOk} onChange={(e) => setModalOk(e.target.checked)} />
              Clarity Popup OK
            </label>
            <button type="button" className="nk-btn emerald" onClick={handleHitlSeal}>
              <CheckCircle2 size={15} />
              Seal HITL (&quot;உறுதி / Confirm&quot;)
            </button>
            <button type="button" className="nk-btn" onClick={handleGeneratePreview}>
              Build GCC Packet
            </button>
            {hitlStatus && <span className="nk-pill">{hitlStatus}</span>}
          </div>

          {previewPacket && (
            <div style={{ marginTop: 14, padding: 14, borderRadius: 12, border: "1px solid var(--emerald)", background: "var(--bg)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
                <strong className="mono">{previewPacket.preview_id}</strong>
                <span className="nk-pill emerald">
                  {previewPacket.ready_for_portal ? "Ready for Portal (Dry-Run)" : `Missing: ${previewPacket.missing_fields.join(", ")}`}
                </span>
              </div>
              <p style={{ margin: "8px 0 4px", fontSize: "0.86rem" }}>{previewPacket.notice_ta}</p>
              <p style={{ margin: "0 0 10px", fontSize: "0.84rem", color: "var(--ink-2)" }}>{previewPacket.notice_en}</p>
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

import { useEffect, useRef, useState } from "react";
import { Mic, MicOff, Volume2, ShieldCheck, Send, MapPin, RotateCcw, ChevronLeft, ChevronRight, Paperclip, X, FileText, Image as ImageIcon } from "lucide-react";
import { RiverOrb, type OrbState, type OrbVoiceTheme } from "../components/RiverOrb";
import { LiveWaveform } from "../components/LiveWaveform";
import { recordBrowserMeasurement, turnHeaders, type TurnMeasurement } from "../callTelemetry";

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
  grievance_draft?: GrievanceDraft | null;
  reply?: string;
  display_text?: string;
  tts_text?: string;
  clauses?: string[];
  tool_trace?: Array<Record<string, unknown>>;
}

interface GrievanceDraft {
  status: "needs_location" | "needs_details" | "needs_confirmation" | "cooldown";
  intent: string;
  label: string;
  label_ta: string;
  summary: string;
  revision: number;
  urgency_tier: string;
  duration_days: number | null;
  impact: string | null;
  next_field: "duration" | "impact" | null;
  checklist: { checks: { label: string; complete: boolean }[]; email?: string; whatsapp?: string; web: string; citizen_enters: string[] };
  location: { landmark: string; ward: string; area: string; street: string; source?: string };
  destination: { id: string; name: string; url: string; helpline: string };
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

interface AttachmentInfo {
  filename: string;
  size_kb: number;
  within_gcc_1mb_limit: boolean;
  type: "document_pdf" | "street_photo" | string;
  extracted_ticket: string | null;
}

const VOICE_THEMES: Record<string, OrbVoiceTheme> = {
  auto: { rgb: "30, 58, 138", top: "#3B82F6", mid: "#1E3A8A", bot: "#0F766E" },
  "sarvam-kavitha": { rgb: "190, 24, 93", top: "#F472B6", mid: "#BE185D", bot: "#831843" },
  "sarvam-shubh": { rgb: "15, 118, 110", top: "#2DD4BF", mid: "#0F766E", bot: "#115E59" },
  "sarvam-priya": { rgb: "124, 58, 237", top: "#A78BFA", mid: "#7C3AED", bot: "#4C1D95" },
  "sarvam-mani": { rgb: "217, 119, 6", top: "#FBBF24", mid: "#D97706", bot: "#92400E" },
  "sarvam-shruti": { rgb: "5, 150, 105", top: "#34D399", mid: "#059669", bot: "#065F46" },
  "sarvam-gokul": { rgb: "8, 145, 178", top: "#22D3EE", mid: "#0891B2", bot: "#155E75" },
  "ta-IN-PallaviNeural": { rgb: "234, 88, 12", top: "#FB923C", mid: "#EA580C", bot: "#9A3412" },
  "ta-IN-ValluvarNeural": { rgb: "71, 85, 105", top: "#94A3B8", mid: "#475569", bot: "#1E293B" },
  "en-IN-PrabhatNeural": { rgb: "37, 99, 235", top: "#60A5FA", mid: "#2563EB", bot: "#1E40AF" },
  "en-IN-NeerjaExpressiveNeural": { rgb: "162, 28, 175", top: "#E879F9", mid: "#A21CAF", bot: "#701A75" },
};

function getVoiceTheme(id: string): OrbVoiceTheme {
  return VOICE_THEMES[id] ?? VOICE_THEMES.auto;
}

const BACKCHANNEL_RE = /^(mm+|mmm+|hmm+|seri|sari|aama|ama|ok|okay|haan|ஆமா|சரி)$/i;

const SAMPLE_PROMPTS = [
  "Anna Nagar-la streetlight eriyala",
  "Tower Park back side, Fifth Avenue",
  "Illa, Tower Park illa, Anna Arch pakkam",
  "Navalur Marina Mall opposite-la water stagnation",
  "உறுதி / Confirm",
];

const SESSION_KEY = "nammakural.complaint";
const CONSENT_KEY = "nammakural.consent";

export default function VoiceAgentPage({ signedIn = false }: { signedIn?: boolean }) {
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const [consentGranted, setConsentGranted] = useState(() => sessionStorage.getItem(CONSENT_KEY) !== "denied");
  const [sessionId, setSessionId] = useState(() => sessionStorage.getItem(SESSION_KEY) || crypto.randomUUID());
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
  const [draft, setDraft] = useState<GrievanceDraft | null>(null);
  const [locationPending, setLocationPending] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [locationStatus, setLocationStatus] = useState("");
  const [messages, setMessages] = useState<Array<{ role: "user" | "agent"; text: string; meta?: string }>>([]);
  const [clientTtfaMs, setClientTtfaMs] = useState<number | null>(null);

  // OTP + HITL state
  const [phoneMasked, setPhoneMasked] = useState<string>("");
  const [otpSessionId, setOtpSessionId] = useState<string>("");
  const [otpDemoHint, setOtpDemoHint] = useState<string>("");
  const [otpCode, setOtpCode] = useState<string>("");
  const [otpVerified, setOtpVerified] = useState<boolean>(false);
  const [modalOk, setModalOk] = useState<boolean>(false);
  const [hitlApproved, setHitlApproved] = useState<boolean>(false);
  const [handoffAuthorized, setHandoffAuthorized] = useState(false);
  const [hitlStatus, setHitlStatus] = useState<string>("");
  const [previewPacket, setPreviewPacket] = useState<PreviewPacket | null>(null);
  const [attachment, setAttachment] = useState<AttachmentInfo | null>(null);
  const [uploadingAttachment, setUploadingAttachment] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const ttsAbortRef = useRef<AbortController | null>(null);
  const recRef = useRef<any>(null);
  const mediaRecRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const vadTimerRef = useRef<number | null>(null);
  const callActiveRef = useRef<boolean>(false);
  const mutedRef = useRef<boolean>(false);
  const playbackGenRef = useRef<number>(0);
  const captureGenRef = useRef(0);
  const responseGenRef = useRef(0);
  const pendingTurnRef = useRef<number | null>(null);
  const localCallId = useRef("");
  const callStartedAt = useRef<number | null>(null);
  const complaintSessionRef = useRef(sessionId);
  const consentRef = useRef(consentGranted);
  const submitTurnRef = useRef(submitTurn);
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

  useEffect(() => {
    sessionStorage.setItem(SESSION_KEY, sessionId);
    if (!consentGranted) return;
    const abort = new AbortController();
    const generation = responseGenRef.current;
    void fetch(`/api/workflow/draft?session_id=${encodeURIComponent(sessionId)}`, { signal: abort.signal })
      .then((response) => response.ok ? response.json() : null)
      .then((data) => {
        if (!abort.signal.aborted && responseGenRef.current === generation && data?.grievance_draft) {
          setDraft(data.grievance_draft);
        }
      })
      .catch(() => undefined);
    return () => abort.abort();
  }, [sessionId, consentGranted]);

  useEffect(() => {
    window.addEventListener("pagehide", endCall);
    return () => {
      window.removeEventListener("pagehide", endCall);
      endCall();
    };
  }, []);

  const chatEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesRef.current = messages;
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    submitTurnRef.current = submitTurn;
  });

  function stopMicCapture() {
    captureGenRef.current += 1;
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
    if (callStartedAt.current !== null) {
      recordBrowserMeasurement("call.ended", localCallId.current, undefined, {
        duration_ms: Math.round(performance.now() - callStartedAt.current),
      });
      callStartedAt.current = null;
    }
    callActiveRef.current = false;
    setCallActive(false);
    stopMicCapture();
    stopPlayback();
    setOrbState("idle");
  }

  function newTurn(modality: TurnMeasurement["modality"]): TurnMeasurement {
    localCallId.current ||= crypto.randomUUID();
    return { callId: localCallId.current, turnId: crypto.randomUUID(), modality };
  }

  async function speakText(text: string, turn?: TurnMeasurement, cachedAssetUrl?: string) {
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
    let measuredPlayback = false;
    const onPlayback = (audio: HTMLAudioElement) => {
      if (myGen !== playbackGenRef.current) {
        audio.pause();
        return;
      }
      if (!turn || turn.submittedAt === undefined || measuredPlayback) return;
      measuredPlayback = true;
      const now = performance.now();
      const postTranscript = Math.round(now - turn.submittedAt);
      setClientTtfaMs(postTranscript);
      recordBrowserMeasurement("call.playback", turn.callId, turn, {
        post_transcript_ms: postTranscript,
        speech_to_playback_ms: turn.speechEndedAt === undefined ? undefined : Math.round(now - turn.speechEndedAt),
        endpoint_wait_ms: turn.endpointWaitMs,
        browser_stt_ms: turn.browserSttMs,
      });
    };

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
            headers: { "Content-Type": "application/json", ...turnHeaders(turn) },
            body: JSON.stringify({ text, voice: selectedVoice, lang: "ta-IN" }),
            signal: ctrl.signal,
          });
          if (myGen !== playbackGenRef.current) return;
          if (res.ok && res.body) {
            const ms = new MediaSource();
            const msUrl = URL.createObjectURL(ms);
            const audio = new Audio(msUrl);
            audioRef.current = audio;
            audio.onplaying = () => onPlayback(audio);
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
          headers: { "Content-Type": "application/json", ...turnHeaders(turn) },
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
      audio.onplaying = () => onPlayback(audio);
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

  async function submitTurn(rawText: string, turn = newTurn("text"), position?: GeolocationCoordinates) {
    const trimmed = rawText.trim();
    if ((!trimmed && !position) || !consentRef.current) {
      if (callActiveRef.current) startListeningTurn();
      return;
    }
    if (pendingTurnRef.current !== null) return;

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

    stopMicCapture();
    const requestGeneration = ++responseGenRef.current;
    pendingTurnRef.current = requestGeneration;
    setSubmitting(true);
    const finishRequest = () => {
      if (pendingTurnRef.current === requestGeneration) {
        pendingTurnRef.current = null;
        setSubmitting(false);
      }
    };
    turn.submittedAt = performance.now();
    setOrbState("thinking");
    if (turn.modality === "voice" && /^(?:confirm|உறுதி|urudhi|uruthi)[\s.!?,]*$/i.test(trimmed) && draft?.status === "needs_confirmation") {
      try {
        await handleHitlSeal(trimmed, turn);
      } finally {
        finishRequest();
      }
      return;
    }
    const recentHistory = messagesRef.current.slice(-6).map((m) => ({ role: m.role, text: m.text }));
    if (trimmed) setMessages((m) => [...m, { role: "user", text: trimmed }]);
    if (turn.modality === "text") setInputText("");

    try {
      const res = await fetch("/api/workflow/turn", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...turnHeaders(turn) },
        body: JSON.stringify({
          utterance: trimmed,
          session_id: sessionId,
          state_code: "tn",
          input_mode: turn.modality,
          dpdp_consented: consentGranted,
          otp_verified: otpVerified,
          history: recentHistory,
          gps_lat: position?.latitude,
          gps_lon: position?.longitude,
          gps_accuracy_m: position ? Math.min(position.accuracy, 100_000) : undefined,
        }),
      });
      if (!res.ok) throw new Error("The service could not process this turn.");
      const data: TurnResponse = await res.json();
      if (requestGeneration !== responseGenRef.current) return;
      setLastTurn(data);
      if (data.grievance_draft) {
        const next = data.grievance_draft;
        if (draft && next.revision !== draft.revision) {
          setModalOk(false);
          setHitlApproved(false);
          setHandoffAuthorized(false);
          setHitlStatus("");
        }
        setDraft(next);
        setPreviewPacket(next.destination.id === "gcc_pgrs" ? data.preview_packet ?? null : null);
        if (position) {
          setLocationStatus(next.location.source === "gps" && next.location.ward
            ? "Location matched to a ward in the civic directory."
            : "GPS did not verify the reported location. Type or say a nearby public landmark.");
        }
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
      await speakText(speechTarget, turn);
    } catch (err) {
      if (requestGeneration !== responseGenRef.current) return;
      setOrbState("idle");
      setMessages((m) => [...m, { role: "agent", text: `Error: ${String(err)}` }]);
      if (position) setLocationStatus("Could not check GPS. Type or say the public landmark.");
      if (callActiveRef.current) startListeningTurn();
    } finally {
      finishRequest();
    }
  }

  function requestLocation() {
    if (!consentGranted || !draft || locationPending || submitting) return;
    if (!navigator.geolocation) {
      setLocationStatus("Location is unavailable in this browser. Type or say a landmark.");
      return;
    }
    const activeSession = complaintSessionRef.current;
    setLocationPending(true);
    setLocationStatus("Waiting for your location permission…");
    navigator.geolocation.getCurrentPosition(async ({ coords }) => {
      if (activeSession !== complaintSessionRef.current || !consentRef.current) return;
      try {
        if (pendingTurnRef.current !== null) {
          setLocationStatus("Finish the current turn, then try sharing your location again.");
          return;
        }
        await submitTurnRef.current("", newTurn("gps"), coords);
      } finally {
        setLocationPending(false);
      }
    }, () => {
      if (activeSession !== complaintSessionRef.current) return;
      setLocationPending(false);
      setLocationStatus("Location unavailable. Type or say a nearby junction or public landmark.");
    }, { enableHighAccuracy: true, maximumAge: 0, timeout: 12000 });
  }

  async function startSarvamMicTurn(): Promise<boolean> {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      return false;
    }
    try {
      const captureGen = ++captureGenRef.current;
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      if (!callActiveRef.current || captureGen !== captureGenRef.current) {
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
        const stoppedAt = performance.now();
        if (captureGen !== captureGenRef.current) {
          audioCtx.close().catch(() => null);
          return;
        }
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
        const turn = newTurn("voice");
        turn.speechEndedAt = lastSpeechMs;
        turn.endpointWaitMs = Math.round(stoppedAt - lastSpeechMs);
        recordBrowserMeasurement("call.upload", turn.callId, turn, {
          recorded_audio_ms: Math.round(stoppedAt - startedMs),
          endpoint_wait_ms: turn.endpointWaitMs,
        });
        const form = new FormData();
        form.append("audio", blob, "speech.webm");
        try {
          setOrbState("thinking");
          const sttStarted = performance.now();
          const sttRes = await fetch("/api/stt?lang=ta-IN", {
            method: "POST", body: form, headers: turnHeaders(turn),
          });
          const sttJson = await sttRes.json();
          if (captureGen !== captureGenRef.current || !callActiveRef.current) return;
          turn.browserSttMs = Math.round(performance.now() - sttStarted);
          const transcript = String(sttJson.transcript || "").trim();
          if (transcript) {
            await submitTurnRef.current(transcript, turn);
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
      endCall();
      setMessages((m) => [
        ...m,
        { role: "agent", text: "Browser SpeechRecognition unavailable; use the Tanglish text box or sample chips." },
      ]);
      return;
    }
    const rec = new SpeechRec();
    const captureGen = ++captureGenRef.current;
    let speechEndedAt: number | undefined;
    rec.onspeechend = () => { speechEndedAt = performance.now(); };
    rec.lang = "ta-IN";
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    let gotResult = false;
    rec.onstart = () => {
      setListening(true);
      setOrbState("listening");
    };
    rec.onresult = (ev: any) => {
      if (captureGen !== captureGenRef.current || !callActiveRef.current) return;
      const transcript = ev?.results?.[0]?.[0]?.transcript || "";
      gotResult = Boolean(transcript);
      setListening(false);
      if (transcript) {
        void submitTurnRef.current(transcript, { ...newTurn("voice"), speechEndedAt });
      } else if (callActiveRef.current) {
        startListeningTurn();
      } else {
        setOrbState("idle");
      }
    };
    rec.onerror = () => {
      if (captureGen !== captureGenRef.current) return;
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
      if (captureGen === captureGenRef.current) setListening(false);
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
    localCallId.current = crypto.randomUUID();
    callStartedAt.current = performance.now();
    recordBrowserMeasurement("call.started", localCallId.current);
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

  async function handleHitlSeal(spokenPhrase: string, turn: TurnMeasurement) {
    try {
      if (!draft || (!signedIn && !otpVerified) || !draft.location.ward) {
        setHitlStatus("Verify your mobile OTP before saying Confirm.");
        return;
      }
      const generation = responseGenRef.current;
      const res = await fetch("/api/hitl/seal", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...turnHeaders(turn) },
        body: JSON.stringify({
          mode: modalOk ? "modal_plus_voice" : "voice_double",
          spoken_phrase: spokenPhrase,
          modal_ok: modalOk,
          otp_session_id: otpSessionId,
          session_id: sessionId,
          ward: draft.location.ward,
          service_id: draft.intent,
          urgency_tier: draft.urgency_tier,
          complaint_revision: String(draft.revision),
          turn_id: turn.turnId,
        }),
      });
      if (!res.ok) throw new Error("Confirmation request failed.");
      const data = await res.json();
      if (generation !== responseGenRef.current) return;
      setHitlApproved(Boolean(data.approved));
      setHandoffAuthorized(Boolean(data.handoff_authorized));
      setHitlStatus(data.approved
        ? data.handoff_authorized ? "Review sealed. Open the official portal to file." : "Demo review complete. No complaint was submitted."
        : data.reason || "Confirmation incomplete");
      if (data.approved) endCall();
    } catch {
      setHitlStatus("Could not confirm the draft. Try saying Confirm again.");
    } finally {
      setOrbState("idle");
      if (callActiveRef.current) startListeningTurn();
    }
  }

  async function saveToHistory() {
    try {
      const response = await fetch("/api/requests", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: sessionId }),
      });
      if (!response.ok) {
        const result = await response.json();
        setHitlStatus(typeof result.detail === "string" ? result.detail : "Could not save this draft.");
        return;
      }
      setHitlStatus("Saved to My requests.");
    } catch {
      setHitlStatus("Could not save this draft.");
    }
  }

  async function handleFileUpload(file: File) {
    setUploadingAttachment(true);
    try {
      const form = new FormData();
      form.append("file", file);
      if (inputText.trim()) form.append("note", inputText.trim());
      const res = await fetch("/api/attachment/inspect", { method: "POST", body: form });
      const data: AttachmentInfo = await res.json();
      setAttachment(data);
      const ticketPart = data.extracted_ticket ? ` · Ticket ${data.extracted_ticket}` : "";
      const limitPart = data.within_gcc_1mb_limit ? "GCC <1 MB OK" : "Exceeds 1 MB GCC limit";
      setMessages((m) => [
        ...m,
        {
          role: "agent",
          text: `Attachment inspected: ${data.filename} (${data.size_kb} KB${ticketPart}) — ${limitPart}.`,
          meta: data.type,
        },
      ]);
    } catch {
      setMessages((m) => [...m, { role: "agent", text: "Attachment inspection failed. Please try another photo or PDF." }]);
    } finally {
      setUploadingAttachment(false);
    }
  }

  return (
    <div className="nk-open-canvas">
      {/* Minimal Waterline Controls */}
      <div className="nk-open-top">
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <span className="nk-pill accent" title="Runtime Engine Mode">
            {health
              ? `${health.engine_mode} · ${health.store_backend}${health.livekit_ready ? " · livekit" : ""}`
              : "Connecting..."}
          </span>
          {clientTtfaMs !== null && (
            <span className={`nk-pill ${clientTtfaMs < 500 ? "emerald" : ""}`} style={{ fontVariantNumeric: "tabular-nums" }}>
              After transcript: {clientTtfaMs} ms
            </span>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <button
            type="button"
            className="nk-pill"
            title="Start a fresh conversation session"
            onClick={() => {
              endCall();
              responseGenRef.current += 1;
              pendingTurnRef.current = null;
              setSubmitting(false);
              localCallId.current = "";
              const nextSession = crypto.randomUUID();
              complaintSessionRef.current = nextSession;
              setSessionId(nextSession);
              setMessages([]);
              setLastTurn(null);
              setDraft(null);
              setPreviewPacket(null);
              setLocationStatus("");
              setLocationPending(false);
              setModalOk(false);
              setOtpSessionId("");
              setOtpDemoHint("");
              setOtpCode("");
              setOtpVerified(false);
              setHitlApproved(false);
              setHandoffAuthorized(false);
              setHitlStatus("");
              setAttachment(null);
            }}
          >
            New Call
          </button>
          <label
            title="DPDP Act 2023 voice processing consent"
            style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: "0.8rem", color: "var(--ink-2)", cursor: "pointer" }}
          >
            <input
              type="checkbox"
              checked={consentGranted}
              onChange={(e) => {
                const next = e.target.checked;
                consentRef.current = next;
                sessionStorage.setItem(CONSENT_KEY, next ? "granted" : "denied");
                setConsentGranted(next);
                if (!next) {
                  endCall();
                  responseGenRef.current += 1;
                  pendingTurnRef.current = null;
                  setSubmitting(false);
                  setDraft(null);
                  setLastTurn(null);
                  setPreviewPacket(null);
                  setHitlApproved(false);
                  setHandoffAuthorized(false);
                  setModalOk(false);
                  setLocationPending(false);
                  setLocationStatus("");
                }
                void fetch("/api/dpdp/consent", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ session_id: sessionId, consented: next }),
                }).catch(() => undefined);
              }}
            />
            Consent
          </label>
        </div>
      </div>

      {/* Voice Orb Carousel (Swipe/Click arrows or voice chips below to shift orb color & voice) */}
      <div className="nk-carousel-row">
        <button
          type="button"
          className="nk-carousel-arrow"
          aria-label="Previous voice"
          title="Previous voice"
          onClick={() => {
            const idx = voices.findIndex((v) => v.id === selectedVoice);
            const prev = (idx <= 0 ? voices.length - 1 : idx - 1);
            if (voices[prev]) setSelectedVoice(voices[prev].id);
          }}
        >
          <ChevronLeft size={20} />
        </button>

        <RiverOrb agentState={orbState} onClick={toggleMic} voiceTheme={getVoiceTheme(selectedVoice)} />

        <button
          type="button"
          className="nk-carousel-arrow"
          aria-label="Next voice"
          title="Next voice"
          onClick={() => {
            const idx = voices.findIndex((v) => v.id === selectedVoice);
            const next = (idx + 1) % Math.max(1, voices.length);
            if (voices[next]) setSelectedVoice(voices[next].id);
          }}
        >
          <ChevronRight size={20} />
        </button>
      </div>

      <div className="nk-voice-strip" role="listbox" aria-label="Voice Persona Carousel">
        {voices.map((v) => {
          const vt = getVoiceTheme(v.id);
          const active = v.id === selectedVoice;
          const shortName = v.label.split("·")[0].trim();
          return (
            <button
              key={v.id}
              type="button"
              role="option"
              aria-selected={active}
              title={v.label}
              className={`nk-voice-chip${active ? " active" : ""}`}
              onClick={() => setSelectedVoice(v.id)}
            >
              <span className="nk-voice-dot" style={{ background: vt.mid }} aria-hidden="true" />
              {shortName}
            </button>
          );
        })}
      </div>

      <LiveWaveform active={listening} speaking={speaking} />

      <div className="nk-dock" style={{ maxWidth: 440 }}>
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

      {/* Open-Canvas Conversation Stream */}
      <div
        className="nk-chat-stream"
        aria-live="polite"
        aria-label="Conversation transcript"
      >
        {messages.length === 0 && (
          <p style={{ margin: "6px 0", textAlign: "center", color: "var(--ink-3)", fontSize: "0.92rem" }}>
            Tap the orb or <strong>Start Call</strong> and speak naturally in Tamil or Tanglish.
          </p>
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

      {/* Attachment Preview Bar (if photo/PDF uploaded) */}
      {attachment && (
        <div className="nk-attachment-bar" role="status">
          <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
            {attachment.type === "document_pdf" ? <FileText size={16} /> : <ImageIcon size={16} />}
            <span style={{ fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {attachment.filename}
            </span>
            <span className={`nk-pill ${attachment.within_gcc_1mb_limit ? "emerald" : ""}`}>
              {attachment.size_kb} KB · {attachment.within_gcc_1mb_limit ? "< 1 MB OK" : "> 1 MB"}
            </span>
            {attachment.extracted_ticket && (
              <span className="nk-pill accent mono">{attachment.extracted_ticket}</span>
            )}
          </div>
          <button
            type="button"
            className="nk-attach-btn"
            aria-label="Remove attachment"
            title="Remove attachment"
            onClick={() => setAttachment(null)}
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* Pill Text Composer with Photo / PDF Upload */}
      <div className="nk-open-composer">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,.pdf"
          aria-label="Upload street photo or PDF bill"
          style={{ display: "none" }}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFileUpload(file);
            e.target.value = "";
          }}
        />
        <button
          type="button"
          className="nk-attach-btn"
          aria-label="Attach photo or PDF"
          title="Attach street photo or PDF bill (<1 MB GCC limit)"
          disabled={uploadingAttachment}
          onClick={() => fileInputRef.current?.click()}
        >
          <Paperclip size={18} />
        </button>
        <input
          type="text"
          aria-label="Civic complaint input"
          placeholder="Speak or type in Tamil / Tanglish..."
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") submitTurn(inputText);
          }}
        />
        <button type="button" className="nk-btn primary" disabled={submitting || !consentGranted} onClick={() => submitTurn(inputText)}>
          <Send size={15} />
          Send
        </button>
      </div>

      {draft && (
        <section className="nk-card nk-grievance" aria-labelledby="grievance-heading">
          <h2 id="grievance-heading">Grievance draft</h2>
          <strong>{draft.label} <span lang="ta">{draft.label_ta}</span></strong>
          <p>{draft.summary}</p>
          <dl>
            <div><dt>Incident location</dt><dd>{[draft.location.landmark || draft.location.street, draft.location.area, draft.location.ward].filter(Boolean).filter((item, index, all) => all.indexOf(item) === index).join(" · ") || "Awaiting a landmark"}</dd></div>
            <div><dt>{draft.location.ward ? "Filing channel" : "Referral channel"}</dt><dd>{draft.destination.name} · {draft.destination.helpline}</dd></div>
            {draft.duration_days !== null && <div><dt>Problem duration</dt><dd>{draft.duration_days} days</dd></div>}
            {draft.impact && <div><dt>Road passability</dt><dd>{draft.impact}</dd></div>}
          </dl>
          <ul className="nk-intake-checks" aria-label="Grievance checklist">
            {draft.checklist.checks.map((check) => <li key={check.label}>{check.label} · {check.complete ? "Complete" : "Pending"}</li>)}
          </ul>
          {draft.status === "needs_location" && (
            <div className="nk-grievance-actions">
              <button type="button" className="nk-btn" onClick={requestLocation} disabled={locationPending || submitting}>
                <MapPin size={16} /> Use my location
              </button>
              <p role="status">{locationStatus || "If you are at the incident, share GPS. You can also say or type a nearby landmark."}</p>
            </div>
          )}
          {draft.status === "cooldown" && <p>There is a recent request of this type for this ward.</p>}
          {draft.status === "needs_details" && <p>{draft.next_field === "impact"
            ? "Say or type whether the road is blocked, passable, or you are unsure."
            : "Chennai Metro Water asks how many days the problem has lasted. Say or type the number of days."}</p>}
          {draft.status === "needs_confirmation" && !hitlApproved && <p>{signedIn
            ? "Review the details and confirm by voice before opening a filing channel."
            : "Review the details and verify the demo code before confirming by voice."}</p>}
          <div className="nk-grievance-actions">
            <button type="button" className="nk-btn" onClick={() => {
              const duration = draft.duration_days === null ? "" : `Problem duration: ${draft.duration_days} days`;
              const text = [draft.label, draft.summary, draft.location.landmark, draft.location.street, draft.location.ward, duration, draft.impact].filter(Boolean).join("\n");
              void navigator.clipboard.writeText(text).then(() => setHitlStatus("Draft copied.")).catch(() => setHitlStatus("Could not copy the draft."));
            }}>Copy grievance draft</button>
            {signedIn && <button className="nk-btn" type="button" onClick={() => void saveToHistory()}>Save to My requests</button>}
          </div>
          {handoffAuthorized && draft.destination.url && (
            <div className="nk-grievance-actions">
              <a className="nk-btn primary" href={draft.destination.url} target="_blank" rel="noreferrer">Open official portal</a>
              {draft.checklist.whatsapp && <a className="nk-btn" href={draft.checklist.whatsapp} target="_blank" rel="noreferrer">Open WhatsApp</a>}
              {draft.checklist.email && <a className="nk-btn" href={`mailto:${draft.checklist.email}`}>Open email</a>}
            </div>
          )}
          {hitlStatus && <p role="status">{hitlStatus}</p>}
        </section>
      )}

      {/* Collapsible Sample Prompts & OTP/HITL Clarity Drawer */}
      <details style={{ width: "100%" }}>
        <summary style={{ cursor: "pointer", textAlign: "center", fontSize: "0.84rem", fontWeight: 600, color: "var(--ink-3)", padding: "6px 0" }}>
          Sample Prompts &amp; Citizen Verification (Optional)
        </summary>
        <div style={{ display: "flex", flexDirection: "column", gap: 14, marginTop: 12 }}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center" }}>
            {SAMPLE_PROMPTS.map((p) => (
              <button key={p} type="button" className="nk-pill" onClick={() => submitTurn(p)}>
                {p}
              </button>
            ))}
          </div>

          {draft?.status === "needs_confirmation" && !hitlApproved && <section
            className="nk-card"
            aria-live="assertive"
            style={{ borderColor: lastTurn?.fsm_state === "HITL_SEAL" ? "var(--emerald)" : "var(--border)" }}
          >
            <h2 style={{ margin: "0 0 12px", fontSize: "1rem", display: "flex", alignItems: "center", gap: 7 }}>
              <ShieldCheck size={18} />
              Citizen verification
            </h2>
            {!signedIn && <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", marginBottom: 12 }}>
              <input
                aria-label="Masked number for demo OTP"
                className="nk-input"
                style={{ width: 145 }}
                value={phoneMasked}
                onChange={(e) => setPhoneMasked(e.target.value)}
              />
              <button type="button" className="nk-btn" onClick={handleSendOtp} disabled={!phoneMasked.trim()}>
                Generate demo code
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
              {otpVerified && <span className="nk-pill emerald">Demo code verified</span>}
            </div>}

            <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
              <label style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: "0.86rem", cursor: "pointer" }}>
                <input type="checkbox" checked={modalOk} onChange={(e) => setModalOk(e.target.checked)} />
                I reviewed the grievance details
              </label>
              <span>Say “உறுதி” or “Confirm” once after review, or twice in separate voice turns.</span>
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
          </section>}
        </div>
      </details>
    </div>
  );
}

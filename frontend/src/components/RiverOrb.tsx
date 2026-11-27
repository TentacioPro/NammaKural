import { useEffect, useRef } from "react";
import { AlertTriangle, Mic, Pause, Sparkles } from "lucide-react";

export type OrbState = "idle" | "listening" | "thinking" | "talking" | "paused" | "urgent";

export interface OrbVoiceTheme {
  rgb: string;
  top: string;
  mid: string;
  bot: string;
}

interface RiverOrbProps {
  agentState: OrbState;
  onClick: () => void;
  voiceTheme?: OrbVoiceTheme;
}

const LABELS: Record<OrbState, { ta: string; en: string }> = {
  idle: { ta: "பேசுங்க", en: "Speak" },
  listening: { ta: "கேட்கிறேன்", en: "Listening" },
  thinking: { ta: "சரிபார்க்கிறேன்", en: "Checking" },
  talking: { ta: "பேசுகிறேன்", en: "Speaking" },
  paused: { ta: "நிறுத்தப்பட்டது", en: "Paused" },
  urgent: { ta: "அவசரம்", en: "Urgent" },
};

export function RiverOrb({ agentState, onClick, voiceTheme }: RiverOrbProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const stateRef = useRef<OrbState>(agentState);
  const themeRef = useRef<OrbVoiceTheme | undefined>(voiceTheme);
  stateRef.current = agentState;
  themeRef.current = voiceTheme;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let raf = 0;
    let phase = 0;
    let lastRipple = 0;
    const ripples: { r: number; alpha: number; speed: number }[] = [];
    const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;

    const draw = (ts = 0) => {
      const st = stateRef.current;
      const w = canvas.width;
      const h = canvas.height;
      const cx = w / 2;
      const cy = h / 2;
      ctx.clearRect(0, 0, w, h);

      const active = st === "listening" || st === "talking";
      const interval = st === "talking" ? 420 : st === "listening" ? 560 : 1850;
      if (!reduced && ts - lastRipple > interval) {
        ripples.push({ r: 74, alpha: active ? 0.48 : 0.25, speed: active ? 1.05 : 0.68 });
        if (ripples.length > 7) ripples.shift();
        lastRipple = ts;
      }

      const vt = themeRef.current;
      const rgb =
        st === "urgent" || st === "paused"
          ? "185, 28, 28"
          : st === "listening" || st === "talking"
            ? "4, 120, 87"
            : st === "thinking"
              ? "217, 119, 6"
              : (vt?.rgb ?? "30, 58, 138");

      if (!reduced) phase += active ? 0.045 : 0.015;

      for (let i = ripples.length - 1; i >= 0; i--) {
        const rp = ripples[i];
        if (!reduced) {
          rp.r += rp.speed;
          rp.alpha *= 0.974;
        }
        if (rp.alpha < 0.015 || rp.r > 122) {
          ripples.splice(i, 1);
          continue;
        }
        ctx.beginPath();
        for (let a = 0; a <= Math.PI * 2 + 0.08; a += 0.12) {
          const osc = Math.sin(a * 4 + phase * 1.1) * (active ? 2.5 : 0.8);
          const rad = rp.r + osc;
          const x = cx + Math.cos(a) * rad;
          const y = cy + Math.sin(a) * rad;
          if (a === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.strokeStyle = `rgba(${rgb}, ${rp.alpha.toFixed(3)})`;
        ctx.lineWidth = 1.75;
        ctx.stroke();
      }

      const amp = st === "talking" ? 11 : st === "listening" ? 8 : 3;
      const halo = ctx.createRadialGradient(cx, cy, 46, cx, cy, 108);
      halo.addColorStop(0, `rgba(${rgb}, 0.22)`);
      halo.addColorStop(1, "rgba(255,255,255,0)");
      ctx.fillStyle = halo;
      ctx.beginPath();
      ctx.arc(cx, cy, 108, 0, Math.PI * 2);
      ctx.fill();

      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, cy, 72, 0, Math.PI * 2);
      ctx.clip();

      const grad = ctx.createLinearGradient(cx - 60, cy - 64, cx + 62, cy + 66);
      if (st === "urgent" || st === "paused") {
        grad.addColorStop(0, "#EF4444");
        grad.addColorStop(1, "#B91C1C");
      } else if (st === "listening" || st === "talking") {
        grad.addColorStop(0, "#10B981");
        grad.addColorStop(1, "#047857");
      } else if (st === "thinking") {
        grad.addColorStop(0, "#FBBF24");
        grad.addColorStop(1, "#D97706");
      } else {
        grad.addColorStop(0, vt?.top ?? "#3B82F6");
        grad.addColorStop(0.55, vt?.mid ?? "#1E3A8A");
        grad.addColorStop(1, vt?.bot ?? "#0F766E");
        grad.addColorStop(1, "#0EA5E9");
      }
      ctx.fillStyle = grad;
      ctx.fillRect(cx - 76, cy - 76, 152, 152);

      ctx.beginPath();
      ctx.moveTo(cx - 76, cy + 76);
      for (let x = -76; x <= 76; x += 4) {
        const y = Math.sin(x * 0.07 + phase * 1.4) * (amp * 0.65) + Math.cos(x * 0.04 - phase) * (amp * 0.45);
        ctx.lineTo(cx + x, cy + 6 + y);
      }
      ctx.lineTo(cx + 76, cy + 76);
      ctx.closePath();
      ctx.fillStyle = "rgba(255, 255, 255, 0.24)";
      ctx.fill();

      const gloss = ctx.createRadialGradient(cx - 22, cy - 26, 5, cx - 16, cy - 22, 54);
      gloss.addColorStop(0, "rgba(255, 255, 255, 0.55)");
      gloss.addColorStop(1, "rgba(255, 255, 255, 0)");
      ctx.fillStyle = gloss;
      ctx.fillRect(cx - 74, cy - 74, 148, 148);
      ctx.restore();

      if (!reduced) raf = requestAnimationFrame(draw);
    };

    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, []);

  const lbl = LABELS[agentState];
  return (
    <div className="orb-wrap">
      <canvas ref={canvasRef} width={248} height={248} aria-hidden="true" style={{ position: "absolute", inset: 0, pointerEvents: "none" }} />
      <button type="button" className="orb-btn" data-state={agentState} onClick={onClick}>
        {agentState === "paused" ? <Pause size={24} /> : agentState === "urgent" ? <AlertTriangle size={24} /> : agentState === "thinking" ? <Sparkles size={24} /> : <Mic size={24} />}
        <span lang="ta">{lbl.ta}</span>
        <span>{lbl.en}</span>
      </button>
    </div>
  );
}

import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";

interface MetricBucket {
  count?: number;
  p50?: number;
  p90?: number;
  p95?: number;
  under_500ms_pct?: number;
}

interface TelemetrySummary {
  workflow?: MetricBucket;
  deterministic?: MetricBucket;
  llm_ttft?: MetricBucket;
  tts_synth?: MetricBucket;
  ttfa?: MetricBucket;
  observability?: Record<string, unknown>;
}

export default function TelemetryPage() {
  const [summary, setSummary] = useState<TelemetrySummary | null>(null);

  async function loadTelemetry() {
    try {
      const res = await fetch("/api/telemetry/summary");
      setSummary(await res.json());
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    loadTelemetry();
  }, []);

  const buckets: Array<{ label: string; data?: MetricBucket }> = [
    { label: "End-to-End TTFA", data: summary?.ttfa },
    { label: "Workflow Turn", data: summary?.workflow },
    { label: "Deterministic FSM", data: summary?.deterministic },
    { label: "TTS Synthesis", data: summary?.tts_synth },
    { label: "LLM TTFT (Fallback)", data: summary?.llm_ttft },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="nk-card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "1.2rem" }}>Latency &amp; TTFA Telemetry</h1>
          <p style={{ margin: "4px 0 0", fontSize: "0.86rem", color: "var(--ink-2)" }}>
            P50 / P90 / P95 latency breakdown targeting &lt; 500 ms TTFA.
          </p>
        </div>
        <button type="button" className="nk-btn primary" onClick={loadTelemetry}>
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 14 }}>
        {buckets.map((b) => (
          <section key={b.label} className="nk-card">
            <h2 style={{ margin: "0 0 8px", fontSize: "0.98rem" }}>{b.label}</h2>
            <div className="mono" style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: "0.86rem" }}>
              <div>Count: {b.data?.count ?? 0}</div>
              <div>P50: {b.data?.p50 !== undefined ? `${b.data.p50.toFixed(1)} ms` : "—"}</div>
              <div>P90: {b.data?.p90 !== undefined ? `${b.data.p90.toFixed(1)} ms` : "—"}</div>
              <div>P95: {b.data?.p95 !== undefined ? `${b.data.p95.toFixed(1)} ms` : "—"}</div>
              {b.data?.under_500ms_pct !== undefined && (
                <div style={{ color: "var(--emerald)", fontWeight: 700 }}>
                  &lt; 500ms: {b.data.under_500ms_pct.toFixed(1)}%
                </div>
              )}
            </div>
          </section>
        ))}
      </div>

      {summary?.observability && (
        <section className="nk-card">
          <h2 style={{ margin: "0 0 8px", fontSize: "1rem" }}>Observability Snapshot</h2>
          <pre className="mono" style={{ margin: 0, fontSize: "0.8rem", overflowX: "auto" }}>
            {JSON.stringify(summary.observability, null, 2)}
          </pre>
        </section>
      )}
    </div>
  );
}

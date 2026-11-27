import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Gauge, RefreshCw, Zap } from "lucide-react";

interface MetricBucket {
  count?: number;
  p50?: number | null;
  p90?: number | null;
  p95?: number | null;
  under_500ms_pct?: number | null;
}

interface VersionStats {
  events: number;
  workflow_count: number;
  workflow_p50: number | null;
  ttfa_p50: number | null;
  ttfa_p95: number | null;
  under_500ms_pct: number;
}

interface TelemetrySummary {
  agent_version?: string;
  telemetry_schema_version?: string;
  selected_version?: string;
  versions?: string[];
  by_version?: Record<string, VersionStats>;
  workflow?: MetricBucket;
  deterministic?: MetricBucket;
  llm_ttft?: MetricBucket;
  tts_synth?: MetricBucket;
  client_ttfa?: MetricBucket;
  ttfa?: MetricBucket;
  recent_events?: Array<Record<string, unknown>>;
}

function fmtMs(val?: number | null): string {
  return typeof val === "number" ? `${val.toFixed(1)} ms` : "—";
}

export default function TelemetryPage() {
  const [summary, setSummary] = useState<TelemetrySummary | null>(null);
  const [selectedVersion, setSelectedVersion] = useState<string>("all");
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);

  async function loadTelemetry(ver = selectedVersion) {
    try {
      const res = await fetch(`/api/telemetry/summary?version=${encodeURIComponent(ver)}`);
      setSummary(await res.json());
    } catch {
      // ignore offline fetch errors
    }
  }

  useEffect(() => {
    loadTelemetry(selectedVersion);
  }, [selectedVersion]);

  useEffect(() => {
    if (!autoRefresh) return undefined;
    const id = window.setInterval(() => loadTelemetry(selectedVersion), 5000);
    return () => window.clearInterval(id);
  }, [autoRefresh, selectedVersion]);

  const stages = [
    { name: "Deterministic FSM / NLU", p50: summary?.deterministic?.p50 ?? null, p95: summary?.deterministic?.p95 ?? null, count: summary?.deterministic?.count ?? 0, budget: 25 },
    { name: "LLM (Sarvam 105B)", p50: summary?.llm_ttft?.p50 ?? null, p95: summary?.llm_ttft?.p95 ?? null, count: summary?.llm_ttft?.count ?? 0, budget: 200 },
    { name: "TTS Stream TTFB (Bulbul v3)", p50: summary?.tts_synth?.p50 ?? null, p95: summary?.tts_synth?.p95 ?? null, count: summary?.tts_synth?.count ?? 0, budget: 250 },
    { name: "Browser Client TTFA", p50: summary?.client_ttfa?.p50 ?? null, p95: summary?.client_ttfa?.p95 ?? null, count: summary?.client_ttfa?.count ?? 0, budget: 500 },
  ];

  // Auto-detect biggest bottleneck among server stages
  const serverStages = stages.slice(0, 3).filter((s) => typeof s.p50 === "number");
  const bottleneck = serverStages.sort((a, b) => (b.p50 ?? 0) - (a.p50 ?? 0))[0];
  const underPct = summary?.ttfa?.under_500ms_pct ?? 0;
  const slaHealthy = underPct >= 50 && (summary?.ttfa?.p50 ?? 9999) <= 500;
  const versionEntries = Object.entries(summary?.by_version || {});
  const recentEvents = summary?.recent_events || [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      {/* Header & Controls */}
      <div className="nk-card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <h1 style={{ margin: 0, fontSize: "1.22rem" }}>Performance Insights &amp; SLA</h1>
            {summary?.agent_version && (
              <span className="nk-pill accent mono">{summary.agent_version}</span>
            )}
          </div>
          <p style={{ margin: "4px 0 0", fontSize: "0.85rem", color: "var(--ink-2)" }}>
            Target: <strong>P50 &lt; 500 ms TTFA</strong> · Schema {summary?.telemetry_schema_version || "—"}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <select
            aria-label="Filter by agent version"
            className="nk-select"
            value={selectedVersion}
            onChange={(e) => setSelectedVersion(e.target.value)}
          >
            <option value="all">All Versions ({summary?.versions?.length ?? 0})</option>
            {(summary?.versions || []).map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
          <label style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: "0.84rem", cursor: "pointer" }}>
            <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} />
            Live (5s)
          </label>
          <button type="button" className="nk-btn primary" onClick={() => loadTelemetry(selectedVersion)}>
            <RefreshCw size={15} />
            Refresh
          </button>
        </div>
      </div>

      {/* 3 Actionable Insight Hero Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: 14 }}>
        <section className="nk-card" style={{ borderColor: slaHealthy ? "var(--emerald)" : "var(--amber)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, fontWeight: 700, color: slaHealthy ? "var(--emerald)" : "var(--amber)" }}>
            {slaHealthy ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
            500 ms TTFA SLA
          </div>
          <div className="mono" style={{ fontSize: "1.65rem", fontWeight: 700 }}>{fmtMs(summary?.ttfa?.p50)}</div>
          <div style={{ fontSize: "0.84rem", color: "var(--ink-2)", marginTop: 4 }}>
            P95: <strong className="mono">{fmtMs(summary?.ttfa?.p95)}</strong> · Under 500ms: <strong className="mono">{underPct.toFixed(1)}%</strong>
          </div>
        </section>

        <section className="nk-card">
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, fontWeight: 700, color: "var(--crimson)" }}>
            <Zap size={18} />
            #1 Latency Bottleneck
          </div>
          <div style={{ fontSize: "1.12rem", fontWeight: 700 }}>
            {bottleneck ? bottleneck.name : "No uncached runs yet"}
          </div>
          <div style={{ fontSize: "0.84rem", color: "var(--ink-2)", marginTop: 4 }}>
            {bottleneck
              ? `P50 ${fmtMs(bottleneck.p50)} (P95 ${fmtMs(bottleneck.p95)}) vs ${bottleneck.budget} ms budget`
              : "Run a live voice turn to measure stage timings."}
          </div>
        </section>

        <section className="nk-card">
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, fontWeight: 700, color: "var(--accent)" }}>
            <Gauge size={18} />
            Browser vs Server
          </div>
          <div className="mono" style={{ fontSize: "1.65rem", fontWeight: 700 }}>{fmtMs(summary?.client_ttfa?.p50)}</div>
          <div style={{ fontSize: "0.84rem", color: "var(--ink-2)", marginTop: 4 }}>
            Client P95: <strong className="mono">{fmtMs(summary?.client_ttfa?.p95)}</strong> · Total Turns: <strong className="mono">{summary?.workflow?.count ?? 0}</strong>
          </div>
        </section>
      </div>

      {/* Visual Stage Waterfall vs 500 ms Target */}
      <section className="nk-card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
          <h2 style={{ margin: 0, fontSize: "1rem" }}>Stage Latency Waterfall (vs 500 ms Budget)</h2>
          <span className="nk-pill mono">Scale: 0 – 1000 ms</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {stages.map((st) => {
            const val = st.p50 ?? 0;
            const pct = Math.min(100, Math.round((val / 1000) * 100));
            const overBudget = val > st.budget;
            return (
              <div key={st.name} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", gap: 8 }}>
                  <span><strong>{st.name}</strong> <span style={{ color: "var(--ink-3)" }}>({st.count} samples · budget ≤ {st.budget} ms)</span></span>
                  <span className="mono" style={{ fontWeight: 700, color: overBudget ? "var(--crimson)" : "var(--emerald)" }}>
                    P50 {fmtMs(st.p50)} · P95 {fmtMs(st.p95)}
                  </span>
                </div>
                <div style={{ height: 10, borderRadius: 999, background: "var(--surface-2)", position: "relative", overflow: "hidden" }}>
                  <div
                    style={{
                      width: `${pct}%`,
                      height: "100%",
                      borderRadius: 999,
                      background: overBudget ? "var(--crimson)" : "var(--emerald)",
                      transition: "width 0.3s ease",
                    }}
                  />
                  <div
                    title="500 ms target"
                    style={{ position: "absolute", left: "50%", top: 0, bottom: 0, width: 2, background: "var(--ink-2)", opacity: 0.45 }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Version Comparison Table */}
      <section className="nk-card" style={{ overflowX: "auto" }}>
        <h2 style={{ margin: "0 0 10px", fontSize: "1rem" }}>Version-over-Version Comparison</h2>
        <table className="nk-table">
          <thead>
            <tr>
              <th>Agent Version</th>
              <th>Events</th>
              <th>Turns</th>
              <th>Workflow P50</th>
              <th>TTFA P50</th>
              <th>TTFA P95</th>
              <th>&lt; 500ms SLA</th>
            </tr>
          </thead>
          <tbody>
            {versionEntries.map(([ver, st]) => (
              <tr key={ver}>
                <td className="mono">{ver}</td>
                <td className="mono">{st.events}</td>
                <td className="mono">{st.workflow_count}</td>
                <td className="mono">{fmtMs(st.workflow_p50)}</td>
                <td className="mono">{fmtMs(st.ttfa_p50)}</td>
                <td className="mono">{fmtMs(st.ttfa_p95)}</td>
                <td className="mono">{st.under_500ms_pct.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* Collapsible Raw Datapoints */}
      <details className="nk-card">
        <summary style={{ cursor: "pointer", fontWeight: 700, fontSize: "0.96rem" }}>
          Recent Versioned Datapoints ({recentEvents.length})
        </summary>
        <div style={{ overflowX: "auto", marginTop: 12 }}>
          <table className="nk-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Agent Version</th>
                <th>Stage</th>
                <th>Latency</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {recentEvents.map((ev, idx) => {
                const data = (ev.data || {}) as Record<string, unknown>;
                const ms = data.latency_ms;
                return (
                  <tr key={idx}>
                    <td className="mono">{String(ev.time || ev.ts || "—")}</td>
                    <td className="mono">{String(ev.agent_version || "0.2.0-legacy")}</td>
                    <td className="mono">{String(ev.stage || "—")}</td>
                    <td className="mono">{typeof ms === "number" ? `${ms.toFixed(1)} ms` : "—"}</td>
                    <td>{String(ev.message || "—")}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}

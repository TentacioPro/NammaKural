import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";

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
  observability?: Record<string, unknown>;
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

  const buckets: Array<{ label: string; data?: MetricBucket }> = [
    { label: "Server TTFA (Turn + TTS)", data: summary?.ttfa },
    { label: "Browser Client TTFA", data: summary?.client_ttfa },
    { label: "Workflow Turn (LangGraph)", data: summary?.workflow },
    { label: "TTS Synthesis", data: summary?.tts_synth },
    { label: "LLM TTFT", data: summary?.llm_ttft },
    { label: "Deterministic Fallback", data: summary?.deterministic },
  ];

  const versionEntries = Object.entries(summary?.by_version || {});
  const recentEvents = summary?.recent_events || [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      <div className="nk-card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <h1 style={{ margin: 0, fontSize: "1.2rem" }}>Versioned Telemetry &amp; SLA Dashboard</h1>
            {summary?.agent_version && (
              <span className="nk-pill accent mono">active: {summary.agent_version}</span>
            )}
          </div>
          <p style={{ margin: "4px 0 0", fontSize: "0.86rem", color: "var(--ink-2)" }}>
            Live P50 / P90 / P95 breakdown across agent versions · Schema {summary?.telemetry_schema_version || "—"}
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

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: 14 }}>
        {buckets.map((b) => (
          <section key={b.label} className="nk-card">
            <h2 style={{ margin: "0 0 8px", fontSize: "0.96rem" }}>{b.label}</h2>
            <div className="mono" style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: "0.85rem" }}>
              <div>Count: {b.data?.count ?? 0}</div>
              <div>P50: {typeof b.data?.p50 === "number" ? `${b.data.p50.toFixed(1)} ms` : "—"}</div>
              <div>P90: {typeof b.data?.p90 === "number" ? `${b.data.p90.toFixed(1)} ms` : "—"}</div>
              <div>P95: {typeof b.data?.p95 === "number" ? `${b.data.p95.toFixed(1)} ms` : "—"}</div>
              {typeof b.data?.under_500ms_pct === "number" && (
                <div style={{ color: "var(--emerald)", fontWeight: 700 }}>
                  &lt; 500ms: {b.data.under_500ms_pct.toFixed(1)}%
                </div>
              )}
            </div>
          </section>
        ))}
      </div>

      <section className="nk-card" style={{ overflowX: "auto" }}>
        <h2 style={{ margin: "0 0 10px", fontSize: "1rem" }}>Metrics by Agent Version</h2>
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
                <td className="mono">{typeof st.workflow_p50 === "number" ? `${st.workflow_p50.toFixed(1)} ms` : "—"}</td>
                <td className="mono">{typeof st.ttfa_p50 === "number" ? `${st.ttfa_p50.toFixed(1)} ms` : "—"}</td>
                <td className="mono">{typeof st.ttfa_p95 === "number" ? `${st.ttfa_p95.toFixed(1)} ms` : "—"}</td>
                <td className="mono">{st.under_500ms_pct.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="nk-card" style={{ overflowX: "auto" }}>
        <h2 style={{ margin: "0 0 10px", fontSize: "1rem" }}>Recent Versioned Datapoints ({recentEvents.length})</h2>
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
      </section>
    </div>
  );
}

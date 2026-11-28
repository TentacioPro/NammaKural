import { useState } from "react";
import { Link } from "react-router-dom";

interface EvalReport {
  available: boolean;
  pass_count: number;
  total: number;
  elapsed_ms: number;
  build: string;
  failures: { id: string; issues: string[] }[];
}

export default function DebugPage() {
  const [report, setReport] = useState<EvalReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function evaluate() {
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/ops/evaluate", { method: "POST" });
      if (!response.ok) throw new Error();
      const result: EvalReport = await response.json();
      if (!result.available) {
        setError("The golden cases are unavailable in this deployment.");
        return;
      }
      setReport(result);
    } catch {
      setError("Could not run the regression cases.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="nk-telemetry">
      <header><h1>Agent experiments</h1><p>Check whether a change improves civic intake before testing it in a live call.</p></header>
      <section className="nk-card nk-telemetry-panel">
        <div className="nk-telemetry-header">
          <div><h2>Golden regression cases</h2><p>Deterministic replay of routing, ward resolution, corrections and safety.</p></div>
          <button className="nk-btn primary" type="button" disabled={busy} onClick={() => void evaluate()}>
            {busy ? "Running cases…" : "Run golden cases"}
          </button>
        </div>
        {error && <p role="status">{error}</p>}
        {report && <div role="status">
          <p><strong>{report.pass_count}/{report.total} passed</strong> · {report.elapsed_ms} ms for the suite{report.build && ` · ${report.build}`}</p>
          {report.failures.map((failure) => <details key={failure.id}>
            <summary>{failure.id}</summary><ul>{failure.issues.map((issue) => <li key={issue}>{issue}</li>)}</ul>
          </details>)}
          <p>This replay exercises the workflow with text fixtures. It does not score microphone quality or playback latency.</p>
        </div>}
      </section>
      <section className="nk-card nk-telemetry-panel">
        <h2>Review a live failure</h2>
        <p>Find the first unresolved intent, location or required detail before tuning provider latency.</p>
        <div className="nk-grievance-actions"><Link to="/traces">Inspect turn traces</Link><Link to="/channels">Review channel requirements</Link></div>
      </section>
    </div>
  );
}

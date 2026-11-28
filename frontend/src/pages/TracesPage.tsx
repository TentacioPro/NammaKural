import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

interface Event {
  stage: string;
  ts: number;
  data: Record<string, number | string>;
}
interface TraceData {
  calls: { id: string; first_ts: number; turn_count: number; draft_status?: string }[];
  selected_call: { id: string; turns: { id: string; events: Event[] }[] } | null;
}

const clock = new Intl.DateTimeFormat("en-IN", { timeZone: "Asia/Kolkata", dateStyle: "medium", timeStyle: "medium" });

function label(value: string) {
  return value.replace(/[._]/g, " ");
}

export default function TracesPage() {
  const [selected, setSelected] = useState("");
  const [trace, setTrace] = useState<TraceData | null>(null);
  const [filter, setFilter] = useState<"all" | "location" | "details" | "errors">("all");
  const [revision, setRevision] = useState(0);
  const [error, setError] = useState(false);

  useEffect(() => {
    const abort = new AbortController();
    const path = selected ? `/api/telemetry/runs?call_id=${encodeURIComponent(selected)}` : "/api/telemetry/runs";
    void fetch(path, { signal: abort.signal, cache: "no-store" }).then((response) => {
      if (!response.ok) throw new Error();
      return response.json();
    }).then((data) => { setTrace(data); setError(false); })
      .catch(() => { if (!abort.signal.aborted) setError(true); });
    return () => abort.abort();
  }, [selected, revision]);

  const turns = trace?.selected_call?.turns.map((turn, index) => ({
    ...turn, index, workflow: turn.events.find((event) => event.stage === "call.workflow")?.data,
  })).filter((turn) => filter === "all" || (
    filter === "location" ? turn.workflow?.draft_status === "needs_location" :
      filter === "details" ? turn.workflow?.draft_status === "needs_details" :
        turn.events.some((event) => event.stage.endsWith("error") || event.stage.endsWith("fallback"))
  )) ?? [];

  return (
    <div className="nk-telemetry">
      <header><h1>Turn traces</h1><p>Inspect routing and timing by turn. Citizen transcripts and coordinates are excluded from this view.</p></header>
      <section className="nk-card nk-telemetry-panel">
        <div className="nk-grievance-actions">
          <select className="nk-select" aria-label="Choose trace call" value={selected} onChange={(event) => setSelected(event.target.value)}>
            <option value="">Latest call</option>
            {trace?.calls.map((call) => <option key={call.id} value={call.id}>{clock.format(call.first_ts * 1000)} · {call.turn_count} turns</option>)}
          </select>
          <select className="nk-select" aria-label="Filter turns" value={filter} onChange={(event) => setFilter(event.target.value as typeof filter)}>
            <option value="all">All turns</option><option value="location">Location pending</option>
            <option value="details">Details pending</option><option value="errors">Provider error or fallback</option>
          </select>
          <button type="button" className="nk-btn" onClick={() => setRevision((value) => value + 1)}>Refresh</button>
          {trace?.selected_call && <Link to={`/telemetry?call=${trace.selected_call.id}`}>Compare timing</Link>}
        </div>
        {error && <p role="status">Could not load turn traces.</p>}
        {!error && !trace && <p role="status">Loading turn traces…</p>}
        {!error && trace && !turns.length && <p>No turns match this filter.</p>}
      </section>
      {turns.map((turn) => (
        <details className="nk-card nk-telemetry-panel" key={turn.id} open={turn.index === 0 ? true : undefined}>
          <summary><strong>Turn {turn.index + 1}</strong> · {turn.workflow?.draft_status ? label(String(turn.workflow.draft_status)) : "No draft decision"}
            {turn.workflow?.destination ? ` · ${label(String(turn.workflow.destination))}` : ""}</summary>
          <div className="nk-telemetry-table" tabIndex={0} role="region" aria-label={`Spans for turn ${turn.index + 1}`}>
            <table className="nk-table">
              <thead><tr><th>Stage</th><th>Elapsed in turn</th><th>Recorded values</th></tr></thead>
              <tbody>{turn.events.map((event, index) => <tr key={index}>
                <th scope="row">{label(event.stage)}</th>
                <td>{Math.max(0, Math.round((event.ts - turn.events[0].ts) * 1000))} ms</td>
                <td>{Object.entries(event.data).map(([key, value]) => `${label(key)}: ${value}`).join(" · ") || "—"}</td>
              </tr>)}</tbody>
            </table>
          </div>
        </details>
      ))}
    </div>
  );
}

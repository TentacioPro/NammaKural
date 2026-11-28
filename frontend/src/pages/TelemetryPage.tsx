import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";

interface Cohort {
  day: string;
  version: string;
  build: string;
  metric: "legacy_playback" | "post_transcript" | "speech_to_playback";
  count: number;
  p50: number | null;
  p95: number | null;
}

interface Run {
  id: string;
  first_ts: number;
  version: string;
  build: string;
  duration_ms: number | null;
  turn_count: number;
}

interface Turn {
  id: string;
  ts: number;
  events: { stage: string; ts: number; data: Record<string, number | string> }[];
}

interface Telemetry {
  history: Cohort[];
  calls: Run[];
  selected_call: (Omit<Run, "turn_count"> & { turns: Turn[] }) | null;
  recent?: { calls_with_drafts: number; ready_for_review: number; waiting_location: number; waiting_details: number; cooldown: number; turns_to_review_p50: number | null };
}

const clock = new Intl.DateTimeFormat("en-IN", {
  timeZone: "Asia/Kolkata", day: "numeric", month: "short",
  hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
});

function ms(value?: number | null) {
  return value == null ? "—" : `${Math.round(value).toLocaleString()} ms`;
}

function callLength(value: number | null) {
  if (value === null) return "End time unavailable";
  const seconds = Math.floor(value / 1000);
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

export default function TelemetryPage() {
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState<Telemetry | null>(null);
  const selection = params.get("call") || "";
  const [refreshKey, setRefreshKey] = useState(0);
  const [live, setLive] = useState(true);
  const [error, setError] = useState(false);
  const [metric, setMetric] = useState<Cohort["metric"]>("legacy_playback");

  useEffect(() => {
    const abort = new AbortController();
    const url = selection ? `/api/telemetry/runs?call_id=${encodeURIComponent(selection)}` : "/api/telemetry/runs";
    async function load() {
      try {
        const response = await fetch(url, { signal: abort.signal, cache: "no-store" });
        if (!response.ok) throw new Error("Telemetry request failed");
        const result: Telemetry = await response.json();
        if (abort.signal.aborted) return;
        setData(result);
        setError(false);
      } catch {
        if (!abort.signal.aborted) setError(true);
      }
    }

    void load();
    const timer = live ? window.setInterval(load, 5000) : undefined;
    return () => {
      abort.abort();
      window.clearInterval(timer);
    };
  }, [selection, refreshKey, live]);

  const run = data?.selected_call;
  const history = data?.history.filter((entry) => entry.metric === metric) ?? [];

  return (
    <div className="nk-telemetry">
      <header className="nk-telemetry-header">
        <div>
          <h1>Call telemetry</h1>
          <p>Compare recorded timings and inspect individual turns. Times are shown in IST.</p>
        </div>
        <div className="nk-telemetry-controls">
          <label><input type="checkbox" checked={live} onChange={(event) => setLive(event.target.checked)} /> Auto-refresh</label>
          <button type="button" className="nk-btn" onClick={() => setRefreshKey((key) => key + 1)}><RefreshCw size={16} /> Refresh</button>
        </div>
      </header>
      {error && <p role="status">Telemetry couldn’t refresh. Use Refresh to retry.</p>}
      {!data && !error && <p role="status">Loading call history…</p>}
      {data?.recent && data.recent.calls_with_drafts > 0 && (
        <section className="nk-card nk-telemetry-panel" aria-labelledby="outcome-heading">
          <h2 id="outcome-heading">Where recent calls stopped</h2>
          <p>Latest observed draft state in {data.recent.calls_with_drafts} instrumented calls.</p>
          <dl className="nk-outcome-list">
            <div><dt>Ready for review</dt><dd>{data.recent.ready_for_review}</dd></div>
            <div><dt>Location pending</dt><dd>{data.recent.waiting_location}</dd></div>
            <div><dt>Details pending</dt><dd>{data.recent.waiting_details}</dd></div>
            <div><dt>Cooldown</dt><dd>{data.recent.cooldown}</dd></div>
            <div><dt>Median turns to review</dt><dd>{data.recent.turns_to_review_p50 ?? "—"}</dd></div>
          </dl>
          <div className="nk-grievance-actions"><Link to="/traces">Inspect turn traces</Link><Link to="/debug">Run regression cases</Link></div>
        </section>
      )}

      <section className="nk-card nk-telemetry-panel" aria-labelledby="run-heading">
        <div className="nk-telemetry-header">
          <div>
            <h2 id="run-heading">Call detail</h2>
            {run && <p>{clock.format(run.first_ts * 1000)} IST · {callLength(run.duration_ms)} · {run.turns.length} turns · {run.version}{run.build && ` · ${run.build}`}</p>}
          </div>
          {Boolean(data?.calls.length) && (
            <select className="nk-select" aria-label="Choose call" value={selection} onChange={(event) =>
              setParams(event.target.value ? { call: event.target.value } : {}, { replace: true })}>
              <option value="">Latest call</option>
              {data?.calls.map((call) => (
                <option value={call.id} key={call.id}>{clock.format(call.first_ts * 1000)} · {call.turn_count} turns</option>
              ))}
            </select>
          )}
        </div>
        {data && !run && <p>Calls and text turns recorded with the new instrumentation will appear here. Earlier timings are in the history below.</p>}
        {run?.turns.length === 0 && <p>Waiting for the first recorded turn.</p>}
        {run && run.turns.length > 0 && (
          <>
            <div className="nk-telemetry-table" tabIndex={0} role="region" aria-label="Timing and usage per turn">
              <table className="nk-table">
                <thead><tr><th>Turn</th><th>Speech → playback</th><th>Input → playback</th><th>Silence wait</th><th>STT</th><th>Workflow</th><th>Model</th><th>TTS first bytes</th><th>Usage</th></tr></thead>
                <tbody>
                  {run.turns.map((turn, index) => {
                    const stage = (name: string) => turn.events.find((event) => event.stage === name)?.data;
                    const playback = stage("call.playback");
                    const upload = stage("call.upload");
                    const workflow = stage("call.workflow");
                    const model = stage("llm.fast_turn");
                    const value = (event: typeof playback, key: string) =>
                      typeof event?.[key] === "number" ? event[key] : undefined;
                    const total = (key: string) => {
                      const values = turn.events.map((event) => value(event.data, key)).filter((item): item is number => item !== undefined);
                      return values.length ? values.reduce((sum, item) => sum + item, 0) : undefined;
                    };
                    const chars = total("submitted_chars");
                    const prompt = total("prompt_tokens");
                    const completion = total("completion_tokens");
                    const cached = total("cached_tokens");
                    const audio = value(upload, "recorded_audio_ms");
                    const usage = [
                      audio === undefined ? "" : `~${(audio / 1000).toFixed(1)} s audio`,
                      chars === undefined ? "" : `${chars} TTS chars`,
                      prompt === undefined ? "" : `${prompt} input tokens${cached === undefined ? "" : ` (${cached} cached)`}`,
                      completion === undefined ? "" : `${completion} output tokens`,
                    ].filter(Boolean);
                    return (
                      <tr key={turn.id}>
                        <th scope="row">{index + 1} · {String(playback?.modality || upload?.modality || workflow?.modality || "turn")}</th>
                        <td>{ms(value(playback, "speech_to_playback_ms"))}</td>
                        <td>{ms(value(playback, "post_transcript_ms"))}</td>
                        <td>{ms(value(playback, "endpoint_wait_ms") ?? value(upload, "endpoint_wait_ms"))}</td>
                        <td>{ms(value(playback, "browser_stt_ms") ?? value(stage("stt.sarvam_saaras"), "latency_ms"))}</td>
                        <td>{ms(value(workflow, "latency_ms"))}</td>
                        <td>{model ? <>{ms(value(model, "latency_ms"))}<br />{String(model.model || "")}</> : "—"}</td>
                        <td>{ms(value(stage("tts.sarvam_stream_ttfb"), "latency_ms"))}</td>
                        <td>{usage.length ? usage.join(" · ") : "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <p>Audio usage is estimated from browser recording time. Blank cells mean the signal was unavailable. The workflow total includes any model call.</p>
          </>
        )}
      </section>

      <section className="nk-card nk-telemetry-panel" aria-labelledby="history-heading">
        <div className="nk-telemetry-header">
          <div>
            <h2 id="history-heading">Latency history</h2>
            <p>Daily samples grouped by recorded agent version and build.</p>
          </div>
          <select className="nk-select" aria-label="Choose latency measurement" value={metric} onChange={(event) => setMetric(event.target.value as Cohort["metric"])}>
            <option value="legacy_playback">Earlier playback measurements</option>
            <option value="post_transcript">Transcript → playback</option>
            <option value="speech_to_playback">Speech → playback</option>
          </select>
        </div>
        <p>{metric === "legacy_playback" ? "Earlier samples use the browser’s play event and have no call or turn ID."
          : metric === "post_transcript" ? "Voice turns only. Starts when the transcript is submitted."
          : "Starts at the browser’s estimated end of speech and includes recognition and playback startup."}</p>
        {data && !history.length && <p>No samples for this measurement.</p>}
        {history.length > 0 && (
          <div className="nk-telemetry-table" tabIndex={0} role="region" aria-label="Daily latency by build">
            <table className="nk-table">
              <thead><tr><th>Date (IST)</th><th>Agent version</th><th>Build</th><th>Samples</th><th>P50</th><th>P95</th></tr></thead>
              <tbody>{history.map((entry) => (
                <tr key={`${entry.day}-${entry.version}-${entry.build}`}>
                  <th scope="row">{entry.day}</th><td>{entry.version}</td><td>{entry.build || "Unrecorded"}</td>
                  <td>{entry.count}</td><td>{ms(entry.p50)}</td><td>{ms(entry.p95)}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

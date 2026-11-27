import { useEffect, useState } from "react";
import { RefreshCw, Trash2 } from "lucide-react";

export default function TracesPage() {
  const [logs, setLogs] = useState<Array<Record<string, unknown>>>([]);
  const [convs, setConvs] = useState<Array<Record<string, unknown>>>([]);

  async function loadAll() {
    try {
      const [lRes, cRes] = await Promise.all([fetch("/api/logs?limit=80"), fetch("/api/conversations?limit=60")]);
      const lJson = await lRes.json();
      const cJson = await cRes.json();
      setLogs(Array.isArray(lJson) ? lJson : lJson.items || lJson.logs || []);
      setConvs(Array.isArray(cJson) ? cJson : cJson.items || cJson.conversations || []);
    } catch {
      // ignore offline fetch errors
    }
  }

  async function clearLogs() {
    await fetch("/api/logs", { method: "DELETE" });
    loadAll();
  }

  useEffect(() => {
    loadAll();
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="nk-card" style={{ display: "flex", flexWrap: "wrap", gap: 10, justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "1.2rem" }}>Turn Traces &amp; Conversations</h1>
          <p style={{ margin: "4px 0 0", fontSize: "0.86rem", color: "var(--ink-2)" }}>
            Redacted JSONL event stream from `logs/nammakural.jsonl` and `logs/conversations.jsonl`.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button type="button" className="nk-btn primary" onClick={loadAll}>
            <RefreshCw size={16} />
            Reload
          </button>
          <button type="button" className="nk-btn danger" onClick={clearLogs}>
            <Trash2 size={16} />
            Clear Logs
          </button>
        </div>
      </div>

      <section className="nk-card" style={{ overflowX: "auto" }}>
        <h2 style={{ margin: "0 0 10px", fontSize: "1rem" }}>Recent Event Logs ({logs.length})</h2>
        <table className="nk-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Event / Stage</th>
              <th>Latency (ms)</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {logs.slice(0, 40).map((row, i) => {
              const data = (row.data || {}) as Record<string, unknown>;
              const latency = data.latency_ms ?? row.latency_ms;
              return (
                <tr key={i}>
                  <td className="mono">{String(row.time || row.ts || row.timestamp || "—")}</td>
                  <td className="mono">{String(row.stage || row.event || row.fsm_state || "turn")}</td>
                  <td className="mono">{latency !== undefined ? String(latency) : "—"}</td>
                  <td className="mono" style={{ maxWidth: 420, wordBreak: "break-word" }}>
                    {JSON.stringify(row)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      <section className="nk-card" style={{ overflowX: "auto" }}>
        <h2 style={{ margin: "0 0 10px", fontSize: "1rem" }}>Conversation Turns ({convs.length})</h2>
        <table className="nk-table">
          <thead>
            <tr>
              <th>Time / Session</th>
              <th>Role</th>
              <th>Text</th>
              <th>State / Ward</th>
            </tr>
          </thead>
          <tbody>
            {convs.slice(0, 30).map((c, i) => (
              <tr key={i}>
                <td className="mono">{String(c.time || c.session_id || "—")}</td>
                <td className="mono">{String(c.role || "—")}</td>
                <td>{String(c.text || c.user_text || c.reply || c.display_text || "—")}</td>
                <td className="mono">
                  {String(c.fsm_state || "—")}
                  {c.ward ? ` · ${String(c.ward)}` : ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

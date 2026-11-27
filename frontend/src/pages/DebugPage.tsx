import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";

interface DebugSessionData {
  session_id: string;
  state_code: string;
  store_backend: string;
  slots: Record<string, unknown>;
  dynamic_keyterms: string[];
}

export default function DebugPage() {
  const [sessionId, setSessionId] = useState("browser");
  const [data, setData] = useState<DebugSessionData | null>(null);
  const [error, setError] = useState("");

  async function loadDebug() {
    setError("");
    try {
      const res = await fetch(`/api/debug/session?session_id=${encodeURIComponent(sessionId)}&state_code=tn`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setData(await res.json());
    } catch (err) {
      setError(String(err));
    }
  }

  useEffect(() => {
    loadDebug();
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="nk-card" style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "1.2rem" }}>Session &amp; Keyterm Debugger</h1>
          <p style={{ margin: "4px 0 0", fontSize: "0.86rem", color: "var(--ink-2)" }}>
            Inspect live Redis/Memory slot state, complaint version, and Sarvam dynamic keyterms.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            aria-label="Session ID"
            className="nk-input"
            value={sessionId}
            onChange={(e) => setSessionId(e.target.value)}
          />
          <button type="button" className="nk-btn primary" onClick={loadDebug}>
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>
      </div>

      {error && <div className="nk-card" style={{ color: "var(--crimson)" }}>{error}</div>}

      {data && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 16 }}>
          <section className="nk-card">
            <h2 style={{ margin: "0 0 8px", fontSize: "1rem" }}>Store &amp; Dynamic Keyterms</h2>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
              <span className="nk-pill">Store: {data.store_backend}</span>
              <span className="nk-pill">State: {data.state_code}</span>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {data.dynamic_keyterms.map((kt) => (
                <span key={kt} className="nk-pill mono">{kt}</span>
              ))}
            </div>
          </section>

          <section className="nk-card">
            <h2 style={{ margin: "0 0 8px", fontSize: "1rem" }}>Active Slots JSON</h2>
            <pre className="mono" style={{ margin: 0, fontSize: "0.8rem", overflowX: "auto" }}>
              {JSON.stringify(data.slots, null, 2)}
            </pre>
          </section>
        </div>
      )}
    </div>
  );
}

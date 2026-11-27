import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { Activity, Bug, ListTree, Mic, Moon, Sun } from "lucide-react";
import VoiceAgentPage from "./pages/VoiceAgentPage";
import DebugPage from "./pages/DebugPage";
import TracesPage from "./pages/TracesPage";
import TelemetryPage from "./pages/TelemetryPage";

export default function App() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
  }, [dark]);

  return (
    <>
      <header className="nk-nav">
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <strong style={{ fontSize: "1.05rem" }}>நம்ம குரல் · NammaKural</strong>
          <span className="nk-pill">Tamil / Tanglish Civic Voice Agent</span>
        </div>

        <nav className="nk-nav-links" aria-label="Primary">
          <NavLink to="/" end className={({ isActive }) => `nk-tab${isActive ? " active" : ""}`}>
            <Mic size={16} />
            Voice Agent
          </NavLink>
          <NavLink to="/debug" className={({ isActive }) => `nk-tab${isActive ? " active" : ""}`}>
            <Bug size={16} />
            Debug
          </NavLink>
          <NavLink to="/traces" className={({ isActive }) => `nk-tab${isActive ? " active" : ""}`}>
            <ListTree size={16} />
            Traces
          </NavLink>
          <NavLink to="/telemetry" className={({ isActive }) => `nk-tab${isActive ? " active" : ""}`}>
            <Activity size={16} />
            Telemetry
          </NavLink>
          <button
            type="button"
            className="nk-tab"
            aria-label={dark ? "Switch to Daylight theme" : "Switch to Dark theme"}
            onClick={() => setDark((d) => !d)}
          >
            {dark ? <Sun size={16} /> : <Moon size={16} />}
            {dark ? "Daylight" : "Dark"}
          </button>
        </nav>
      </header>

      <main className="nk-main">
        <Routes>
          <Route path="/" element={<VoiceAgentPage />} />
          <Route path="/debug" element={<DebugPage />} />
          <Route path="/traces" element={<TracesPage />} />
          <Route path="/telemetry" element={<TelemetryPage />} />
        </Routes>
      </main>
    </>
  );
}

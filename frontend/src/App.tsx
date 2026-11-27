import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { Activity, Bug, ExternalLink, ListTree, Mic, Moon, Sun } from "lucide-react";
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
        <div className="nk-brand">
          <span className="nk-brand-dot" aria-hidden="true" />
          <strong style={{ fontSize: "1.08rem", letterSpacing: "-0.01em" }}>நம்ம குரல் · NammaKural</strong>
          <span className="nk-pill">Tamil / Tanglish Voice AI</span>
        </div>

        <nav className="nk-nav-links" aria-label="Primary">
          <NavLink to="/" end className={({ isActive }) => `nk-tab${isActive ? " active" : ""}`}>
            <Mic size={15} />
            Voice Studio
          </NavLink>
          <NavLink to="/debug" className={({ isActive }) => `nk-tab${isActive ? " active" : ""}`}>
            <Bug size={15} />
            Debug
          </NavLink>
          <NavLink to="/traces" className={({ isActive }) => `nk-tab${isActive ? " active" : ""}`}>
            <ListTree size={15} />
            Traces
          </NavLink>
          <NavLink to="/telemetry" className={({ isActive }) => `nk-tab${isActive ? " active" : ""}`}>
            <Activity size={15} />
            Telemetry
          </NavLink>
          <a
            href="http://localhost:6006"
            target="_blank"
            rel="noreferrer"
            className="nk-tab"
            title="Open Arize Phoenix OTel & Eval Dashboard"
          >
            <ExternalLink size={14} />
            Phoenix
          </a>
          <button
            type="button"
            className="nk-tab"
            aria-label={dark ? "Switch to Daylight theme" : "Switch to Dark theme"}
            onClick={() => setDark((d) => !d)}
          >
            {dark ? <Sun size={15} /> : <Moon size={15} />}
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

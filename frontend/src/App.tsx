import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { Activity, Bug, ExternalLink, ListTree, Mic, Moon, Sun } from "lucide-react";
import VoiceAgentPage from "./pages/VoiceAgentPage";
import DebugPage from "./pages/DebugPage";
import TracesPage from "./pages/TracesPage";
import TelemetryPage from "./pages/TelemetryPage";
import { ChannelsPage, RequestsPage, SignInPage, type AuthStatus } from "./pages/CitizenPages";

export default function App() {
  const [dark, setDark] = useState(false);
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  const [authError, setAuthError] = useState(false);

  async function checkSignIn() {
    try {
      const response = await fetch("/api/auth/status", { cache: "no-store" });
      if (!response.ok) throw new Error();
      setAuth(await response.json());
      setAuthError(false);
    } catch {
      setAuthError(true);
    }
  }

  useEffect(() => {
    void checkSignIn();
    const timer = window.setInterval(checkSignIn, 60_000);
    return () => window.clearInterval(timer);
  }, []);

  async function signOut() {
    try {
      const response = await fetch("/api/auth/signout", { method: "POST" });
      if (!response.ok) throw new Error();
      sessionStorage.removeItem("nammakural.complaint");
      await checkSignIn();
    } catch {
      setAuthError(true);
    }
  }

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
  }, [dark]);

  if (!auth || (auth.required && !auth.signed_in)) {
    return <main className="nk-main">
      {authError && <button className="nk-btn" onClick={() => void checkSignIn()}>Retry sign-in status</button>}
      {auth ? <SignInPage configured={auth.configured} onSignedIn={() => void checkSignIn()} />
            : !authError && <p role="status">Checking sign-in…</p>}
    </main>;
  }

  return (
    <>
      <header className="nk-nav">
        <div className="nk-brand">
          <strong className="nk-brand-title">நம்ம குரல் · NammaKural</strong>
          <span className="nk-brand-sub">Tamil / Tanglish Voice AI</span>
        </div>

        <nav className="nk-nav-links" aria-label="Primary">
          <NavLink to="/" end className={({ isActive }) => `nk-tab${isActive ? " active" : ""}`}>
            <Mic size={15} />
            Voice Studio
          </NavLink>
          <NavLink to="/channels" className="nk-tab">Channels</NavLink>
          {auth.signed_in && <NavLink to="/requests" className="nk-tab">My requests</NavLink>}
          {auth.operator && <>
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
          </>}
          {auth.signed_in && <button type="button" className="nk-tab" onClick={() => void signOut()}>Sign out</button>}
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
        {authError && <p role="status">Could not refresh sign-in status. Try again.</p>}
        <Routes>
          <Route path="/" element={<VoiceAgentPage signedIn={auth.signed_in} />} />
          <Route path="/channels" element={<ChannelsPage />} />
          <Route path="/requests" element={auth.signed_in ? <RequestsPage /> : <p>Request history requires mobile sign-in.</p>} />
          <Route path="/debug" element={auth.operator ? <DebugPage /> : <p>Operator access required.</p>} />
          <Route path="/traces" element={auth.operator ? <TracesPage /> : <p>Operator access required.</p>} />
          <Route path="/telemetry" element={auth.operator ? <TelemetryPage /> : <p>Operator access required.</p>} />
        </Routes>
      </main>
    </>
  );
}

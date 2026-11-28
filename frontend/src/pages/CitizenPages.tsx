import { useEffect, useState } from "react";

export interface AuthStatus {
  required: boolean;
  configured: boolean;
  signed_in: boolean;
  operator: boolean;
}

export interface Channel {
  name: string;
  web: string;
  access: string;
  collect: string[];
  optional: string[];
  citizen_enters: string[];
  helpline: string;
  whatsapp?: string;
  email?: string;
}

export function SignInPage({ configured, onSignedIn }: { configured: boolean; onSignedIn: () => void }) {
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function submit() {
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch(sent ? "/api/auth/verify" : "/api/auth/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: `+91${phone}`, ...(sent ? { code } : {}) }),
      });
      const result = await response.json();
      if (!response.ok) {
        setMessage(typeof result.detail === "string" ? result.detail : "Check the number or code and try again.");
      } else if (sent) {
        onSignedIn();
      } else {
        setSent(true);
        setMessage("Code sent by SMS.");
      }
    } catch {
      setMessage("Could not reach sign-in. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="nk-card nk-signin">
      <h1>Sign in to NammaKural</h1>
      <p>Verify your mobile number to open Voice Studio and keep a private history of your grievances.</p>
      {!configured ? <p role="status">Mobile sign-in is unavailable until the SMS provider is configured.</p> : (
        <form onSubmit={(event) => { event.preventDefault(); void submit(); }}>
          <label>Indian mobile number
            <input className="nk-input" type="tel" autoComplete="tel-national" placeholder="10 digits" value={phone}
              maxLength={10} disabled={sent} onChange={(event) => setPhone(event.target.value.replace(/\D/g, ""))} required />
          </label>
          {sent && <label>SMS verification code
            <input className="nk-input" inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={code}
              onChange={(event) => setCode(event.target.value.replace(/\D/g, ""))} required />
          </label>}
          <button className="nk-btn primary" disabled={busy || !/^[6-9]\d{9}$/.test(phone) || (sent && code.length !== 6)}>
            {sent ? "Verify and sign in" : "Send SMS code"}
          </button>
          {sent && <button className="nk-btn" type="button" disabled={busy} onClick={() => { setSent(false); setCode(""); setMessage(""); }}>Change number or resend</button>}
        </form>
      )}
      {message && <p role="status">{message}</p>}
    </section>
  );
}

interface RequestItem {
  id: string;
  updated: number;
  title: string;
  destination: string;
  filing_reference: string | null;
  draft: { summary: string; location: { landmark: string; ward: string; area: string } };
}

export function RequestsPage() {
  const [data, setData] = useState<{ saved: number; reported_filed: number; items: RequestItem[] } | null>(null);
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState("");

  async function load() {
    try {
      const response = await fetch("/api/requests", { cache: "no-store" });
      if (!response.ok) throw new Error();
      setData(await response.json());
    } catch {
      setMessage("Could not load your requests.");
    }
  }

  useEffect(() => { void load(); }, []);

  async function record(id: string, reference: string) {
    setPending(id);
    setMessage("");
    try {
      const response = await fetch(`/api/requests/${id}/filing-reference`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reference }),
      });
      if (!response.ok) throw new Error();
      setMessage("Reference recorded. The agency status has not been verified.");
      await load();
    } catch {
      setMessage("Could not record that reference. Use the complaint number given by the agency.");
    } finally {
      setPending("");
    }
  }

  return (
    <div className="nk-telemetry">
      <header><h1>My requests</h1><p>Saved drafts and complaints you reported filing through a public channel.</p></header>
      {data && <div className="nk-card nk-request-counts"><strong>{data.saved} saved</strong><strong>{data.reported_filed} reported filed</strong></div>}
      {message && <p role="status">{message}</p>}
      {data?.items.length === 0 && <p>Save a grievance from Voice Studio to start your history.</p>}
      {data?.items.map((item) => (
        <section className="nk-card nk-grievance" key={item.id}>
          <h2>{item.title}</h2>
          <p>{item.draft.summary}</p>
          <p>{[item.draft.location.landmark, item.draft.location.area, item.draft.location.ward].filter(Boolean).join(" · ")}</p>
          <p>{item.destination} · {new Date(item.updated * 1000).toLocaleDateString("en-IN")}</p>
          {item.filing_reference ? <p>Reported filed · Reference {item.filing_reference}</p> : (
            <form className="nk-grievance-actions" onSubmit={(event) => {
              event.preventDefault();
              const reference = String(new FormData(event.currentTarget).get("reference") || "").trim();
              void record(item.id, reference);
            }}>
              <label>Agency complaint reference <input className="nk-input" name="reference" minLength={4} maxLength={50} required /></label>
              <button className="nk-btn" disabled={pending === item.id}>Record external filing</button>
            </form>
          )}
        </section>
      ))}
    </div>
  );
}

export function ChannelsPage() {
  const [channels, setChannels] = useState<Record<string, Channel>>({});
  const [error, setError] = useState(false);
  useEffect(() => {
    void fetch("/api/civic/channels").then((response) => {
      if (!response.ok) throw new Error();
      return response.json();
    }).then((data) => setChannels(data.channels)).catch(() => setError(true));
  }, []);
  return (
    <div className="nk-telemetry">
      <header><h1>Citizen grievance channels</h1><p>What to collect and where the citizen completes verification.</p></header>
      {error && <p role="status">Could not load the channel directory.</p>}
      {Object.entries(channels).map(([id, channel]) => (
        <section className="nk-card nk-grievance" key={id}>
          <h2>{channel.name}</h2>
          <p>{channel.access}</p>
          <dl><div><dt>Collect</dt><dd>{channel.collect.join(" · ")}</dd></div>
            <div><dt>Citizen enters directly</dt><dd>{channel.citizen_enters.join(" · ")}</dd></div>
            <div><dt>Optional</dt><dd>{channel.optional.join(" · ")}</dd></div></dl>
          <div className="nk-grievance-actions">
            <a href={channel.web} target="_blank" rel="noreferrer">Official site</a>
            <a href={`tel:${channel.helpline}`}>{channel.helpline}</a>
            {channel.whatsapp && <a href={channel.whatsapp} target="_blank" rel="noreferrer">Official WhatsApp</a>}
            {channel.email && <a href={`mailto:${channel.email}`}>Official email</a>}
          </div>
        </section>
      ))}
    </div>
  );
}

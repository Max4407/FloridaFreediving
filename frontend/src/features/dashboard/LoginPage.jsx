import { useState } from "react";
import { api } from "../../api";

export function LoginPage({ onLogin }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault(); setLoading(true); setError("");
    try {
      await api("/api/auth/login", { method: "POST", body: JSON.stringify({ password }) });
      onLogin();
    } catch (caught) { setError(caught.message); }
    finally { setLoading(false); }
  }

  return <main className="login-shell"><section className="login-card">
    <p className="eyebrow">Florida Freediving</p><h1>Officer access</h1>
    <p className="muted">Sign in with the shared club password.</p>
    <form onSubmit={submit}><label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required autoFocus /></label>
      {error && <p className="error" role="alert">{error}</p>}<button className="primary" disabled={loading}>{loading ? "Signing in…" : "Sign in"}</button></form>
  </section></main>;
}

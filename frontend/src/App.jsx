import { useEffect, useState } from "react";
import { SignupPage } from "./features/signup/SignupPage";
import { Dashboard } from "./features/dashboard/Dashboard";
import { LoginPage } from "./features/dashboard/LoginPage";
import { api } from "./api";

function OfficerApp() {
  const [auth, setAuth] = useState("loading");

  useEffect(() => {
    api("/api/auth/session").then(() => setAuth("yes")).catch(() => setAuth("no"));
  }, []);

  if (auth === "loading") return <main className="center-card">Checking officer session…</main>;
  if (auth === "no") return <LoginPage onLogin={() => setAuth("yes")} />;
  return <Dashboard onLogout={() => setAuth("no")} />;
}

export default function App() {
  if (window.location.pathname === "/signup") return <SignupPage />;
  if (window.location.pathname.startsWith("/dash")) return <OfficerApp />;
  return (
    <main className="center-card landing-page">
      <section className="landing-card">
        <p className="eyebrow">Florida Freediving</p>
        <h1>Find your depth. Find your people.</h1>
        <p>Use the signup link shared by your dive organizer.</p>
        <a className="text-link" href="/dash">Officer dashboard</a>
      </section>
    </main>
  );
}

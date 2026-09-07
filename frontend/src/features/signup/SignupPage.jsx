import { useEffect, useState } from "react";
import { api, easternDateTime } from "../../api";

const initialForm = {
  name: "",
  email: "",
  needs_carpool: false,
  pickup_location: "",
  needs_gear: false,
  suit_size: "",
  shoe_size: "",
};

export function SignupPage() {
  const publicId = new URLSearchParams(window.location.search).get("dive");
  const [dive, setDive] = useState(null);
  const [form, setForm] = useState(initialForm);
  const [state, setState] = useState({ loading: true, error: "", result: null });

  useEffect(() => {
    if (!publicId) {
      setState({ loading: false, error: "This signup link is missing a dive ID.", result: null });
      return;
    }
    api(`/api/public/dives/${publicId}`)
      .then((data) => { setDive(data); setState({ loading: false, error: "", result: null }); })
      .catch((error) => setState({ loading: false, error: error.message, result: null }));
  }, [publicId]);

  function update(event) {
    const { name, type, checked, value } = event.target;
    setForm((current) => ({ ...current, [name]: type === "checkbox" ? checked : value }));
  }

  async function submit(event) {
    event.preventDefault();
    setState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const result = await api(`/api/public/dives/${publicId}/signups`, {
        method: "POST",
        body: JSON.stringify({
          ...form,
          pickup_location: form.needs_carpool ? form.pickup_location : null,
          suit_size: form.needs_gear ? form.suit_size : null,
          shoe_size: form.needs_gear ? Number(form.shoe_size) : null,
        }),
      });
      setState({ loading: false, error: "", result });
    } catch (error) {
      setState({ loading: false, error: error.message, result: null });
    }
  }

  if (state.loading && !dive) return <main className="center-card">Loading dive…</main>;
  if (state.error && !dive) return <main className="center-card"><h1>Signup unavailable</h1><p>{state.error}</p></main>;
  if (state.result) {
    const confirmed = state.result.status === "confirmed";
    return (
      <main className="center-card success-card">
        <span className="success-mark">✓</span>
        <p className="eyebrow">{confirmed ? "You’re on the dive" : "Waitlist joined"}</p>
        <h1>{dive.title}</h1>
        <p>{confirmed ? "Your spot is confirmed." : `You are number ${state.result.waitlist_position} on the waitlist. An officer will contact you if a spot opens.`}</p>
        <p className="muted">Need a correction? Contact a club officer.</p>
      </main>
    );
  }

  return (
    <main className="signup-shell">
      <section className="dive-hero">
        <p className="eyebrow">Florida Freediving · Club Dive</p>
        <h1>{dive.title}</h1>
        <p className="hero-description">{dive.description}</p>
        <dl className="facts">
          <div><dt>When</dt><dd>{easternDateTime(dive.starts_at)} ET</dd></div>
          <div><dt>Where</dt><dd>{dive.location}</dd></div>
          <div><dt>Status</dt><dd>{dive.remaining ? `${dive.remaining} spot${dive.remaining === 1 ? "" : "s"} left` : "New signups join the waitlist"}</dd></div>
        </dl>
      </section>
      <section className="form-card">
        <p className="eyebrow">Reserve your spot</p>
        <h2>Diver details</h2>
        <form onSubmit={submit}>
          <label>Full name<input name="name" value={form.name} onChange={update} required maxLength="160" autoComplete="name" /></label>
          <label>Email address<input name="email" type="email" value={form.email} onChange={update} required autoComplete="email" /></label>
          <label className="check-row"><input name="needs_gear" type="checkbox" checked={form.needs_gear} onChange={update} /><span><strong>I need rental gear</strong><small>Includes a wetsuit, fins, mask, and weight set.</small></span></label>
          {form.needs_gear && <div className="field-grid">
            <label>Wetsuit size<select name="suit_size" value={form.suit_size} onChange={update} required><option value="">Select size</option>{["XS", "S", "M", "L", "XL"].map((size) => <option key={size}>{size}</option>)}</select></label>
            <label>US unisex shoe size<input name="shoe_size" type="number" min="1" max="18" step="0.5" value={form.shoe_size} onChange={update} required /></label>
          </div>}
          <label className="check-row"><input name="needs_carpool" type="checkbox" checked={form.needs_carpool} onChange={update} /><span><strong>I need a carpool</strong><small>Choose this if you do not have a car.</small></span></label>
          {form.needs_carpool && <label>Pickup location<input name="pickup_location" value={form.pickup_location} onChange={update} required maxLength="300" placeholder="Neighborhood, landmark, or address" /></label>}
          {state.error && <p className="error" role="alert">{state.error}</p>}
          <button className="primary" disabled={state.loading}>{state.loading ? "Submitting…" : dive.remaining ? "Join this dive" : "Join the waitlist"}</button>
        </form>
      </section>
    </main>
  );
}


import { useEffect, useMemo, useState } from "react";
import { api, easternDateTime } from "../../api";

function monthTitle(date) {
  return new Intl.DateTimeFormat("en-US", { month: "long", year: "numeric" }).format(date);
}

function easternDayKey(value) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/New_York", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date(value));
  const get = (type) => parts.find((part) => part.type === type).value;
  return `${get("year")}-${get("month")}-${get("day")}`;
}

function Calendar({ dives, month, onSelect }) {
  const first = new Date(month.getFullYear(), month.getMonth(), 1);
  const last = new Date(month.getFullYear(), month.getMonth() + 1, 0);
  const cells = Array(first.getDay()).fill(null);
  for (let day = 1; day <= last.getDate(); day += 1) cells.push(day);
  while (cells.length % 7) cells.push(null);
  const grouped = useMemo(() => {
    const result = {};
    dives.forEach((dive) => { (result[easternDayKey(dive.starts_at)] ||= []).push(dive); });
    return result;
  }, [dives]);

  return <div className="calendar" aria-label={monthTitle(month)}>
    {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((name) => <div className="weekday" key={name}>{name}</div>)}
    {cells.map((day, index) => {
      const key = day ? `${month.getFullYear()}-${String(month.getMonth() + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}` : `blank-${index}`;
      return <div className={`calendar-day ${day ? "" : "blank"}`} key={key}>{day && <><span className="day-number">{day}</span>{(grouped[key] || []).map((dive) => <button type="button" className={`calendar-event ${dive.warnings.length ? "warn" : ""}`} key={dive.id} onClick={() => onSelect(dive)}><span>{dive.title}</span><small>{dive.confirmed_count}/{dive.capacity}</small></button>)}</>}</div>;
    })}
  </div>;
}

function DiveForm({ dive, officers, onSave, onCancel }) {
  const [form, setForm] = useState({
    title: dive?.title || "", description: dive?.description || "", location: dive?.location || "",
    starts_at: dive ? localInput(dive.starts_at) : "", capacity: dive?.capacity || 12,
    officer_ids: dive?.assigned_officer_ids || [],
  });
  const [error, setError] = useState("");
  function update(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: name === "capacity" ? Number(value) : value }));
  }
  async function submit(event) {
    event.preventDefault(); setError("");
    try { await onSave(form); } catch (caught) { setError(caught.message); }
  }
  function toggleOfficer(id) {
    setForm((current) => ({ ...current, officer_ids: current.officer_ids.includes(id) ? current.officer_ids.filter((value) => value !== id) : [...current.officer_ids, id] }));
  }
  return <div className="modal-backdrop"><section className="modal form-modal" role="dialog" aria-modal="true" aria-label={dive ? "Edit dive" : "Create dive"}>
    <div className="section-heading"><div><p className="eyebrow">Dive setup</p><h2>{dive ? "Edit dive" : "Create a dive"}</h2></div><button className="icon-button" onClick={onCancel} aria-label="Close">×</button></div>
    <form onSubmit={submit}><div className="field-grid"><label>Title<input name="title" value={form.title} onChange={update} required /></label><label>Capacity<input name="capacity" type="number" min="1" max="500" value={form.capacity} onChange={update} required /></label></div>
      <label>Description<textarea name="description" rows="4" value={form.description} onChange={update} /></label>
      <label>Location<input name="location" value={form.location} onChange={update} required /></label>
      <label>Date and time (Eastern)<input name="starts_at" type="datetime-local" value={form.starts_at} onChange={update} required /></label>
      <fieldset><legend>Assigned officers</legend><div className="chip-options">{officers.filter((officer) => officer.active || form.officer_ids.includes(officer.id)).map((officer) => <label className="chip-check" key={officer.id}><input type="checkbox" checked={form.officer_ids.includes(officer.id)} onChange={() => toggleOfficer(officer.id)} />{officer.name}{!officer.active && " (inactive)"}</label>)}</div></fieldset>
      {error && <p className="error">{error}</p>}<div className="actions"><button type="button" className="secondary" onClick={onCancel}>Cancel</button><button className="primary">Save dive</button></div>
    </form>
  </section></div>;
}

function localInput(value) {
  const date = new Date(value);
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/New_York", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  }).formatToParts(date);
  const get = (type) => parts.find((part) => part.type === type).value;
  return `${get("year")}-${get("month")}-${get("day")}T${get("hour")}:${get("minute")}`;
}

function ParticipantEditor({ signup, onSave, onDelete, onPromote, firstWaitlisted }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ ...signup, suit_size: signup.suit_size || "", shoe_size: signup.shoe_size || "", pickup_location: signup.pickup_location || "" });
  const [error, setError] = useState("");
  const update = (event) => { const { name, type, checked, value } = event.target; setForm((current) => ({ ...current, [name]: type === "checkbox" ? checked : value })); };
  async function save() {
    try { await onSave(signup.id, { ...form, shoe_size: form.needs_gear ? Number(form.shoe_size) : null, suit_size: form.needs_gear ? form.suit_size : null, pickup_location: form.needs_carpool ? form.pickup_location : null }); setEditing(false); } catch (caught) { setError(caught.message); }
  }
  return <article className="participant">
    <div className="participant-summary"><div><strong>{signup.name}</strong><a href={`mailto:${signup.email}`}>{signup.email}</a></div><div className="tag-row">{signup.needs_carpool && <span className="tag">Carpool</span>}{signup.needs_gear && <span className="tag">Gear · {signup.suit_size} · US {signup.shoe_size}</span>}</div></div>
    {signup.needs_carpool && <p className="pickup">Pickup: {signup.pickup_location}</p>}
    {editing && <div className="inline-editor"><div className="field-grid"><label>Name<input name="name" value={form.name} onChange={update} /></label><label>Email<input name="email" type="email" value={form.email} onChange={update} /></label></div>
      <label className="check-row compact"><input name="needs_gear" type="checkbox" checked={form.needs_gear} onChange={update} />Needs gear</label>{form.needs_gear && <div className="field-grid"><label>Suit<select name="suit_size" value={form.suit_size} onChange={update}>{["XS", "S", "M", "L", "XL"].map((size) => <option key={size}>{size}</option>)}</select></label><label>Shoe<input name="shoe_size" type="number" min="1" max="18" step=".5" value={form.shoe_size} onChange={update} /></label></div>}
      <label className="check-row compact"><input name="needs_carpool" type="checkbox" checked={form.needs_carpool} onChange={update} />Needs carpool</label>{form.needs_carpool && <label>Pickup<input name="pickup_location" value={form.pickup_location} onChange={update} /></label>}{error && <p className="error">{error}</p>}<div className="actions"><button className="secondary" onClick={() => setEditing(false)}>Cancel</button><button className="primary small" onClick={save}>Save</button></div></div>}
    {!editing && <div className="row-actions">{signup.status === "waitlisted" && <button className="secondary small" disabled={!firstWaitlisted} onClick={() => onPromote(signup.id)}>Promote</button>}<button className="text-button" onClick={() => setEditing(true)}>Edit</button><button className="text-button danger" onClick={() => onDelete(signup)}>Remove</button></div>}
  </article>;
}

function DiveDetail({ dive, onClose, onEdit, onRefresh }) {
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const signupUrl = `${window.location.origin}/signup?dive=${dive.public_id}`;
  async function mutate(path, options) { try { await api(path, options); await onRefresh(); } catch (caught) { setError(caught.message); } }
  async function copySignupLink() {
    try {
      await navigator.clipboard.writeText(signupUrl);
      setCopied(true);
    } catch {
      setError("Copy failed. Select the signup link and copy it manually.");
    }
  }
  async function deleteDive() {
    const total = dive.confirmed_count + dive.waitlist_count;
    if (window.confirm(`Permanently delete “${dive.title}” and all ${total} signup record${total === 1 ? "" : "s"}? This cannot be undone.`)) { await api(`/api/officer/dives/${dive.id}`, { method: "DELETE" }); onClose(); await onRefresh(); }
  }
  return <div className="modal-backdrop"><section className="modal detail-modal" role="dialog" aria-modal="true" aria-label="Dive details">
    <div className="section-heading"><div><p className="eyebrow">{easternDateTime(dive.starts_at)} ET</p><h2>{dive.title}</h2><p>{dive.location}</p></div><button className="icon-button" onClick={onClose} aria-label="Close">×</button></div>
    {dive.description && <p className="detail-description">{dive.description}</p>}
    <div className="share-row"><div><span>Member signup link</span><a href={signupUrl} target="_blank" rel="noreferrer">{signupUrl}</a></div><button className="secondary small" onClick={copySignupLink}>{copied ? "Copied" : "Copy link"}</button></div>
    {dive.warnings.length > 0 && <div className="warning-panel"><strong>Needs attention</strong><ul>{dive.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>}
    <div className="stat-grid"><div><span>Confirmed</span><strong>{dive.confirmed_count}/{dive.capacity}</strong></div><div><span>Waitlist</span><strong>{dive.waitlist_count}</strong></div><div><span>Officers</span><strong>{dive.officers.length}</strong></div></div>
    <section><h3>Assigned officers</h3><p>{dive.officers.map((officer) => officer.name).join(", ") || "No active officers assigned"}</p></section>
    <section><h3>Gear outlook</h3><div className="table-wrap"><table><thead><tr><th>Gear</th><th>Available</th><th>Confirmed</th><th>Waitlist</th></tr></thead><tbody>{dive.gear.map((row) => <tr className={row.shortage ? "shortage" : ""} key={`${row.category}-${row.label}`}><td>{row.label}</td><td>{row.available}</td><td>{row.confirmed_needed}</td><td>{row.waitlisted_needed}</td></tr>)}</tbody></table></div></section>
    <section><h3>Confirmed divers</h3><div className="participant-list">{dive.confirmed.length ? dive.confirmed.map((signup) => <ParticipantEditor key={signup.id} signup={signup} onSave={(id, body) => mutate(`/api/officer/signups/${id}`, { method: "PATCH", body: JSON.stringify(body) })} onDelete={(item) => window.confirm(`Remove ${item.name}?`) && mutate(`/api/officer/signups/${item.id}`, { method: "DELETE" })} />) : <p className="empty">No confirmed signups yet.</p>}</div></section>
    <section><h3>Waitlist</h3><div className="participant-list">{dive.waitlisted.length ? dive.waitlisted.map((signup, index) => <ParticipantEditor key={signup.id} signup={signup} firstWaitlisted={index === 0 && dive.confirmed_count < dive.capacity} onPromote={(id) => mutate(`/api/officer/signups/${id}/promote`, { method: "POST" })} onSave={(id, body) => mutate(`/api/officer/signups/${id}`, { method: "PATCH", body: JSON.stringify(body) })} onDelete={(item) => window.confirm(`Remove ${item.name}?`) && mutate(`/api/officer/signups/${item.id}`, { method: "DELETE" })} />) : <p className="empty">The waitlist is empty.</p>}</div></section>
    {error && <p className="error">{error}</p>}<div className="detail-footer"><button className="danger-button" onClick={deleteDive}>Delete dive</button><button className="secondary" onClick={onEdit}>Edit dive</button></div>
  </section></div>;
}

function OfficersPanel({ officers, reload }) {
  const [name, setName] = useState(""); const [error, setError] = useState("");
  async function add(event) { event.preventDefault(); try { await api("/api/officer/officers", { method: "POST", body: JSON.stringify({ name }) }); setName(""); reload(); } catch (caught) { setError(caught.message); } }
  async function toggle(officer) { try { await api(`/api/officer/officers/${officer.id}`, { method: "PATCH", body: JSON.stringify({ active: !officer.active }) }); reload(); } catch (caught) { setError(caught.message); } }
  return <section className="panel"><div className="section-heading"><div><p className="eyebrow">Club roster</p><h2>Officers</h2></div></div><form className="inline-form" onSubmit={add}><label><span className="sr-only">Officer name</span><input value={name} onChange={(event) => setName(event.target.value)} placeholder="Officer name" required /></label><button className="primary small">Add officer</button></form>{error && <p className="error">{error}</p>}<div className="settings-list">{officers.map((officer) => <div key={officer.id}><span><strong>{officer.name}</strong><small>{officer.active ? "Available for assignment" : "Inactive · preserved on past dives"}</small></span><button className="secondary small" onClick={() => toggle(officer)}>{officer.active ? "Deactivate" : "Reactivate"}</button></div>)}</div></section>;
}

function InventoryPanel({ inventory, reload }) {
  const [form, setForm] = useState({ category: "wetsuit", suit_size: "XS", min_shoe_size: 5, max_shoe_size: 7, quantity: 0 }); const [error, setError] = useState("");
  function update(event) { const { name, value } = event.target; setForm((current) => ({ ...current, [name]: ["quantity", "min_shoe_size", "max_shoe_size"].includes(name) ? Number(value) : value })); }
  function payload() { return { category: form.category, suit_size: form.category === "wetsuit" ? form.suit_size : null, min_shoe_size: form.category === "fins" ? form.min_shoe_size : null, max_shoe_size: form.category === "fins" ? form.max_shoe_size : null, quantity: form.quantity }; }
  async function add(event) { event.preventDefault(); try { await api("/api/officer/inventory", { method: "POST", body: JSON.stringify(payload()) }); reload(); } catch (caught) { setError(caught.message); } }
  async function changeQuantity(item, quantity) { try { await api(`/api/officer/inventory/${item.id}`, { method: "PUT", body: JSON.stringify({ ...item, quantity: Math.max(0, quantity) }) }); reload(); } catch (caught) { setError(caught.message); } }
  const label = (item) => item.category === "wetsuit" ? `Wetsuit · ${item.suit_size}` : item.category === "fins" ? `Fins · US ${item.min_shoe_size}–${item.max_shoe_size}` : item.category === "mask" ? "Masks" : "Weight sets";
  return <section className="panel"><div className="section-heading"><div><p className="eyebrow">Loaner gear</p><h2>Inventory</h2></div></div><div className="inventory-grid">{inventory.map((item) => <article key={item.id}><span>{label(item)}</span><div className="quantity"><button aria-label={`Decrease ${label(item)}`} onClick={() => changeQuantity(item, item.quantity - 1)}>−</button><strong>{item.quantity}</strong><button aria-label={`Increase ${label(item)}`} onClick={() => changeQuantity(item, item.quantity + 1)}>+</button></div></article>)}</div><h3>Add inventory range</h3><form onSubmit={add}><div className="field-grid three"><label>Category<select name="category" value={form.category} onChange={update}><option value="wetsuit">Wetsuit</option><option value="fins">Fins</option><option value="mask">Mask</option><option value="weight_set">Weight set</option></select></label>{form.category === "wetsuit" && <label>Size<select name="suit_size" value={form.suit_size} onChange={update}>{["XS", "S", "M", "L", "XL"].map((size) => <option key={size}>{size}</option>)}</select></label>}{form.category === "fins" && <><label>Min shoe<input name="min_shoe_size" type="number" min="1" max="18" step=".5" value={form.min_shoe_size} onChange={update} /></label><label>Max shoe<input name="max_shoe_size" type="number" min="1" max="18" step=".5" value={form.max_shoe_size} onChange={update} /></label></>}<label>Quantity<input name="quantity" type="number" min="0" value={form.quantity} onChange={update} /></label></div>{error && <p className="error">{error}</p>}<button className="primary small">Add inventory</button></form></section>;
}

export function Dashboard({ onLogout }) {
  const [data, setData] = useState({ dives: [], officers: [], inventory: [] });
  const [month, setMonth] = useState(() => new Date(new Date().getFullYear(), new Date().getMonth(), 1));
  const [selected, setSelected] = useState(null); const [editing, setEditing] = useState(null); const [tab, setTab] = useState("calendar"); const [error, setError] = useState("");
  async function load() { try { const [dives, officers, inventory] = await Promise.all([api("/api/officer/dives"), api("/api/officer/officers"), api("/api/officer/inventory")]); setData({ dives, officers, inventory }); setSelected((current) => current ? dives.find((dive) => dive.id === current.id) || null : null); } catch (caught) { if (caught.status === 401) onLogout(); else setError(caught.message); } }
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  async function saveDive(form) { const body = { ...form, starts_at: form.starts_at }; if (editing?.id) await api(`/api/officer/dives/${editing.id}`, { method: "PATCH", body: JSON.stringify(body) }); else await api("/api/officer/dives", { method: "POST", body: JSON.stringify(body) }); setEditing(null); await load(); }
  async function logout() { await api("/api/auth/logout", { method: "POST" }); onLogout(); }
  return <div className="app-shell"><header className="topbar"><a href="/dash" className="brand"><span className="brand-mark">FF</span><span>Florida Freediving<small>Officer console</small></span></a><nav><button className={tab === "calendar" ? "active" : ""} onClick={() => setTab("calendar")}>Calendar</button><button className={tab === "officers" ? "active" : ""} onClick={() => setTab("officers")}>Officers</button><button className={tab === "inventory" ? "active" : ""} onClick={() => setTab("inventory")}>Gear</button></nav><button className="logout" onClick={logout}>Log out</button></header>
    <main className="dashboard">{error && <p className="error">{error}</p>}{tab === "calendar" && <><div className="page-heading"><div><p className="eyebrow">Dive operations</p><h1>{monthTitle(month)}</h1><p>Plan staffing, rides, and equipment at a glance.</p></div><div className="heading-actions"><button className="secondary" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}>←</button><button className="secondary" onClick={() => setMonth(new Date())}>Today</button><button className="secondary" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}>→</button><button className="primary" onClick={() => setEditing({})}>+ New dive</button></div></div><Calendar dives={data.dives} month={month} onSelect={setSelected} /></>}{tab === "officers" && <OfficersPanel officers={data.officers} reload={load} />}{tab === "inventory" && <InventoryPanel inventory={data.inventory} reload={load} />}</main>
    {selected && <DiveDetail dive={selected} onClose={() => setSelected(null)} onEdit={() => { setEditing(selected); setSelected(null); }} onRefresh={load} />}{editing && <DiveForm dive={editing.id ? editing : null} officers={data.officers} onSave={saveDive} onCancel={() => setEditing(null)} />}
  </div>;
}

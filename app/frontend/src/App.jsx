import React, { useEffect, useState } from "react";
import { api } from "./api.js";
import { AS_OF, addDays, eur, mdLite, pct, riskLevel } from "./format.js";

const OWNERS = {
  escalate_master_data: "Master Data Lead",
  escalate_artwork: "Regulatory Artwork Manager",
  book_maintenance: "Site Maintenance Manager",
};
const LABELS = {
  escalate_master_data: "Escalate master data",
  escalate_artwork: "Escalate artwork approval",
  book_maintenance: "Book preventive maintenance",
};
const SUGGESTIONS = {
  demand: ["Perché Zyvanta è a rischio?", "Cosa rende un lancio pronto?", "Which actions are open on our launches?"],
  manufacturing: ["Which machines will fail in the next 30 days and which brands are at risk?",
                  "What does OEE mean and why do all three components matter?"],
};

function Gate({ label, value }) {
  const cls = value >= 1 ? "ok" : value >= 0.5 ? "part" : "bad";
  const icon = value >= 1 ? "✓" : value >= 0.5 ? `◐ ${pct(value)}` : "✕";
  return <span className={`gate ${cls}`}>{icon} {label}</span>;
}

function EscalatePanel({ launch, onDone, onClose }) {
  const proposed = [];
  if (launch.master_data_ready < 0.5) proposed.push({ action_type: "escalate_master_data" });
  if (launch.artwork_ready < 0.5) proposed.push({ action_type: "escalate_artwork" });
  if (launch.linked_failure_prob >= 0.3)
    proposed.push({ action_type: "book_maintenance", equipment: launch.linked_equipment });
  const [rows, setRows] = useState(proposed.map((p) => ({ ...p, on: true, owner: OWNERS[p.action_type],
    due_date: addDays(AS_OF, p.action_type === "book_maintenance" ? 3 : 7) })));
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const set = (i, k, v) => setRows(rows.map((r, j) => (j === i ? { ...r, [k]: v } : r)));
  const submit = async () => {
    setBusy(true); setErr(null);
    try {
      const results = [];
      for (const r of rows.filter((x) => x.on)) {
        const { status, body } = await api.createAction({ launch_id: launch.launch_id, action_type: r.action_type,
          owner: r.owner, due_date: r.due_date, equipment: r.equipment || null,
          note: `Raised from Control Tower for ${launch.brand} (${launch.blocking_gates || "machine risk"})` });
        results.push({ ...body, already: status === 200 });
      }
      onDone(results);
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };
  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>Escalate blockers · {launch.brand}</h3>
        <p className="muted">Each action gets an owner and a due date, and is stored in Lakebase (control_tower.actions).</p>
        {rows.map((r, i) => (
          <div className="action-row" key={r.action_type}>
            <label><input type="checkbox" checked={r.on} onChange={(e) => set(i, "on", e.target.checked)} />
              <b>{LABELS[r.action_type]}</b>{r.equipment ? ` · ${r.equipment}` : ""}</label>
            <input value={r.owner} onChange={(e) => set(i, "owner", e.target.value)} aria-label="owner" />
            <input type="date" value={r.due_date} onChange={(e) => set(i, "due_date", e.target.value)} aria-label="due date" />
          </div>
        ))}
        {err && <p className="error">{err}</p>}
        <div className="modal-actions">
          <button className="ghost" onClick={onClose}>Cancel</button>
          <button className="primary" disabled={busy || !rows.some((r) => r.on)} onClick={submit}>
            {busy ? "Saving…" : `Confirm ${rows.filter((r) => r.on).length} action(s)`}</button>
        </div>
      </div>
    </div>
  );
}

function LaunchCard({ l, actions, onEscalate }) {
  const [lang, setLang] = useState("en");
  const atRisk = l.readiness < 0.8 && l.phase === "launch";
  const open = actions.filter((a) => a.launch_id === l.launch_id && a.status === "open");
  return (
    <div className={`card launch ${atRisk ? "risk" : ""}`}>
      <div className="card-head">
        <div><div className="brand">{l.brand}</div><div className="muted">{l.launch_id} · {l.therapeutic_area} · {l.phase}</div></div>
        {atRisk && <span className="pill red">AT RISK</span>}
      </div>
      <div className="row">
        <div className="metric"><div className="label">Readiness</div><div className="big">{pct(l.readiness)}</div>
          <div className="bar"><div style={{ width: pct(l.readiness) }} /></div></div>
        <div className="metric"><div className="label">€ at risk <span className="muted">(estimate)</span></div>
          <div className="big red-text">{eur(l.revenue_at_risk_eur)}</div>
          <div className="muted small">{l.phase === "launch" ? "4 weeks of launch delay" : "phase-out: no launch risk"}</div></div>
      </div>
      <div className="gates"><Gate label="Master data" value={l.master_data_ready} /><Gate label="Artwork" value={l.artwork_ready} />
        <Gate label="Serialization" value={l.serialization_ready} /></div>
      {l.linked_equipment && (
        <div className={`machine ${riskLevel(l.linked_failure_prob)}`}>
          <b>{l.linked_failure_prob >= 0.3 ? "Hidden supply risk:" : "Line health:"}</b> {l.linked_equipment} on {l.primary_line} ({l.plant}) ·{" "}
          <b>{pct(l.linked_failure_prob)}</b> chance of unplanned failure in 30 days
        </div>)}
      {l.brief_en && (
        <details className="brief"><summary>AI action brief
          <span className="lang"><button className={lang === "en" ? "on" : ""} onClick={(e) => { e.preventDefault(); setLang("en"); }}>EN</button>
            <button className={lang === "it" ? "on" : ""} onClick={(e) => { e.preventDefault(); setLang("it"); }}>IT</button></span></summary>
          <div dangerouslySetInnerHTML={{ __html: mdLite(lang === "en" ? l.brief_en : l.brief_it) }} />
          <div className="muted small">Generated with ai_query from governed facts. Advice, not a decision.</div></details>)}
      <div className="card-foot">
        {open.length > 0 && <span className="pill green">✓ {open.length} action(s) tracked</span>}
        {atRisk && <button className="primary" onClick={() => onEscalate(l)}>Escalate</button>}
      </div>
      {open.length > 0 && (<ul className="tracked">{open.map((a) => (
        <li key={a.action_id}>{LABELS[a.action_type]} → <b>{a.owner}</b> by {String(a.due_date).slice(0, 10)}</li>))}</ul>)}
    </div>
  );
}

function Genie() {
  const [space, setSpace] = useState("demand");
  const [q, setQ] = useState("");
  const [conv, setConv] = useState({ demand: null, manufacturing: null });
  const [log, setLog] = useState([]);
  const [busy, setBusy] = useState(false);
  const ask = async (question) => {
    if (!question.trim()) return;
    setBusy(true); setQ("");
    setLog((l) => [...l, { role: "user", text: question, space }]);
    try {
      const a = await api.ask({ question, space, conversation_id: conv[space] });
      setConv((c) => ({ ...c, [space]: a.conversation_id }));
      setLog((l) => [...l, { role: "genie", ...a, space }]);
    } catch (e) {
      setLog((l) => [...l, { role: "genie", status: "error", text: `Request failed: ${e.message}`, space }]);
    } finally { setBusy(false); }
  };
  return (
    <div className="card genie">
      <div className="card-head"><div className="brand">Ask Genie</div>
        <div className="toggle">{["demand", "manufacturing"].map((s) => (
          <button key={s} className={space === s ? "on" : ""} onClick={() => setSpace(s)}>
            {s === "demand" ? "Demand & Supply" : "Manufacturing"}</button>))}</div></div>
      <div className="chips">{SUGGESTIONS[space].map((s) => <button key={s} onClick={() => ask(s)} disabled={busy}>{s}</button>)}</div>
      <div className="log">
        {log.filter((m) => m.space === space).map((m, i) => (
          <div key={i} className={`msg ${m.role} ${m.status || ""}`}>
            <div dangerouslySetInnerHTML={{ __html: mdLite(m.text || (m.status === "no_data" ? "No rows matched." : "")) }} />
            {m.sql && <details><summary>SQL used (governed tables)</summary><pre>{m.sql}</pre></details>}
            {m.rows && m.rows.length > 0 && (
              <table><thead><tr>{m.columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
                <tbody>{m.rows.slice(0, 8).map((r, j) => <tr key={j}>{r.map((v, k) => <td key={k}>{v}</td>)}</tr>)}</tbody></table>)}
          </div>))}
        {busy && <div className="msg genie muted">Genie is thinking…</div>}
      </div>
      <form onSubmit={(e) => { e.preventDefault(); ask(q); }} className="ask">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Perché Zyvanta è a rischio?" />
        <button className="primary" disabled={busy}>Ask</button></form>
    </div>
  );
}

export default function App() {
  const [launches, setLaunches] = useState([]);
  const [equipment, setEquipment] = useState([]);
  const [actions, setActions] = useState([]);
  const [escalating, setEscalating] = useState(null);
  const [toast, setToast] = useState(null);
  const [err, setErr] = useState(null);
  const load = async () => {
    try {
      const [l, e, a] = await Promise.all([api.launches(), api.equipment(8), api.actions()]);
      setLaunches(l); setEquipment(e); setActions(a);
    } catch (x) { setErr(x.message); }
  };
  useEffect(() => { load(); }, []);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(null), 6000); return () => clearTimeout(t); }, [toast]);
  const atRisk = launches.filter((l) => l.phase === "launch" && l.readiness < 0.8);
  const highRisk = equipment.filter((e) => e.failure_prob_30d >= 0.6);
  return (
    <div className="page">
      <header><div><h1>Helivara · Launch & Supply Control Tower</h1>
        <div className="muted">As of {AS_OF} · synthetic data, fictional company · Lakebase + Unity Catalog + Genie</div></div></header>
      {err && <p className="error">Could not load data: {err}</p>}
      <section className="kpis">
        <div className="kpi"><div className="label">Launches at risk</div><div className="big red-text">{atRisk.length}</div></div>
        <div className="kpi"><div className="label">Revenue at risk (estimate)</div>
          <div className="big">{eur(atRisk.reduce((s, l) => s + (l.revenue_at_risk_eur || 0), 0))}</div></div>
        <div className="kpi"><div className="label">Machines ≥ 60% failure risk</div><div className="big">{highRisk.length}</div></div>
        <div className="kpi"><div className="label">Open actions</div><div className="big">{actions.filter((a) => a.status === "open").length}</div></div>
      </section>
      <main>
        <div className="col">
          {launches.map((l) => <LaunchCard key={l.launch_id} l={l} actions={actions} onEscalate={setEscalating} />)}
          <div className="card"><div className="brand">Equipment risk (model: equipment_failure_model@champion)</div>
            <table className="equip"><thead><tr><th>Machine</th><th>Plant / line</th><th>Class</th><th>30-day failure risk</th>
              <th>RUL</th><th>Top driver</th><th>Brands made on this line</th></tr></thead>
              <tbody>{equipment.map((e) => (
                <tr key={e.equipment} className={riskLevel(e.failure_prob_30d)}>
                  <td>{e.equipment}</td><td>{e.plant} · {e.line}</td><td>{e.equipment_class}</td>
                  <td><div className="bar small"><div style={{ width: pct(e.failure_prob_30d) }} /></div> {pct(e.failure_prob_30d)}</td>
                  <td>{e.rul_days}d</td><td>{e.top_driver}</td><td>{e.impacted_brands || "—"}</td></tr>))}</tbody></table></div>
        </div>
        <div className="col side"><Genie /></div>
      </main>
      {escalating && <EscalatePanel launch={escalating} onClose={() => setEscalating(null)}
        onDone={(res) => { setEscalating(null); setToast(res.map((r) => `${LABELS[r.action_type]}: ${r.already ? "already tracked" : "tracked"}`).join(" · ")); load(); }} />}
      {toast && <div className="toast" onClick={() => setToast(null)}>✓ {toast}</div>}
    </div>
  );
}

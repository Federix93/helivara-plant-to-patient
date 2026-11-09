export const AS_OF = "2026-09-22";
export const eur = (v) =>
  v == null ? "—" : v >= 1e6 ? `€${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `€${Math.round(v / 1e3)}k` : `€${Math.round(v)}`;
export const pct = (v) => (v == null ? "—" : `${Math.round(v * 100)}%`);
export const addDays = (iso, n) => {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
};
const esc = (s) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
export const mdLite = (s = "") => esc(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/\n/g, "<br/>");
export const riskLevel = (p) => (p >= 0.6 ? "high" : p >= 0.3 ? "medium" : "low");

async function req(path, opts = {}) {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.detail ? JSON.stringify(body.detail) : `HTTP ${r.status}`);
  return { status: r.status, body };
}
export const api = {
  launches: () => req("/api/launches").then((r) => r.body),
  equipment: (limit = 10) => req(`/api/equipment-risk?limit=${limit}`).then((r) => r.body),
  actions: (launchId) => req(`/api/actions${launchId ? `?launch_id=${launchId}` : ""}`).then((r) => r.body),
  createAction: (a) => req("/api/actions", { method: "POST", body: JSON.stringify(a) }),
  ask: (q) => req("/api/genie/ask", { method: "POST", body: JSON.stringify(q) }).then((r) => r.body),
};

// webapp/static/js/shock-alerts/affects.js
//
// The "Affects:" block of a shock alert card. Alerts stored since 2026-10-05 carry a
// per-instrument `lean` ("buy" | "sell" | "mixed") and `lean_why` (see alerting/direction.py);
// older rows have neither and keep the compact one-line form.
import { escapeHtml } from "../format.js";

const LEAN = {
  buy: { icon: "🟢", label: "potential BUY", color: "#2e7d32" },
  sell: { icon: "🔴", label: "potential SELL-OFF", color: "#c62828" },
  mixed: { icon: "⚪", label: "no clear lean", color: "#888" },
};

// "[convention]" / "[Layer2]" mark where a lean's reasoning comes from; useful in the data, noise on screen.
const PROVENANCE_TAG = /\s*\[(?:convention|Layer2)\]/g;

export function affectsLineHtml(symbols) {
  if (!symbols || symbols.length === 0) return "none currently tracked";
  if (!symbols.some((s) => "lean" in s)) {
    return symbols.map((s) => `${escapeHtml(s.symbol)} (${escapeHtml(s.channel)})`).join(", ");
  }
  const lines = symbols.map((s) => {
    const lean = LEAN[s.lean] || LEAN.mixed;
    const why = (s.lean_why || "").replace(PROVENANCE_TAG, "");
    const channel = (s.channel || "").replace(/_/g, " ");
    return `<div class="shock-lean">${escapeHtml(s.symbol)} (${escapeHtml(channel)}): `
      + `<span style="color:${lean.color};font-weight:bold">${lean.icon} ${lean.label}</span>`
      + `${why ? ` — ${escapeHtml(why)}` : ""}</div>`;
  });
  return `${lines.join("")}<div class="meta-text-sm">Typical reaction, not a trade signal.</div>`;
}

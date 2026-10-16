// webapp/static/js/stats/impact-filter.js
//
// The impact chips shared by all four Stats sub-tabs (market-reaction spec section 5): pure helpers, no DOM.
// The selection is a list of bucket names; the API takes it as `impacts=High,Unrated`.
import { escapeHtml } from "../format.js";

// Canonical order of the buckets, used for the query string and the chips. "Unrated" is the bucket for rows
// whose impact tag was inferred from another release of the same event.
const LEVELS = [
  { name: "High", label: "High" },
  { name: "Medium", label: "Medium" },
  { name: "Low", label: "Low" },
  { name: "Unrated", label: "Unrated (inferred)" },
];

// What the chips start as: High, plus Unrated so seeded history (CPI, NFP, PPI) is not silently hidden.
export const DEFAULT_IMPACTS = ["High", "Unrated"];

function canonical(selected) {
  const chosen = new Set(selected || []);
  return LEVELS.map((l) => l.name).filter((name) => chosen.has(name));
}

// "High,Unrated" in canonical order; "" for no selection (the caller must not call the API then).
export function impactsParam(selected) {
  return canonical(selected).join(",");
}

// Selection with `name` switched on/off, in canonical order. Never mutates the input; unknown names are ignored.
export function toggleImpact(selected, name) {
  const chosen = new Set(canonical(selected));
  if (!LEVELS.some((l) => l.name === name)) return [...chosen];
  if (chosen.has(name)) chosen.delete(name); else chosen.add(name);
  return canonical([...chosen]);
}

// The four toggle buttons; a pressed one carries aria-pressed="true" and the impact-chip-on class.
export function chipsHtml(selected) {
  const on = new Set(selected || []);
  const buttons = LEVELS.map((l) => {
    const pressed = on.has(l.name);
    return `<button type="button" class="impact-chip${pressed ? " impact-chip-on" : ""}" `
      + `data-impact="${escapeHtml(l.name)}" aria-pressed="${pressed}">${escapeHtml(l.label)}</button>`;
  }).join("");
  return `<div class="impact-chips" role="group" aria-label="Impact levels">${buttons}</div>`;
}

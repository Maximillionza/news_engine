// webapp/static/js/stats/chart.js
//
// Stats tab line chart: Forecast (dotted grey), Actual (solid), Predicted (dashed; green when the
// call was Right, red when Wrong). A release with no call leaves a gap, never a zero. Pure: returns
// an SVG string so it can be unit-tested under plain Node.
import { escapeHtml } from "../format.js";

const GREEN = "#2e7d32";
const RED = "#c62828";
const DEFAULT_W = 640, H = 210, L = 44, R = 28, T = 12, B = 26;
const LABEL_PX = 56;   // room one x-axis label needs, so neighbours do not overlap

// Build an SVG path for one series. A null value ends the current stroke so the line breaks (a gap).
function seriesPath(pts, key, x, y) {
  let d = "";
  let drawing = false;
  pts.forEach((p, i) => {
    if (p[key] == null) { drawing = false; return; }
    d += `${drawing ? " L" : (d ? " M" : "M")}${x(i).toFixed(1)},${y(p[key]).toFixed(1)}`;
    drawing = true;
  });
  return d;
}

// opts.width: the viewBox width in CSS pixels. Passing the container's real width keeps the 11px axis
// text 11px on a phone instead of shrinking with a fixed 640-wide viewBox.
export function buildChartSvg(chart, opts = {}) {
  const W = opts.width || DEFAULT_W;
  const pts = (chart && chart.points) || [];
  if (pts.length === 0) {
    return '<div class="meta-text-sm">No scored releases for this selection.</div>';
  }
  const vals = pts.flatMap((p) => [p.forecast, p.actual, p.predicted]).filter((v) => v !== null && v !== undefined);
  let lo = Math.min(...vals), hi = Math.max(...vals);
  if (hi === lo) { hi += 0.1; lo -= 0.1; }
  const pad = (hi - lo) * 0.15;
  lo -= pad; hi += pad;
  const x = (i) => (pts.length === 1 ? (L + W - R) / 2 : L + (i * (W - L - R)) / (pts.length - 1));
  const y = (v) => T + ((hi - v) * (H - T - B)) / (hi - lo);
  const unit = escapeHtml((chart && chart.unit) || "");

  let svg = `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Forecast, actual and predicted by release">`;
  for (let k = 0; k <= 4; k++) {
    const v = lo + ((hi - lo) * k) / 4;
    svg += `<line x1="${L}" x2="${W - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}" stroke="#ccc" stroke-width="0.5"/>`
      + `<text x="${L - 6}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end" font-size="11" fill="#666">${v.toFixed(2)}${unit}</text>`;
  }
  // X-axis text is the server's per-point label (month, or full date when a month repeats).
  const labelEvery = Math.max(1, Math.ceil(pts.length / Math.max(1, Math.floor((W - L - R) / LABEL_PX))));
  pts.forEach((p, i) => {
    if (i % labelEvery !== 0 && i !== pts.length - 1) return;
    svg += `<text x="${x(i).toFixed(1)}" y="${H - 8}" text-anchor="middle" font-size="11" fill="#666">${escapeHtml(p.label)}</text>`;
  });
  svg += `<path data-line="forecast" d="${seriesPath(pts, "forecast", x, y)}" fill="none" stroke="#999" stroke-width="1.5" stroke-dasharray="2 3"/>`;
  svg += `<path data-line="actual" d="${seriesPath(pts, "actual", x, y)}" fill="none" stroke="#222" stroke-width="2"/>`;
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1], b = pts[i];
    if (a.predicted == null || b.predicted == null) continue;
    const colour = b.verdict === "right" ? GREEN : RED;
    svg += `<line data-predicted="seg" x1="${x(i - 1).toFixed(1)}" y1="${y(a.predicted).toFixed(1)}" x2="${x(i).toFixed(1)}" y2="${y(b.predicted).toFixed(1)}" stroke="${colour}" stroke-width="2.5" stroke-dasharray="6 4"/>`;
  }
  pts.forEach((p, i) => {
    if (p.actual != null) svg += `<circle cx="${x(i).toFixed(1)}" cy="${y(p.actual).toFixed(1)}" r="3" fill="#222"/>`;
    if (p.predicted != null) {
      svg += `<circle data-predicted="dot" cx="${x(i).toFixed(1)}" cy="${y(p.predicted).toFixed(1)}" r="4" fill="${p.verdict === "right" ? GREEN : RED}"/>`;
    }
  });
  return svg + "</svg>";
}

import React from "react";

// Flat cartoon avatars per the approved mockups (reference image 4 style): varied skin,
// hair, and shirt tones assigned deterministically from the agent id so each agent keeps a
// stable look across views and refreshes.

const SKINS = ["#F4C7A1", "#C68642", "#8D5524", "#F2C09B", "#A56A3A"];
const HAIRS = ["#5B3A21", "#2C2C2A", "#E8B54A", "#C9552E", "#444441", "#B4B2A9"];
const SHIRTS = ["#378ADD", "#D85A30", "#2E9E8F", "#D4537E", "#639922", "#EF9F27", "#E24B4A"];

export function palette(id) {
  let h = 0;
  for (const ch of String(id)) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return {
    skin: SKINS[h % SKINS.length],
    hair: HAIRS[(h >> 3) % HAIRS.length],
    shirt: SHIRTS[(h >> 6) % SHIRTS.length],
  };
}

// Front-facing bust (building view windows).
export function FrontAgent({ x, y, id, working, animClass = "", scale = 1 }) {
  const p = palette(id);
  return (
    <g transform={`translate(${x} ${y}) scale(${scale})`}>
      <g className={working ? `agent-working ${animClass}` : ""}>
        <rect x="-9" y="0" width="18" height="11" rx="4" fill={p.shirt} />
        <circle cx="0" cy="-6" r="6.4" fill={p.hair} />
        <circle cx="0" cy="-4.6" r="5.1" fill={p.skin} />
        {working ? (
          <>
            <circle cx="-2" cy="-5.4" r="0.9" fill="#2C2C2A" />
            <circle cx="2" cy="-5.4" r="0.9" fill="#2C2C2A" />
            <path d="M-1.6 -2.6 Q0 -1.4 1.6 -2.6" stroke="#2C2C2A" strokeWidth="0.6" fill="none" />
          </>
        ) : (
          <path d="M-3 -4.8 L-1.4 -4.8 M1.4 -4.8 L3 -4.8" stroke="#2C2C2A" strokeWidth="0.7" fill="none" />
        )}
      </g>
      <circle cx="11" cy="-9" r="3" fill={working ? "var(--working)" : "var(--idle)"} className={working ? "dot-working" : ""} stroke="var(--interior)" strokeWidth="1" />
      {!working && (
        <g fill="#7A776E" fontFamily="sans-serif">
          <text x="10" y="-14" fontSize="9" className="zzz">z</text>
          <text x="15" y="-20" fontSize="11" className="zzz z2">Z</text>
          <text x="21" y="-26" fontSize="9" className="zzz z3">z</text>
        </g>
      )}
    </g>
  );
}

// Top-down figure (department view): chair, shoulders, hair ring, face crescent showing
// the facing direction. dir is degrees: 0 faces up (north).
export function TopDownAgent({ x, y, id, working, dir = 0, scale = 1, animClass = "", head = false }) {
  const p = palette(id);
  const rad = ((dir - 90) * Math.PI) / 180;
  const fx = Math.cos(rad) * 2.6;
  const fy = Math.sin(rad) * 2.6;
  const r = head ? 1.18 : 1;
  return (
    <g transform={`translate(${x} ${y}) scale(${scale * r})`}>
      <circle cx="0" cy="0" r="11" fill={head ? "#4A4A46" : "#55524C"} />
      <g className={working ? `agent-working ${animClass}` : ""}>
        <ellipse cx="0" cy="0" rx="13" ry="9" fill={p.shirt} />
        <circle cx={fx * 0.4} cy={fy * 0.4} r="7" fill={p.hair} />
        <circle cx={fx} cy={fy} r="5.5" fill={p.skin} />
      </g>
      <circle cx="13" cy="-8" r="3.5" fill={working ? "var(--working)" : "var(--idle)"} className={working ? "dot-working" : ""} stroke="var(--floor-wood)" strokeWidth="1" />
      {!working && (
        <g fill="#7A776E" fontFamily="sans-serif">
          <text x="13" y="-14" fontSize="10" className="zzz">z</text>
          <text x="19" y="-22" fontSize="12" className="zzz z2">Z</text>
          <text x="26" y="-29" fontSize="10" className="zzz z3">z</text>
        </g>
      )}
    </g>
  );
}

import React from "react";
import { FrontAgent } from "./avatars.jsx";

// The primary UI: cutaway building, one department per floor, COO penthouse on top
// (per the approved building-view mockup). Floors are generated from live /activity data;
// clicking a floor opens its department view. At night (app-level .night class) the CSS
// variables dim the facade and active offices read as lit windows.

const FLOOR_H = 70;
const BLD_X = 175;
const BLD_W = 170;
const WIN_X = BLD_X + 10;
const WIN_W = BLD_W - 20;

function Floor({ y, label, isCoo, agents, onClick, night }) {
  const anyWorking = agents.some((a) => a.status === "working");
  const interior = isCoo ? "var(--interior-coo)" : night && anyWorking ? "var(--interior-lit, var(--interior))" : "var(--interior)";
  const slots = agents.length <= 2 ? [0.28, 0.72] : [0.18, 0.5, 0.82];
  return (
    <g className="svg-clickable" onClick={onClick}>
      <rect x={BLD_X - 2} y={y} width={BLD_W + 4} height="6" rx="1" fill="var(--slab)" />
      <rect x={BLD_X + 25} y={y + 8} width={BLD_W - 50} height="14" rx="7" fill={isCoo ? "var(--accent)" : "var(--plate)"} />
      <text x={BLD_X + BLD_W / 2} y={y + 18} fontSize="11" fill="var(--plate-text)" textAnchor="middle" fontFamily="sans-serif">
        {label}
      </text>
      <rect className="floor-hover" x={WIN_X} y={y + 26} width={WIN_W} height="42" fill={interior} stroke="#8B877B" strokeWidth="0.8" />
      {isCoo && (
        <>
          <rect x={WIN_X + 8} y={y + 32} width="11" height="9" rx="1" fill="#FBFAF6" stroke="#9C9685" strokeWidth="0.6" />
          <path d={`M${WIN_X + 10} ${y + 38} l3 -4 l4 3`} stroke="#378ADD" strokeWidth="0.8" fill="none" />
          <circle cx={WIN_X + WIN_W - 13} cy={y + 56} r="5" fill="#4F7F1C" />
          <rect x={WIN_X + WIN_W - 17} y={y + 60} width="9" height="7" rx="1" fill="#8E6C49" />
        </>
      )}
      {agents.map((agent, i) => {
        const cx = WIN_X + WIN_W * slots[Math.min(i, slots.length - 1)];
        const baseY = y + 54;
        const working = agent.status === "working";
        return (
          <g key={agent.id}>
            <FrontAgent x={cx} y={baseY} id={agent.id} working={working} animClass={`d${(i % 3) + 1}`} scale={isCoo ? 1.15 : 1} />
            <rect x={cx - 16} y={baseY + 12} width="32" height="5" rx="1" fill="#8E6C49" />
            {working && <rect x={cx - 6.5} y={baseY + 5} width="13" height="8" rx="1" fill="#3A3A37" />}
          </g>
        );
      })}
    </g>
  );
}

export default function BuildingView({ activity, onSelectDept, night, boot }) {
  const departments = activity?.departments || [];
  const agents = activity?.agents || [];
  const byDept = (dept) =>
    agents.filter((a) => a.department.toLowerCase() === dept.name.toLowerCase() || dept.agents?.includes(a.id));

  const floors = [
    { id: "coo", label: "COO", isCoo: true, agents: [{ id: "coo", status: agents.some((a) => a.status === "working") ? "working" : "idle" }] },
    ...departments.map((d) => ({
      id: d.id,
      label: d.name.replace(/\s*department\s*$/i, ""),
      isCoo: false,
      agents: byDept(d),
    })),
  ];

  const bldTop = 66;
  const lobbyH = 64;
  const bldBottom = bldTop + 8 + floors.length * FLOOR_H + lobbyH;
  const H = bldBottom + 40;

  return (
    <svg viewBox={`0 0 520 ${H}`} preserveAspectRatio="xMidYMid meet">
      <g className={boot ? "boot-cam" : ""}>
        <rect x="0" y="0" width="520" height={H} rx="10" fill="var(--sky)" />
        <rect x="28" y={bldTop + 80} width="66" height={bldBottom - bldTop - 80 + 10} fill="var(--skyline)" />
        <rect x="426" y={bldTop + 140} width="70" height={bldBottom - bldTop - 140 + 10} fill="var(--skyline)" />
        {[0, 1, 2, 3].map((r) => (
          <g key={r}>
            <rect x={38 + (r % 2) * 18} y={bldTop + 96 + r * 22} width="9" height="7" fill="var(--skyline-win)" />
            <rect x={64} y={bldTop + 96 + r * 22} width="9" height="7" fill="var(--skyline-win)" />
            <rect x={438 + (r % 2) * 16} y={bldTop + 156 + r * 22} width="9" height="7" fill="var(--skyline-win)" />
            <rect x={470} y={bldTop + 156 + r * 22} width="9" height="7" fill="var(--skyline-win)" />
          </g>
        ))}
        <g className="cloud">
          <ellipse cx="90" cy="46" rx="17" ry="7" fill="#fff" opacity={night ? 0.25 : 0.9} />
          <ellipse cx="104" cy="41" rx="11" ry="6" fill="#fff" opacity={night ? 0.25 : 0.9} />
        </g>
        <g className="cloud" style={{ animationDelay: "-6s" }}>
          <ellipse cx="420" cy="60" rx="15" ry="6" fill="#fff" opacity={night ? 0.25 : 0.9} />
          <ellipse cx="431" cy="55" rx="10" ry="5" fill="#fff" opacity={night ? 0.25 : 0.9} />
        </g>
        {night && (
          <>
            <circle cx="452" cy="34" r="11" fill="#F4EDD8" />
            <circle cx="447" cy="30" r="9" fill="var(--sky)" />
            <circle cx="120" cy="30" r="1.2" fill="#F4EDD8" />
            <circle cx="200" cy="44" r="1" fill="#F4EDD8" />
            <circle cx="330" cy="26" r="1.2" fill="#F4EDD8" />
            <circle cx="390" cy="48" r="1" fill="#F4EDD8" />
          </>
        )}

        <rect x="0" y={bldBottom} width="520" height="16" fill="var(--sidewalk)" />
        <rect x="0" y={bldBottom + 16} width="520" height="24" fill="var(--road)" />
        <path
          d={`M14 ${bldBottom + 28}H36M56 ${bldBottom + 28}H78M98 ${bldBottom + 28}H120M140 ${bldBottom + 28}H162M182 ${bldBottom + 28}H204M224 ${bldBottom + 28}H246M266 ${bldBottom + 28}H288M308 ${bldBottom + 28}H330M350 ${bldBottom + 28}H372M392 ${bldBottom + 28}H414M434 ${bldBottom + 28}H456M476 ${bldBottom + 28}H498`}
          stroke="#D9D5CC"
          strokeWidth="2"
          fill="none"
          opacity="0.8"
        />
        <g>
          <rect x="60" y={bldBottom + 5} width="36" height="11" rx="3" fill="#F2C230" stroke="#C79A18" />
          <rect x="68" y={bldBottom + 7} width="9" height="5" rx="1" fill="#B5D4F4" />
          <rect x="79" y={bldBottom + 7} width="9" height="5" rx="1" fill="#B5D4F4" />
          <circle cx="68" cy={bldBottom + 17} r="3.5" fill="#2C2C2A" />
          <circle cx="88" cy={bldBottom + 17} r="3.5" fill="#2C2C2A" />
        </g>

        <rect x={BLD_X} y={bldTop + 8} width={BLD_W} height={bldBottom - bldTop - 8} fill="var(--facade)" stroke="#9C9685" />
        <rect x={BLD_X + BLD_W - 8} y={bldTop + 8} width="8" height={bldBottom - bldTop - 8} fill="var(--facade-shade)" />
        <rect x={BLD_X - 2} y={bldTop + 4} width={BLD_W + 4} height="7" rx="2" fill="var(--slab)" />
        <path d={`M${BLD_X + 15} ${bldTop + 4}V${bldTop - 6}`} stroke="#5F5E5A" strokeWidth="1.5" fill="none" />
        <circle cx={BLD_X + 15} cy={bldTop - 7} r="1.8" fill="#E24B4A" />
        <rect x={BLD_X + BLD_W - 37} y={bldTop - 2} width="20" height="6" rx="1" fill="var(--slab)" stroke="#8B877B" strokeWidth="0.5" />

        {floors.map((floor, i) => (
          <Floor
            key={floor.id}
            y={bldTop + 8 + i * FLOOR_H}
            label={floor.label}
            isCoo={floor.isCoo}
            agents={floor.agents}
            night={night}
            onClick={() => onSelectDept(floor.isCoo ? "coo" : floor.id)}
          />
        ))}

        {(() => {
          const ly = bldTop + 8 + floors.length * FLOOR_H;
          return (
            <g>
              <rect x={BLD_X - 2} y={ly} width={BLD_W + 4} height="6" rx="1" fill="var(--slab)" />
              <rect x={WIN_X} y={ly + 6} width={WIN_W} height={lobbyH - 8} fill="var(--interior-dim)" opacity="0.85" />
              <rect x={WIN_X + 12} y={ly + 9} width={WIN_W - 24} height="13" rx="3" fill="#3F3E39" />
              <text x={BLD_X + BLD_W / 2} y={ly + 19} fontSize="11" fill="#F5F2EA" textAnchor="middle" fontFamily="sans-serif">
                The Company
              </text>
              <rect x={BLD_X + BLD_W / 2 - 22} y={ly + 24} width="44" height="7" rx="2" fill="#D85A30" />
              <rect x={BLD_X + BLD_W / 2 - 16} y={ly + 24} width="7" height="7" fill="#F5F2EA" />
              <rect x={BLD_X + BLD_W / 2 - 2} y={ly + 24} width="7" height="7" fill="#F5F2EA" />
              <rect x={BLD_X + BLD_W / 2 + 12} y={ly + 24} width="7" height="7" fill="#F5F2EA" />
              <rect x={BLD_X + BLD_W / 2 - 15} y={ly + 31} width="14" height={lobbyH - 33} fill="#A9CFE4" stroke="#6F8FA3" />
              <rect x={BLD_X + BLD_W / 2 + 1} y={ly + 31} width="14" height={lobbyH - 33} fill="#A9CFE4" stroke="#6F8FA3" />
              <rect x={WIN_X + 12} y={ly + 36} width="24" height="18" fill="#A9CFE4" stroke="#6F8FA3" strokeWidth="0.8" />
              <rect x={WIN_X + WIN_W - 36} y={ly + 36} width="24" height="18" fill="#A9CFE4" stroke="#6F8FA3" strokeWidth="0.8" />
            </g>
          );
        })()}
      </g>
    </svg>
  );
}

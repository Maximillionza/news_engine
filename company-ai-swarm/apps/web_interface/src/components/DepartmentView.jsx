import React from "react";
import { TopDownAgent, palette } from "./avatars.jsx";

// Department drill-down: stylized top-down office (2D with soft shadows) per the approved
// detailed mockup - wooden floor, board room, sofa corner, bookshelf, department head at
// lower center facing the room. Desks are generated from the department's live agents.
// Collaboration rule (spec sec.4.3): when 2+ agents of the department are working, they sit
// in the board room together instead of at their desks.

const DESK_SLOTS = [
  { x: 155, y: 150 },
  { x: 250, y: 150 },
  { x: 155, y: 290 },
  { x: 250, y: 290 },
  { x: 155, y: 400 },
  { x: 250, y: 400 },
];
const BOARD_SEATS = [
  { x: 395, y: 130, dir: 180 },
  { x: 335, y: 168, dir: 90 },
  { x: 455, y: 168, dir: 270 },
  { x: 370, y: 205, dir: 0 },
  { x: 420, y: 205, dir: 0 },
];

function Desk({ x, y, occupied, working, agentId, animClass, showMonitor }) {
  return (
    <g>
      <rect x={x - 30} y={y + 4} width="66" height="34" rx="3" fill="#5C452B" opacity="0.18" />
      <rect x={x - 33} y={y} width="66" height="34" rx="3" fill="#8E6C49" stroke="#6F5236" />
      {showMonitor && <rect x={x - 9} y={y + 4} width="18" height="10" rx="1" fill="#2F2F2D" />}
      <rect x={x - 7} y={y + 18} width="14" height="5" rx="1" fill="#D9D5CC" />
      <path d={`M${x - 9} ${y + 74} A11 11 0 0 0 ${x + 9} ${y + 74}`} stroke="#44423E" strokeWidth="3" fill="none" />
      {occupied ? (
        <TopDownAgent x={x} y={y + 56} id={agentId} working={working} dir={0} animClass={animClass} />
      ) : (
        <circle cx={x} cy={y + 56} r="11" fill="#55524C" />
      )}
    </g>
  );
}

export default function DepartmentView({ dept, agents, night, showAvatarCard }) {
  const deptAgents = agents.filter(
    (a) => a.department.toLowerCase() === dept.name.toLowerCase() || dept.agents?.includes(a.id)
  );
  const head = deptAgents[0];
  const staff = deptAgents.slice(1);
  const working = deptAgents.filter((a) => a.status === "working");
  const collaborating = working.length >= 2;
  const boardRoomAgents = collaborating ? working.slice(0, BOARD_SEATS.length) : [];
  const inBoardRoom = new Set(boardRoomAgents.map((a) => a.id));

  const deskAgents = staff.filter((a) => !inBoardRoom.has(a.id));
  const desks = DESK_SLOTS.map((slot, i) => ({ slot, agent: deskAgents[i] || null })).filter(
    (d, i) => d.agent || i < Math.max(2, deptAgents.length)
  );

  return (
    <svg viewBox="0 0 520 600" preserveAspectRatio="xMidYMid meet">
      <rect x="0" y="0" width="520" height="600" rx="10" fill="var(--page)" />
      <rect x="30" y="14" width="460" height="556" rx="8" fill="var(--wall)" stroke="#9C9685" />
      <rect x="42" y="26" width="436" height="532" rx="4" fill="var(--floor-wood)" />
      <path
        d={Array.from({ length: 20 }, (_, i) => `M42 ${52 + i * 26}H478`).join("")}
        stroke="var(--floor-line)"
        strokeWidth="1"
        fill="none"
      />
      <path
        d={Array.from({ length: 19 }, (_, i) => {
          const y = 26 + i * 26;
          const x = 80 + ((i * 97) % 340);
          return `M${x} ${y}V${y + 26}`;
        }).join("")}
        stroke="var(--floor-line)"
        strokeWidth="0.8"
        fill="none"
      />

      <circle cx="215" cy="40" r="9" fill="#FBFAF6" stroke="#6F5236" strokeWidth="1.5" />
      <path d="M215 40 L215 34.5 M215 40 L219 42" stroke="#3F3E39" strokeWidth="1.2" fill="none" strokeLinecap="round" />

      <rect x="46" y="150" width="15" height="92" rx="2" fill="#6F5236" />
      {[0, 1, 2].map((s) => (
        <g key={s}>
          <rect x="48" y={154 + s * 30} width="11" height="26" fill="#8E6C49" />
          <rect x="49" y={157 + s * 30} width="3" height="20" fill={["#D85A30", "#534AB7", "#2E9E8F"][s]} />
          <rect x="53" y={159 + s * 30} width="3" height="18" fill={["#378ADD", "#EF9F27", "#D4537E"][s]} />
          <rect x="57" y={156 + s * 30} width="2" height="21" fill={["#639922", "#E24B4A", "#378ADD"][s]} />
        </g>
      ))}

      <ellipse cx="88" cy="497" rx="34" ry="15" fill="#5C452B" opacity="0.18" />
      <rect x="55" y="480" width="64" height="26" rx="8" fill="#2E9E8F" stroke="#1D7A6C" />
      <rect x="61" y="484" width="24" height="18" rx="4" fill="#3BB3A1" />
      <rect x="88" y="484" width="24" height="18" rx="4" fill="#3BB3A1" />
      <circle cx="57" cy="493" r="7" fill="#1D7A6C" />
      <circle cx="117" cy="493" r="7" fill="#1D7A6C" />
      <circle cx="86" cy="456" r="12" fill="#8E6C49" stroke="#6F5236" />
      <rect x="79" y="451" width="11" height="8" rx="1" fill="#F5F2EA" stroke="#C9C5BA" strokeWidth="0.5" />

      <rect x="462" y="330" width="13" height="21" rx="2" fill="#E7E1D2" stroke="#9C9685" />
      <circle cx="468" cy="327" r="5.5" fill="#B5D4F4" stroke="#85B7EB" />

      <circle cx="62" cy="44" r="7" fill="#4F7F1C" />
      <circle cx="70" cy="42" r="6" fill="#639922" />
      <circle cx="66" cy="50" r="6" fill="#5A8E1E" />
      <rect x="59" y="53" width="12" height="8" rx="2" fill="#8E6C49" />
      <circle cx="452" cy="530" r="7" fill="#4F7F1C" />
      <circle cx="459" cy="534" r="6" fill="#639922" />
      <rect x="448" y="540" width="12" height="8" rx="2" fill="#8E6C49" />

      <rect x="310" y="60" width="170" height="170" rx="4" fill="var(--interior-dim)" stroke="#9C9685" strokeWidth="2" opacity="0.96" />
      <rect x="340" y="66" width="110" height="14" rx="2" fill="#FBFAF6" stroke="#9C9685" strokeWidth="0.8" />
      <path d="M348 76 L360 70 L370 75 L382 68" stroke="#378ADD" strokeWidth="1.2" fill="none" />
      <rect x="404" y="69" width="3" height="8" fill="#E24B4A" />
      <rect x="410" y="71" width="3" height="6" fill="#E24B4A" />
      <rect x="416" y="67" width="3" height="10" fill="#E24B4A" />
      <ellipse cx="398" cy="172" rx="56" ry="28" fill="#5C452B" opacity="0.2" />
      <ellipse cx="395" cy="168" rx="55" ry="27" fill="#7A5A3B" stroke="#61462C" />
      <ellipse cx="395" cy="166" rx="47" ry="21" fill="#8E6C49" />
      <rect x="372" y="162" width="11" height="8" rx="1" fill="#F5F2EA" />
      <rect x="404" y="168" width="13" height="9" rx="1" fill="#2F2F2D" />
      <circle cx="395" cy="150" r="2.5" fill="#F5F2EA" stroke="#C9C5BA" strokeWidth="0.5" />
      {boardRoomAgents.map((agent, i) => (
        <TopDownAgent
          key={agent.id}
          x={BOARD_SEATS[i].x}
          y={BOARD_SEATS[i].y}
          id={agent.id}
          working
          dir={BOARD_SEATS[i].dir}
          scale={0.92}
          animClass={`d${(i % 3) + 1}`}
        />
      ))}
      {!collaborating &&
        BOARD_SEATS.slice(0, 2).map((seat, i) => (
          <circle key={i} cx={seat.x} cy={seat.y} r="8" fill="none" stroke="#55524C" strokeWidth="2.5" />
        ))}
      <text x="395" y="222" fontSize="11" fill="var(--ink-2)" textAnchor="middle" fontFamily="sans-serif">
        Board room{collaborating ? " · shared task" : ""}
      </text>

      {desks.map(({ slot, agent }, i) => (
        <Desk
          key={i}
          x={slot.x}
          y={slot.y}
          occupied={!!agent}
          working={agent?.status === "working"}
          agentId={agent?.id}
          animClass={`d${(i % 3) + 1}`}
          showMonitor
        />
      ))}

      <ellipse cx="260" cy="512" rx="72" ry="36" fill="#C99F6F" />
      <ellipse cx="260" cy="512" rx="63" ry="29" fill="#D3AE80" />
      <rect x="218" y="470" width="90" height="34" rx="3" fill="#7A5A3B" stroke="#61462C" />
      <rect x="236" y="474" width="16" height="10" rx="1" fill="#2F2F2D" />
      <rect x="268" y="474" width="16" height="10" rx="1" fill="#2F2F2D" />
      <rect x="252" y="490" width="16" height="5" rx="1" fill="#D9D5CC" />
      {head && !inBoardRoom.has(head.id) ? (
        <TopDownAgent x={260} y={522} id={head.id} working={head.status === "working"} dir={0} head />
      ) : (
        <circle cx="260" cy="522" r="13" fill="#4A4A46" />
      )}
      <text x="260" y="556" fontSize="11" fill="var(--ink-2)" textAnchor="middle" fontFamily="sans-serif">
        {head ? `${head.name} · department head` : "Department head"}
      </text>

      {showAvatarCard && head && (
        <g>
          <rect x="352" y="470" width="122" height="64" rx="8" fill="var(--card)" stroke="var(--card-border)" />
          <circle cx="376" cy="496" r="14" fill={palette(head.id).shirt} />
          <circle cx="376" cy="491" r="8" fill={palette(head.id).hair} />
          <circle cx="376" cy="493" r="6.4" fill={palette(head.id).skin} />
          <text x="398" y="492" fontSize="11" fill="var(--ink)" fontFamily="sans-serif">{head.name}</text>
          <text x="398" y="506" fontSize="10" fill="var(--ink-3)" fontFamily="sans-serif">
            {head.status === "working" ? "Working" : "Idle"}
          </text>
          <text x="360" y="524" fontSize="9.5" fill="var(--ink-3)" fontFamily="sans-serif">
            {(head.capabilities || []).slice(0, 2).join(" · ")}
          </text>
        </g>
      )}
    </svg>
  );
}

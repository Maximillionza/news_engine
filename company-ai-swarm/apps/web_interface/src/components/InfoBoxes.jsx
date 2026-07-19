import React from "react";

// The four flanking boxes (spec sec.3.3/4.3): condensed 3-line views, click to expand into
// a full text-only list. Building view aggregates company-wide; department view filters to
// the selected department's agents.

const fmtTime = (iso) => {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
};

export function buildBoxes(activity, dept) {
  if (!activity) return [];
  const m = activity.metrics || {};
  const deptAgentIds = dept
    ? new Set(activity.agents.filter((a) => a.department.toLowerCase() === dept.name.toLowerCase()).map((a) => a.id))
    : null;
  const decisions = (activity.decisions || []).filter(
    (d) => !deptAgentIds || (d.agents_selected || []).some((id) => deptAgentIds.has(id))
  );
  const agents = (activity.agents || []).filter((a) => !deptAgentIds || deptAgentIds.has(a.id));
  const proposals = activity.proposals || [];
  const escalations = activity.escalations || [];

  const decisionLine = (d) =>
    `${fmtTime(d.created_at)}  ${d.objective.length > 60 ? d.objective.slice(0, 57) + "..." : d.objective}`;
  const achieved = decisions.filter((d) => (d.outcome || "").includes("objective_achieved=True")).length;
  const completed = decisions.filter((d) => d.outcome).length;

  return [
    {
      id: "logs",
      title: "Live logs",
      rows: decisions.slice(0, 3).map(decisionLine),
      all: decisions.map((d) => `${decisionLine(d)}\n    → ${d.chosen_action} [${(d.agents_selected || []).join(", ")}]`),
      empty: "No objectives yet",
    },
    {
      id: "metrics",
      title: "Top metrics",
      rows: [
        `Success rate ${completed ? Math.round((achieved / completed) * 100) + "%" : "—"}`,
        `Objectives total ${decisions.length}`,
        `Active agents ${agents.filter((a) => a.status === "working").length} of ${agents.length}`,
      ],
      all: [
        `Success rate: ${completed ? Math.round((achieved / completed) * 100) + "%" : "no completed objectives"}`,
        `Objectives total: ${decisions.length}`,
        `Objectives achieved: ${achieved}`,
        `Agents working: ${agents.filter((a) => a.status === "working").length}`,
        `Agents total: ${agents.length}`,
        `Telemetry records: ${m.telemetry_records ?? 0}`,
      ],
      empty: "No metrics yet",
    },
    {
      id: "workflow",
      title: "Workflow state",
      rows: [
        `${agents.filter((a) => a.status === "working").length} working`,
        `${completed} completed`,
        `${escalations.length} escalated`,
      ],
      all: agents.map((a) => `${a.name} (${a.department}): ${a.status}`),
      empty: "No workflow activity",
    },
    {
      id: "proposals",
      title: "Proposals",
      rows: [
        `${proposals.filter((p) => p.status === "pending").length} pending approval`,
        `${proposals.filter((p) => p.status === "approved").length} approved`,
        `${proposals.filter((p) => p.status === "implemented").length} implemented`,
      ],
      all: proposals.map((p) => `[${p.status}] ${p.target}\n    ${p.proposed_state}`),
      empty: "No proposals yet",
    },
  ];
}

export function InfoBox({ box, onExpand }) {
  return (
    <div className="infobox" onClick={() => onExpand(box)} title="View all">
      <h3>{box.title}</h3>
      {box.rows.length === 0 ? (
        <div className="row">{box.empty}</div>
      ) : (
        box.rows.map((row, i) => (
          <div className="row" key={i}>
            {row}
          </div>
        ))
      )}
      <div className="more">View all ›</div>
    </div>
  );
}

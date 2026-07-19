import React from "react";
import { api } from "../api.js";

// Shared overlay for mail (delivered communications), risks (pending escalations),
// approvals (Evolution proposals with the human hard-gate actions), and expanded info boxes.

const fmt = (iso) => {
  try {
    return new Date(iso).toLocaleString([], { dateStyle: "short", timeStyle: "short" });
  } catch {
    return "";
  }
};

export default function ListPanel({ kind, box, activity, onClose, onAction, toast }) {
  const titles = { mail: "Communications", risks: "Risks and issues", approvals: "Evolution approvals" };
  const title = box ? box.title : titles[kind];

  const proposalAction = async (id, action) => {
    try {
      await api.proposalAction(id, action);
      toast(`Proposal ${id}: ${action} done`);
      onAction?.();
    } catch (e) {
      toast(`${action} failed: ${e.message || e}`);
    }
  };

  let body;
  if (box) {
    body =
      box.all.length === 0 ? (
        <div className="empty">{box.empty}</div>
      ) : (
        box.all.map((line, i) => (
          <div className="list-item" key={i} style={{ whiteSpace: "pre-wrap" }}>
            {line}
          </div>
        ))
      );
  } else if (kind === "mail") {
    const delivered = (activity?.decisions || []).filter((d) => d.outcome);
    body =
      delivered.length === 0 ? (
        <div className="empty">No communications yet</div>
      ) : (
        delivered.map((d) => (
          <div className="list-item" key={d.decision_id}>
            <strong>{(d.outcome || "").includes("objective_achieved=True") ? "Delivered" : "Completed with issues"}:</strong>{" "}
            {d.objective}
            <div className="meta">
              {fmt(d.created_at)} · {d.chosen_action} · agents: {(d.agents_selected || []).join(", ") || "—"}
            </div>
          </div>
        ))
      );
  } else if (kind === "risks") {
    const items = activity?.escalations || [];
    body =
      items.length === 0 ? (
        <div className="empty">No open risks or issues</div>
      ) : (
        items.map((e) => (
          <div className="list-item" key={e.id}>
            <strong>{e.condition}</strong>
            <div>{e.reasoning}</div>
            <div className="meta">{fmt(e.created_at)} · {e.id}{e.decision_id ? ` · decision ${e.decision_id}` : ""}</div>
          </div>
        ))
      );
  } else {
    const items = activity?.proposals || [];
    body =
      items.length === 0 ? (
        <div className="empty">No evolution proposals</div>
      ) : (
        items.map((p) => (
          <div className="list-item" key={p.id}>
            <strong>{p.target}</strong>
            <span className={`status-pill ${p.status}`}>{p.status}</span>
            <div>{p.proposed_state}</div>
            <div className="meta">
              {fmt(p.created_at)} · risk {p.risk} · {p.id}
              {p.resolved_by ? ` · resolved by ${p.resolved_by}` : ""}
            </div>
            <div className="actions">
              {p.status === "pending" && (
                <>
                  <button className="approve" onClick={() => proposalAction(p.id, "approve")}>Approve</button>
                  <button className="reject" onClick={() => proposalAction(p.id, "reject")}>Reject</button>
                </>
              )}
              {p.status === "approved" && (
                <button className="implement" onClick={() => proposalAction(p.id, "implement")}>Implement</button>
              )}
            </div>
          </div>
        ))
      );
  }

  return (
    <div className="overlay">
      <div className="panel">
        <header>
          <span>{title}</span>
          <button onClick={onClose} title="Close">✕</button>
        </header>
        <div className="body">{body}</div>
      </div>
    </div>
  );
}

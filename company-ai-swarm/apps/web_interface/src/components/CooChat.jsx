import React, { useEffect, useRef, useState } from "react";
import { api, readFileAsBase64 } from "../api.js";
import { FrontAgent } from "./avatars.jsx";

// COO focus mode (spec sec.5 + point 10): full-focus chat over a faded building. Shows the
// 10 most recent lines (older ones stay archived server-side). File attach shows a
// paperclip-document chip on pickup; send is assumed successful - an error reply appears
// only if the save fails.
//
// Phase B (Documentation/plans/SDK_MIGRATION_PLAN.md Section 4.2): POST /chat is now
// fire-and-forget - send() gets back an objective_id, not an immediate reply, so it polls
// GET /objectives/{id}/result until the queue worker (a separate process, see
// Scripts/run_queue_worker.py) finishes, then reloads the transcript to pick up the coo's
// reply. "Working on it…" (below) now covers that whole wait, not just the request itself.

const RESULT_POLL_INTERVAL_MS = 800;
const RESULT_POLL_MAX_ATTEMPTS = 25; // ~20s - generous for a synchronous single-agent task,
// not a promise the swarm always replies within this window; see the timeout note in send().

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export default function CooChat({ onClose, onActivityRefresh, showAvatar }) {
  const [messages, setMessages] = useState([]);
  const [archived, setArchived] = useState(0);
  const [text, setText] = useState("");
  const [attachment, setAttachment] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const fileRef = useRef(null);
  const logRef = useRef(null);

  const load = async () => {
    try {
      const h = await api.chatHistory();
      setMessages(h.messages);
      setArchived(h.archived);
    } catch (e) {
      setError(String(e.message || e));
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [messages]);

  const pickFile = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setAttachment({ file, name: file.name });
    event.target.value = "";
  };

  const send = async () => {
    if (busy || (!text.trim() && !attachment)) return;
    setBusy(true);
    setError(null);
    try {
      let filePath = null;
      if (attachment) {
        const b64 = await readFileAsBase64(attachment.file);
        const saved = await api.uploadFile(attachment.name, b64);
        filePath = saved.path;
      }
      const response = await api.chatSend(text.trim(), filePath);
      setText("");
      setAttachment(null);
      await load(); // shows the user's own message immediately either way

      // Documentation/plans/2026-07-19-dynamic-department-routing-design.md: the COO may
      // come back needing more detail instead of an objective_id - its reply is already in
      // the transcript load() just fetched, so there's nothing to poll.
      if (response.status === "needs_clarification") {
        onActivityRefresh?.();
        return;
      }

      const objectiveId = response.objective_id;
      for (let attempt = 0; attempt < RESULT_POLL_MAX_ATTEMPTS; attempt++) {
        await sleep(RESULT_POLL_INTERVAL_MS);
        const result = await api.objectiveResult(objectiveId);
        if (result.status === "completed" || result.status === "failed") break;
      }
      // Reload either way: on settlement the reply is there; on timeout this at least
      // shows nothing-new rather than leaving "Working on it…" up after busy clears - the
      // dashboard's own periodic /activity refresh, or reopening chat, will pick up a reply
      // that arrives after this window.
      await load();
      onActivityRefresh?.();
    } catch (e) {
      setError(`Could not deliver that: ${e.message || e}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="overlay">
      <div className="panel" style={{ height: "88%" }}>
        <header>
          <span>COO</span>
          <button onClick={onClose} title="Close">✕</button>
        </header>
        {showAvatar && (
          <div className="coo-avatar">
            <svg width="70" height="52" viewBox="-35 -34 70 52">
              <FrontAgent x={0} y={0} id="coo" working scale={1.6} />
            </svg>
          </div>
        )}
        <div className="body chat-log" ref={logRef}>
          {archived > 0 && <div className="chat-archived">{archived} earlier messages archived</div>}
          {messages.length === 0 && <div className="empty">Give the COO an objective to get the swarm working.</div>}
          {messages.map((m) => (
            <div key={m.id} className={`chat-msg ${m.role === "user" ? "user" : "coo"}`}>
              {m.content}
            </div>
          ))}
          {busy && <div className="chat-msg coo">Working on it…</div>}
          {error && <div className="chat-msg coo" style={{ color: "#a32d2d" }}>{error}</div>}
        </div>
        {attachment && (
          <div className="attachment-chip">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5z" />
              <path d="M14 3v5h5" />
              <path d="M12 18v-6M9.5 14.5a2.5 2.5 0 0 0 5 0" />
            </svg>
            {attachment.name}
            <button onClick={() => setAttachment(null)} title="Remove">✕</button>
          </div>
        )}
        <div className="chat-input">
          <button className="attach" onClick={() => fileRef.current?.click()} title="Attach a file">📎</button>
          <input ref={fileRef} type="file" style={{ display: "none" }} onChange={pickFile} />
          <input
            type="text"
            placeholder="Instruct the swarm…"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            disabled={busy}
          />
          <button onClick={send} disabled={busy}>{busy ? "…" : "Send"}</button>
        </div>
      </div>
    </div>
  );
}

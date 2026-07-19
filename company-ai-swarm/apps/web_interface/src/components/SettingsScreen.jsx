import React, { useState } from "react";

// Separate settings screen (spec sec.6, point 7): live refresh is paused while this is
// open (App skips polling when the settings view is active). Intervals are 30s steps up to
// 5 minutes, plus "Only on manual refresh".

const INTERVALS = [
  { value: 30, label: "30 seconds" },
  { value: 60, label: "1 minute" },
  { value: 120, label: "2 minutes" },
  { value: 300, label: "5 minutes" },
  { value: 0, label: "Only on manual refresh" },
];

export default function SettingsScreen({ settings, onSave, onCancel }) {
  const [draft, setDraft] = useState({ ...settings });
  const set = (key, value) => setDraft((d) => ({ ...d, [key]: value }));

  return (
    <div className="settings">
      <div className="panel" style={{ width: "100%" }}>
        <header>
          <span>Settings</span>
        </header>
        <div className="body">
          <div className="field">
            <span>Auto refresh interval</span>
            <select value={draft.refreshSec} onChange={(e) => set("refreshSec", Number(e.target.value))}>
              {INTERVALS.map((i) => (
                <option key={i.value} value={i.value}>{i.label}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <span>Building theme follows time of day</span>
            <input type="checkbox" className="switch" checked={draft.timeTheme} onChange={(e) => set("timeTheme", e.target.checked)} />
          </div>
          <div className="field">
            <span>Show avatar card in department and COO views</span>
            <input type="checkbox" className="switch" checked={draft.showAvatars} onChange={(e) => set("showAvatars", e.target.checked)} />
          </div>
          <div className="field">
            <span>API key</span>
            <input type="text" value={draft.apiKey} onChange={(e) => set("apiKey", e.target.value)} style={{ width: 180 }} />
          </div>
          <div className="buttons">
            <button onClick={onCancel}>Cancel</button>
            <button className="primary" onClick={() => onSave(draft)}>Save and resume</button>
          </div>
        </div>
      </div>
    </div>
  );
}

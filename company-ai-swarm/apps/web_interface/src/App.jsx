import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api.js";
import TopNav from "./components/TopNav.jsx";
import BuildingView from "./components/BuildingView.jsx";
import DepartmentView from "./components/DepartmentView.jsx";
import CooChat from "./components/CooChat.jsx";
import ListPanel from "./components/ListPanel.jsx";
import SettingsScreen from "./components/SettingsScreen.jsx";
import { buildBoxes, InfoBox } from "./components/InfoBoxes.jsx";

const SETTINGS_KEY = "company.settings";
const BOOT_KEY = "company.bootPlayed";
const MAIL_SEEN_KEY = "company.mailSeen";

const defaultSettings = {
  refreshSec: 30,
  timeTheme: true,
  showAvatars: true,
  apiKey: localStorage.getItem("company.apiKey") || "dev-only-api-key",
};

function loadSettings() {
  try {
    return { ...defaultSettings, ...JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}") };
  } catch {
    return { ...defaultSettings };
  }
}

export default function App() {
  const [settings, setSettings] = useState(loadSettings);
  const [activity, setActivity] = useState(null);
  const [fetchError, setFetchError] = useState(null);
  const [view, setView] = useState({ name: "building" });
  const [overlay, setOverlay] = useState(null); // 'coo' | 'mail' | 'risks' | 'approvals' | {box}
  const [toastMsg, setToastMsg] = useState(null);
  const [clock, setClock] = useState(new Date());
  const [boot, setBoot] = useState(() => !sessionStorage.getItem(BOOT_KEY));
  const [mailSeen, setMailSeen] = useState(() => Number(localStorage.getItem(MAIL_SEEN_KEY) || 0));
  const toastTimer = useRef(null);

  const toast = useCallback((msg) => {
    setToastMsg(null);
    clearTimeout(toastTimer.current);
    requestAnimationFrame(() => setToastMsg(msg));
    toastTimer.current = setTimeout(() => setToastMsg(null), 3600);
  }, []);

  const refresh = useCallback(async () => {
    try {
      setActivity(await api.activity());
      setFetchError(null);
    } catch (e) {
      setFetchError(String(e.message || e));
    }
  }, []);

  // Boot animation: once per session (spec point 9). Refreshing the page does not replay.
  useEffect(() => {
    if (!boot) return;
    const t = setTimeout(() => {
      sessionStorage.setItem(BOOT_KEY, "1");
      setBoot(false);
    }, 4400);
    return () => clearTimeout(t);
  }, [boot]);

  // Configurable polling (spec point 7), paused while settings is open (spec sec.6).
  useEffect(() => {
    refresh();
    if (!settings.refreshSec || view.name === "settings") return;
    const id = setInterval(refresh, settings.refreshSec * 1000);
    return () => clearInterval(id);
  }, [refresh, settings.refreshSec, view.name]);

  useEffect(() => {
    const id = setInterval(() => setClock(new Date()), 30000);
    return () => clearInterval(id);
  }, []);

  const night = settings.timeTheme && (clock.getHours() >= 18 || clock.getHours() < 6);

  const dept = useMemo(() => {
    if (view.name !== "dept" || !activity) return null;
    return activity.departments.find((d) => d.id === view.deptId) || null;
  }, [view, activity]);

  const boxes = useMemo(() => buildBoxes(activity, dept), [activity, dept]);

  const delivered = (activity?.decisions || []).filter((d) => d.outcome);
  const badges = {
    mail: delivered.filter((d) => new Date(d.created_at).getTime() > mailSeen).length,
    coo: 0,
    risks: activity?.escalations?.length || 0,
    approvals: (activity?.proposals || []).filter((p) => p.status === "pending").length,
    settings: 0,
  };

  const openNav = (id) => {
    if (id === "settings") {
      setOverlay(null);
      setView((v) => (v.name === "settings" ? { name: "building" } : { name: "settings", back: v }));
      return;
    }
    if (id === "mail") {
      const now = Date.now();
      localStorage.setItem(MAIL_SEEN_KEY, String(now));
      setMailSeen(now);
    }
    setOverlay((cur) => (cur === id ? null : id));
  };

  const saveSettings = (draft) => {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(draft));
    localStorage.setItem("company.apiKey", draft.apiKey);
    setSettings(draft);
    setView(view.back || { name: "building" });
    toast("Settings saved");
  };

  const overlayIsPanel = overlay && overlay !== "coo";
  const sceneFaded = overlay === "coo";

  let scene = null;
  let title = null;
  if (view.name === "settings") {
    scene = (
      <SettingsScreen
        settings={settings}
        onSave={saveSettings}
        onCancel={() => setView(view.back || { name: "building" })}
      />
    );
  } else if (view.name === "dept" && dept) {
    title = (
      <div className="scene-title">
        <span className="back" onClick={() => setView({ name: "building" })}>← Building view</span>
        {dept.name}
        <span className="clock">{night ? "Night" : "Day"} · {clock.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
      </div>
    );
    scene = (
      <DepartmentView dept={dept} agents={activity?.agents || []} night={night} showAvatarCard={settings.showAvatars} />
    );
  } else {
    title = (
      <div className="scene-title">
        {view.name === "dept" ? "Loading…" : "The Company"}
        <span className="clock">{night ? "Night" : "Day"} · {clock.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
        {!settings.refreshSec && (
          <span className="back" onClick={refresh} title="Refresh now">⟳ Refresh</span>
        )}
      </div>
    );
    scene = (
      <BuildingView
        activity={activity}
        night={night}
        boot={boot}
        onSelectDept={(id) => {
          if (boot) return;
          if (id === "coo") setOverlay("coo");
          else setView({ name: "dept", deptId: id });
        }}
      />
    );
  }

  const showSides = view.name !== "settings";

  return (
    <div className={`app ${night ? "night" : ""}`}>
      {!boot && <TopNav open={overlay || (view.name === "settings" ? "settings" : null)} onOpen={openNav} badges={badges} />}
      <div className="layout">
        {showSides ? (
          <div className="side">
            {boxes.slice(0, 2).map((b) => (
              <InfoBox key={b.id} box={b} onExpand={(box) => setOverlay({ box })} />
            ))}
          </div>
        ) : (
          <div />
        )}
        <div className={`center ${sceneFaded ? "faded" : ""}`}>
          {title}
          <div className="scene-wrap">
            {scene}
            {boot && <div className="boot-title">THE COMPANY</div>}
          </div>
          {view.name !== "settings" && (
            <div className="legend">
              <span><span className="swatch" style={{ background: "var(--working)" }} />Working</span>
              <span><span className="swatch" style={{ background: "var(--idle)" }} />Idle</span>
              {view.name === "building" && <span>Click a floor to open its department</span>}
              {fetchError && <span style={{ color: "#a32d2d" }}>Offline: {fetchError}</span>}
            </div>
          )}
          {overlay === "coo" && (
            <CooChat onClose={() => setOverlay(null)} onActivityRefresh={refresh} showAvatar={settings.showAvatars} />
          )}
          {overlayIsPanel && (
            <ListPanel
              kind={typeof overlay === "string" ? overlay : null}
              box={typeof overlay === "object" ? overlay.box : null}
              activity={activity}
              onClose={() => setOverlay(null)}
              onAction={refresh}
              toast={toast}
            />
          )}
        </div>
        {showSides ? (
          <div className="side">
            {boxes.slice(2, 4).map((b) => (
              <InfoBox key={b.id} box={b} onExpand={(box) => setOverlay({ box })} />
            ))}
          </div>
        ) : (
          <div />
        )}
      </div>
      {toastMsg && <div className="toast">{toastMsg}</div>}
    </div>
  );
}

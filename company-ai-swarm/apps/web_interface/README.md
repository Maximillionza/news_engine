# Web Interface - The Company Dashboard

The animated building dashboard over the swarm, per
`Documentation/ui/swarm_dashboard_design_spec.md` and the two approved SVG mockups
(building view + department view).

**Spec:** Specifications/2 - construction-framework/The Company Repository Blueprint Specification (CRBS).md

**Status:** Implemented (dashboard build, post-Phase-11). React 18 + Vite, SVG scenes,
no state library - a single polling loop over the gateway's `/activity` endpoint.

## Run

```bash
# one-time
cd apps/web_interface && npm install && npm run build

# serve (gateway mounts dist/ at /ui)
.venv/Scripts/python.exe Scripts/run_gateway.py
# open http://127.0.0.1:8000/ui/
```

Dev mode with hot reload (`npm run dev`, port 5173) proxies API calls to a gateway already
running on port 8000.

## What maps to what

| Spec item | Where |
| --- | --- |
| Boot animation (once per session) | `App.jsx` (`sessionStorage`), `.boot-cam` keyframes in `styles.css` |
| Building view, one department per floor, COO penthouse | `components/BuildingView.jsx` |
| Department view (top-down office, board room, head at lower center) | `components/DepartmentView.jsx` |
| Working/sleeping agents (bob + zzz animations, status dots) | `components/avatars.jsx` + CSS keyframes |
| Board room = 2+ department agents working together | `DepartmentView.jsx` collaboration rule |
| 4 info boxes, condensed 3 lines, click to expand (text-only) | `components/InfoBoxes.jsx` + `ListPanel.jsx` |
| COO focus mode: chat, file attach (paperclip chip), building faded | `components/CooChat.jsx` |
| Chat shows 10 most recent lines, older archived | gateway `/chat` (server-side), `CooChat.jsx` |
| Top nav: mail / chat / risks / approvals / settings, badges | `components/TopNav.jsx` |
| Settings screen, pauses refresh, 30s-5min intervals or manual | `components/SettingsScreen.jsx`, polling gate in `App.jsx` |
| Day/night theme (after 18:00 building darkens, active offices light up) | `.night` CSS variables in `styles.css` |

Backend endpoints these consume: `apps/api_gateway/dashboard_api.py` (`/activity`, `/chat`,
`/files`, `/proposals/{id}/approve|reject|implement`). File uploads land in
`uploads/inbox/` - the pickup location referenced in the chat message to the COO.

Honest limits: agent "working" status is derived (selected by a decision in the last 120s -
execution is synchronous, nothing is ever mid-flight when polled), and the board room only
populates when a department has 2+ agents, which needs SDK-built additions to the one-agent
MVS roster.

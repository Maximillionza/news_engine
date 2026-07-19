# Swarm Dashboard UI — Design Specification

## 1. Core Architecture

### 1.1 Navigation Hierarchy
- **Level 0:** Welcome Animation (boot only, once per session)
- **Level 1:** Building View (primary UI) — high-level agent activity across all departments
- **Level 2:** Department View (drill-down) — office layout with agents, department head, desks/cubicles
- **Level 3:** COO Focus Mode (full-screen) — chat + file upload interface, building faded in background

### 1.2 Persistent Elements
- **Top Navigation Bar** (always visible except during welcome animation): 5 icon buttons in a rounded bezelled bar
  1. Letter icon → Communications/Mailbox (project deliverables, updates)
  2. Chat bubble icon → COO chat access
  3. Triangle with exclamation → Risks/Issues affecting the swarm
  4. Box with tick mark → Evolution proposal approvals
  5. Settings icon → Settings menu (separate screen, pauses live refresh)

---

## 2. Welcome Animation (Boot Only)

### 2.1 Behavior
- Plays only once per session (not on refresh)
- Starts from top of building, camera rotates down to show front facade
- Layers reveal departments as camera rotates
- Final frame: building front-facing, ready for interaction

### 2.2 Design Notes
- Smooth, seamless rotation (no jarring cuts)
- Grey building base color (adjusts by time of day — see Section 5)
- Clear labeling of departments as layers reveal
- Transition smoothly into Building View

---

## 3. Building View (Level 1)

### 3.1 Visual Structure
- **Center:** Grey building facade showing all departments as visible windows/offices
- **Left & Right:** 4 information boxes (2 left, 2 right) showing aggregated metrics and workflow states
- Each department is a clickable window showing high-level agent activity

### 3.2 Department Windows
- **Labeled above each window** with department name (Research, Engineering, Compliance, Operations)
- **Distinct design per department** (COO gets special treatment as most important)
- **Agent animation states:**
  - **Inactive:** Sleeping agent (zzz animation)
  - **Active/Working:** Agent performing seamless loop of different work actions (no breaks in animation, maintains illusion)
- **Click to drill into department view**

### 3.3 Information Boxes (4 Aggregated)
- **Position:** 2 on left, 2 on right of building
- **Content:** Live Logs (last 3 items), Top 3 metrics
- **Interactivity:** 
  - Click to expand and see full list (text-only)
  - Condensed view by default
  - Collapse back to summary view
- **Real-time updates:** Refreshes at configured interval (default 30s)

---

## 4. Department View (Level 2)

### 4.1 Navigation
- Accessed by clicking a department window in Building View
- Returns to Building View via back button or clicking building icon in top nav

### 4.2 Visual Structure
- **Top-down office layout** with stylized hybrid perspective (2D floorplan with fake shadows for depth)
- **Department Head:** Lower center of screen, facing top center
- **Desks/Cubicles:** Arranged around office representing number of agents spawned
- **Conference Room:** Visible area for collaborative task animations
- **Avatar Display** (optional, toggled in settings): Static image of each agent when clicked

### 4.3 Agent States & Animations
- **Inactive Agents:** zzz animation at their desk/cubicle (sleeping)
- **Active Agents:** Performing at their desk
- **Collaborative Work:** When agents work together on single task:
  - Agents move from desks to conference room
  - Animated working together (seamless loop)
  - Animation ends only when task fully delivered
  - Agents return to desks
- **Information Boxes:** Same 4 boxes as Building View, now showing **department-specific data** (e.g., dept's last 3 projects, dept's top 3 metrics)

### 4.4 Interaction
- No clicking into individual agents (avatars are representative only, not detailed)
- Focus remains at department level
- Can still access top nav (communications, chat, risks, approvals, settings)

---

## 5. COO Focus Mode (Full-Screen)

### 5.1 Access
- Click chat bubble icon in top nav
- Expands to fill screen
- Building fades into background (if possible without complexity)

### 5.2 Interface
- **Chat Panel:**
  - Shows 10 most recent chat lines
  - Previous chats archived (reduces performance impact)
  - Text-based interaction only
  - Swarm responses visible in chat

- **File Upload:**
  - Click to attach files
  - Visual confirmation on attachment: document icon with paperclip
  - File is saved to a location the swarm can access
  - Send button triggers swarm to process file location
  - Only show error response if file save fails (assume success otherwise)

### 5.3 Behavior
- **Takes full focus** (building faded, cannot interact with it)
- Can close/exit back to Building View
- Chat history persists within session
- File attachments queue sequentially

---

## 6. Settings Screen

### 6.1 Access
- Settings icon in top nav
- Opens as separate screen (not modal overlay)
- Pauses live refresh while open

### 6.2 Configuration Options
1. **Refresh Interval**
   - Default: 30 seconds
   - Intervals: 30s, 1m, 2m, 5m
   - Option: "Only on manual refresh" (no auto-refresh)

2. **Display Options**
   - Agent avatar display in department view (toggle on/off)
   - Building theme based on time of day (toggle on/off)
   - Other customization as needed

3. **Actions**
   - Resume live refresh (closes settings, returns to previous view)
   - Cancel (no changes, returns to previous view)

---

## 7. Visual Design

### 7.1 Building Appearance
- **Base color:** Grey
- **Time-based theming:**
  - After 6 PM: Building darkens
  - Office lights illuminate in active departments/agents
  - Creates visual indicator of activity level during off-hours

### 7.2 Agent Avatars
- **Style:** Cartoon-based (non-detailed, representative)
- **Humanization:** Not heavily detailed; simple, recognizable silhouettes
- **Consistency:** Same avatar style across all views
- **Static image optional:** Can display static avatar in department view or COO context if enabled in settings

### 7.3 Color & Theming
- Primary: Building grey (adjusts by time of day)
- Secondary: Information box backgrounds
- Accent: Highlight colors for active agents, interactive elements
- Dark mode support should match time-of-day theme

### 7.4 Typography & Spacing
- Clean, readable labels on all departments
- Crisp info box headers and data
- Generous spacing to avoid visual clutter
- Consistent sizing across all views

---

## 8. Animations & Motion

### 8.1 Boot Animation
- Smooth camera rotation from top of building to front view
- No jarring cuts or frame drops
- Duration: 3–5 seconds (smooth but not slow)
- Plays once, then never again in that session

### 8.2 Agent Working Animations
- **Loop of different work actions:** typing, reviewing, collaborating
- Seamless transitions (no breaks, maintains illusion of work)
- Different action sequences for variety (don't repeat exact same action 3x)

### 8.3 Collaboration Animation
- Agents move from desks to conference room (smooth transition)
- Animated working together in conference room (seamless loop)
- Animation ends when task delivery confirmed
- Agents return to desks

### 8.4 Transitions Between Views
- Building ↔ Department View: Smooth zoom/pan (no cuts)
- Any View ↔ COO Focus: Fade building to background, focus on chat
- Settings screen: Slide in from side or fade (no live refresh while open)

### 8.5 Box Expansion/Collapse
- Information boxes expand on click (smooth animation)
- Full list displays (text-only)
- Click to collapse back to summary
- No performance stutters

---

## 9. Real-Time Updates & Performance

### 9.1 Refresh Strategy
- Default interval: 30 seconds
- User-configurable: 30s, 1m, 2m, 5m, or manual-only
- Paused while in Settings menu
- **Low-impact updates:** Only changed data refreshes (no full redraws)

### 9.2 Chat & File Management
- Chat: Shows 10 most recent lines; archive old messages (don't keep all in DOM)
- Files: Upload queue processes sequentially
- No performance impact from growing chat history

---

## 10. Top Navigation Bar

### 10.1 Persistent Element
- **Position:** Top of screen, rounded bezelled container
- **Always visible:** Except during welcome animation
- **Icons (left to right):**
  1. ✉️ Letter → Communications/Mailbox
  2. 💬 Chat bubble → COO Chat
  3. ⚠️ Triangle + Exclamation → Risks/Issues
  4. ☑️ Box with checkmark → Evolution Approvals
  5. ⚙️ Settings → Settings Screen

### 10.2 Behavior
- Icons are clickable buttons
- Each icon shows current status (e.g., unread count on mailbox)
- Clicking icon navigates to corresponding feature
- From COO Focus mode, can still access other nav items

---

## 11. Data Integration

### 11.1 API Endpoints (from Swarm)
- `POST /objectives` → Submit objective from COO
- `GET /objectives/{decision_id}` → Track objective status
- `GET /agents` → Fetch agent list and status
- File pickup location: Configured path for swarm to consume uploads

### 11.2 Data Refresh
- Poll endpoints on configured interval (default 30s)
- Update: agent status, task completions, metrics, communications
- Archive old messages/logs to prevent DOM bloat

---

## 12. Implementation Notes

- **No pixel-perfect design required** — focus on interaction flow and animation timing
- **Responsive considerations:** Desktop-first, mobile friendliness if applicable
- **Performance:** Keep smooth animations, minimal re-renders, efficient data loading
- **Accessibility:** Ensure labels, icons, and navigation are clear and keyboard-navigable

---

## Appendix: User Flows

### Flow 1: Check Agent Status (Building View)
1. User opens dashboard
2. Sees boot animation (first load only)
3. Building View shows all departments with agent activity
4. 4 information boxes show aggregated metrics
5. User can click a department to drill down for details

### Flow 2: Drill into Department
1. From Building View, click a department window
2. Department View opens, showing office layout
3. Department head visible, agents at desks/cubicles
4. Can see collaborative agents in conference room
5. Information boxes show dept-specific data
6. Back button returns to Building View

### Flow 3: Communicate with COO
1. Click chat bubble in top nav
2. COO Focus Mode opens, building fades
3. User types message and sends
4. Swarm response appears in chat
5. User can attach file (document icon confirms pickup)
6. Send file → swarm processes
7. Close to return to previous view

### Flow 4: Configure Settings
1. Click settings icon in top nav
2. Settings screen opens (live refresh paused)
3. Adjust refresh interval, toggle display options
4. Click Resume to save and return to previous view

### Flow 5: Check Communications
1. Click letter icon in top nav
2. Mailbox shows recent communications (projects delivered, updates)
3. Can read full message or dismiss
4. Return to previous view

---

**Design Specification Complete. Ready for Claude Design implementation.**

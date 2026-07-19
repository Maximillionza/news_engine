# SDK Migration Plan: The Company

**Scope:** Migrate from stub agents (StubModelProvider) to real Claude reasoning via Claude Agent SDK. Convert execution from synchronous to asynchronous. Enable stateful voice-first interface as the primary Director.

**Effort:** ~80–120 hours (planning + implementation + testing)  
**Timeline:** 3–4 weeks at full-time focus  
**Risk Level:** Medium (touches core execution paths; existing tests remain valid through interface contracts)

---

## 1. Problem Statement

**Current state:**
- Agents respond with canned stubs; no real reasoning
- COOOrchestrator blocks on `receive_objective()` — HTTP POST /chat waits until workflow completes
- The web dashboard polls for state but sees no true "in-flight" execution — agents complete instantly
- ModelGateway's provider is injectable but only StubModelProvider exists

**Why SDK:**
- The Claude Agent SDK gives us the Claude Code harness (agent loop, built-in tools, session/context management) as a library, instead of hand-rolling a tool-use loop against the raw Messages API
- Reasoning takes 5–30 seconds per agent; blocking HTTP requests can't hold that long
- Async execution model matches the swarm's async nature (multiple departments reasoning in parallel)
- Voice-first interface becomes the Director with continuous context, not a REST client polling stubs

**Billing correction, revised (2026-07-19):** An earlier pass of this section claimed the Agent SDK always requires API-key billing and that subscription auth can't power a headless swarm. That was too broad — corrected here.

The Agent SDK is a harness, not a billing tier by itself, and it supports **two** distinct credential paths:
- `ANTHROPIC_API_KEY` (or Bedrock / Claude Platform on AWS / Vertex / Foundry) — standard per-token usage billing.
- `CLAUDE_CODE_OAUTH_TOKEN`, generated once via `claude setup-token` — authenticates against a personal Claude **Pro/Max/Team/Enterprise subscription** and is explicitly documented for CI/scripts/headless automation. Claude Code's auth docs state that `ANTHROPIC_API_KEY`/`ANTHROPIC_AUTH_TOKEN`/`apiKeyHelper` "apply to the CLI and the surfaces that wrap it, including... the Agent SDK" — `CLAUDE_CODE_OAUTH_TOKEN` sits in that same precedence chain, so the Python/TypeScript Agent SDK packages honor it too.

The restriction that actually exists — *"Anthropic does not allow third party developers to offer claude.ai login or rate limits for their products"* — is about **multi-tenant resale**: building a product where other people's usage rides on your subscription. It does not bar a single account holder from automating their own subscription for their own tooling. Since The Company is a personal swarm with you as sole Director, `CLAUDE_CODE_OAUTH_TOKEN` is a workable path — **if it moves to serving other users, that traffic must switch to API-key billing.** (This also applies cleanly if you distribute the whole swarm for someone else to run on their own machine under their own Claude account — that's them bringing their own subscription for their own personal use, not you offering yours to them.)

**Caveats that do apply, and change the implementation:**
1. `CLAUDE_CODE_OAUTH_TOKEN` is **not read in `--bare` mode** — bare invocations fall back to requiring `ANTHROPIC_API_KEY`.
2. Subscription auth only works through the **Agent SDK or `claude` CLI** (`claude_agent_sdk.query()` / subprocess `claude -p`) — **not** the plain `anthropic` Python/TS client's `messages.create()`, which only ever accepts an API key. Section 4.1's `AnthropicModelProvider`, as originally scoped ("Calls Claude API, not Agent SDK directly"), is incompatible with subscription billing as written — getting subscription billing for swarm agents (not just voice) means rebuilding that provider on top of the Agent SDK/CLI, not the raw API client. See the revised Section 4.1 below.
3. Subscription usage limits are shared, finite windows sized for one interactive user. A multi-agent swarm firing off many parallel/background agent calls can burn through that budget materially faster — this needs sizing, not just wiring up the token.
4. Any future non-Director user of The Company must authenticate via API key, not subscription — unless they're running their own separate installation under their own account, per the distribution note above.

---

## 2. Current Architecture

```
User (dashboard / voice)
  ↓ HTTP (synchronous)
API Gateway (FastAPI)
  ├─ POST /chat → blocks until result
  ├─ GET /activity → instant state snapshot
  └─ GET /agents → instant list
  ↓
COOOrchestrator.receive_objective()
  ├─ Interpret (keyword match)
  ├─ Select (department + agent)
  ├─ Dispatch (workflow_engine.execute_workflow())
  │  └─ Agent execution (StubModelProvider → instant output)
  └─ return result (to blocked HTTP response)
  ↓
AgentRuntime.execute()
  └─ ModelGateway.invoke() → StubModelProvider (1ms)
```

**Key synchronous assumption:** Everything completes within HTTP timeout (30s).

---

## 3. Target Architecture

```
Voice-first UI (Agent SDK container, real Claude sessions)
  ↓ HTTP (fire-and-forget, async)
API Gateway (FastAPI, now with async job queue)
  ├─ POST /chat → returns {objective_id, status: "queued"} immediately
  ├─ GET /activity → includes in-flight objectives + completion ETA
  ├─ GET /objectives/{id}/result → polls for completion, returns {status, result} when ready
  └─ GET /agents → includes live status (executing, idle, waiting)
  ↓
Objective Queue (PostgreSQL table or Redis)
  ├─ Each objective is a Job record: {id, status, payload, result, created_at, updated_at}
  └─ Background worker polls queue, executes objectives
  ↓
COOOrchestrator (unchanged logic)
  ├─ Interpret, Select, Dispatch (same)
  ├─ Now calls AgentRuntime with real provider, not stub
  └─ Returns result → job record updated
  ↓
Agent Execution (real Claude Code sessions)
  ├─ AgentRuntime.execute() with AnthropicModelProvider
  └─ ModelGateway.invoke() → Claude Agent SDK (5–30s per agent)
```

**Key async assumption:** Voice interface polls for completion; no HTTP request hangs.

---

## 4. Component-by-Component Changes

### 4.1 ModelGateway & Providers

**Current:**
- `shared/model_gateway.py`: `ModelGateway(provider)` is injectable
- `StubModelProvider`: returns `{"output": "stub response"}`
- No real provider exists

**Changes (revised 2026-07-19 — see billing correction in Section 1):**
1. Create two providers behind the same interface, selected by `MODEL_PROVIDER` env var:
   - `AnthropicModelProvider(api_key)` — calls the raw Claude API via the `anthropic` client. Bills per-token against `ANTHROPIC_API_KEY`. Simple, but cannot use subscription auth.
   - `AgentSDKModelProvider()` — invokes Claude via `claude_agent_sdk.query()` (or a `claude -p` subprocess). Reads credentials via the normal Claude Code precedence chain, so it picks up `CLAUDE_CODE_OAUTH_TOKEN` (subscription billing) if set, or falls back to `ANTHROPIC_API_KEY`. **Must not run with `--bare`** — bare mode ignores `CLAUDE_CODE_OAUTH_TOKEN` and silently requires an API key instead.
   - Both implement `invoke(task, context)` → structured task output; both handle errors gracefully (rate limits/usage-window exhaustion, API failures)
2. `ModelGateway.__init__()` gets env var support: `MODEL_PROVIDER=anthropic` (API key) vs `agent_sdk` (subscription-capable) vs `stub`
3. No changes to `ModelGateway` interface; all existing agent code works unchanged regardless of which provider is active
4. If the swarm should run entirely on subscription billing, `agent_sdk` is the one to use for production — `anthropic` remains useful for cheap, high-throughput or CI paths where you'd rather pay per-token than draw down subscription usage windows

**Files:**
- `shared/model_gateway.py` (add env var handling)
- `shared/providers/anthropic_provider.py` (new)
- `shared/providers/agent_sdk_provider.py` (new — wraps `claude_agent_sdk.query()`)
- `shared/providers/__init__.py` (new)

**Effort:** ~14 hours (was ~8h for a single API-key provider; +6h for the Agent SDK/subscription provider, since it's a subprocess/async-generator integration rather than a direct HTTP client call, plus a smoke test that verifies `CLAUDE_CODE_OAUTH_TOKEN` is actually being picked up instead of silently falling back to an API key)

---

### 4.2 Objective Execution: Synchronous → Asynchronous

**Current:**
- `POST /chat` → `COOOrchestrator.receive_objective()` → blocks → returns result

**Changes:**
1. Create an `ObjectiveQueue` (database table):
   ```sql
   CREATE TABLE objective_queue (
     id TEXT PRIMARY KEY,
     status TEXT (queued/executing/completed/failed),
     objective TEXT,
     required_output TEXT,
     result JSON,
     error TEXT,
     created_at TIMESTAMP,
     started_at TIMESTAMP,
     completed_at TIMESTAMP,
     submitted_by TEXT (identity_id)
   );
   ```

2. `POST /chat` now:
   - Validates the message (same)
   - Creates an ObjectiveQueue row with `status=queued`
   - Returns `{objective_id: "OBJ-xyz", status: "queued"}` immediately
   - Does NOT call `receive_objective()`

3. New background worker (separate from FastAPI process):
   - Polls `objective_queue WHERE status='queued'` every 100ms
   - Updates row to `status='executing'`
   - Calls `COOOrchestrator.receive_objective()` (blocking is fine in background)
   - Writes result/error to the row, sets `status='completed'` or `status='failed'`

4. New endpoint: `GET /objectives/{id}/result`
   - Returns the queue row (status, result, error, ETA if still executing)
   - Voice interface polls this until status changes from `executing` to `completed`

**Files:**
- `apps/api_gateway/objective_queue.py` (ORM model + CRUD)
- `apps/api_gateway/queue_worker.py` (background loop)
- `apps/api_gateway/dashboard_api.py` (update POST /chat, add GET /objectives/{id}/result)
- `apps/api_gateway/main.py` (start worker on gateway startup)
- Tests: `Tests/integration/test_api_gateway_async.py` (new)

**Effort:** ~20 hours (queue schema, worker loop, endpoint, tests)

---

### 4.3 Dashboard/Voice Interface State Observation

**Current:**
- `/activity` returns `{agents, departments, decisions, escalations, proposals, metrics}`
- Agent status is derived (decisions in last 120s → "working", else "idle")
- No visibility into queued or in-flight objectives

**Changes:**
1. `/activity` now includes `in_flight_objectives`:
   ```json
   {
     "in_flight_objectives": [
       {
         "id": "OBJ-abc123",
         "status": "executing",
         "submitted_by": "voice_director",
         "submitted_at": "2026-07-18T22:45:00Z",
         "current_stage": "workflow_engine.execute_workflow",
         "target_departments": ["research", "engineering"]
       }
     ]
   }
   ```

2. Agent status becomes **three states** instead of two:
   - `idle` — no decisions in last 120s
   - `working` — decision in last 120s, objective not yet completed
   - `waiting` — decision in last 120s, waiting for user input (e.g., during chat turn)

3. The web dashboard updates to show in-flight objectives as a separate lane in the timeline

**Files:**
- `apps/api_gateway/dashboard_api.py` (update /activity)
- `apps/web_interface/src/components/BuildingView.jsx` (optional: show in-flight banner)
- Tests: `Tests/integration/test_api_gateway_dashboard.py` (update to verify in_flight_objectives)

**Effort:** ~12 hours (schema + endpoint + dashboard updates + tests)

---

### 4.4 Agent Execution: From Stubs to Real Sessions

**Current:**
- `AgentRuntime.execute(task)` calls `ModelGateway.invoke(task)` (stub, 1ms)
- Returns `{output: "stub analysis of the task"}`

**Changes:**
1. `AnthropicModelProvider.invoke()` makes a real Claude API call
   - Uses a system prompt tuned to the agent's role (Agent prompt in `agents/active/{id}/agent.yaml`)
   - Passes the task + context (prior decisions, conversation history from memory)
   - Handles structured outputs (model's `response_format` if needed)
   - Times out gracefully (10 minutes per agent, then fail the objective)

2. No changes to `AgentRuntime` interface; existing tests mock at the provider level

3. Production gateway bootstraps `AnthropicModelProvider` with `ANTHROPIC_API_KEY` env var

**Files:**
- `shared/providers/anthropic_provider.py` (real implementation)
- `apps/api_gateway/main.py` (initialize with env var)
- Tests: mock at provider level (no real API calls in CI)

**Effort:** ~16 hours (provider + error handling + structured output + tests)

---

### 4.5 Voice-First Interface Integration

**Current:** None. The web dashboard is the only interface.

**Changes:**
1. Voice container (separate from The Company) runs as an Agent SDK session
   - Maintains conversation context across turns (Claude sessions are stateful)
   - Submits objectives to The Company's `POST /chat` endpoint
   - Polls `/objectives/{id}/result` and `/activity` for state
   - Acts as identity `voice_director` (HUMAN type, holds all Director permissions)

2. The Company's gateway adds a `submitted_by` field to every objective (from the API key's identity)
   - Voice interface identifies as `voice_director`
   - Dashboard can be downgraded to read-only (optional)

3. Voice interface handles async naturally:
   - User: "Research blockchain app ideas."
   - Voice (to Company): POST /chat → gets back OBJ-123, queued
   - Voice (to user): "I've sent that to Research. Let me check on its progress..."
   - Voice (to Company): polls /objectives/OBJ-123/result every 2s
   - 15 seconds later: result comes back
   - Voice (to user): "Research found three ideas: [...]"

**Files:**
- `C:\My AI\voice_core\swarm_client.py` (HTTP client to The Company gateway)
- `C:\My AI\voice_core\director_agent.py` (Claude session that orchestrates voice ↔ swarm)
- Env: `SWARM_GATEWAY_URL`, `SWARM_API_KEY` (points to The Company)

**Effort:** ~24 hours (new repository; no changes to The Company itself)

---

## 5. Execution Sequence

### Phase A: Foundation (Week 1) — ✅ done, commit `a271c64`
1. **ModelGateway providers** (14h, revised - see Section 4.1)
   - AnthropicModelProvider scaffold + tests — done
   - AgentSDKModelProvider scaffold + tests (subscription-capable) — done
   - Env var bootstrap in gateway (`MODEL_PROVIDER`) — done
   - Smoke test: call Claude API from within gateway container — implemented as a gated/skipped test (needs real credentials + an explicit opt-in env var to actually run; not run live as part of this rollout)

2. **ObjectiveQueue schema & CRUD** (10h)
   - Database table + ORM model — done
   - Queue worker skeleton (doesn't execute yet, just transitions state) — done, via an injectable handler (Phase A shipped no dependency on COOOrchestrator)
   - Integration tests — done

3. **Status: stubs still work, but infrastructure is in place** — confirmed: full pre-existing test suite passed unchanged throughout

### Phase B: Async Execution (Week 2) — ✅ done, commit `ce6b41f`
4. **Queue worker core loop** (8h)
   - Poll queued objectives — done (`run_forever()`, ~100ms interval, runs as its own OS process per this section's original intent — see `Scripts/run_queue_worker.py`, not an in-process thread)
   - Call `receive_objective()` in background — done (`dashboard_api.build_queue_handler()`)
   - Handle failures, write results — done

5. **Gateway endpoint refactor** (12h)
   - `POST /chat` → fire-and-forget + queue insert — done (`POST /chat/sync` added alongside, preserving the old blocking behavior per Section 6)
   - `GET /objectives/{id}/result` → polls for completion — done
   - `/activity` → includes in_flight_objectives — done
   - Update dashboard to poll result endpoint — done (`CooChat.jsx` polls, verified end-to-end in-browser with the gateway and queue worker running as separate processes)

6. **Status: async execution works; voice interface can submit + poll** — the dashboard chat submits + polls; no voice interface exists yet (Phase D). Not implemented: the plan's three-state agent status (idle/working/**waiting**) - no real signal in this codebase's execution model to derive "waiting" from; documented as a conscious scope decision in `dashboard_api.py` rather than guessed at.

### Phase C: Real Agents (Week 3)
7. **AnthropicModelProvider full implementation** (12h)
   - Structured outputs, error handling, timeouts
   - Integration tests with real API (in optional, gated test suite)

8. **Agent execution via provider** (4h)
   - Flip gateway to use AnthropicModelProvider (or keep env var configurable for testing)

9. **Status: Company swarm now reasons with real Claude**

### Phase D: Voice Interface (Week 4)
10. **Voice Director scaffold** (24h)
    - Separate Agent SDK container (your `C:\My AI` repo)
    - HTTP client to Company gateway
    - Director identity (HUMAN, full permissions)
    - Claude session that orchestrates voice input → Company objective → polling result
    - Streaming voice response back to user

11. **Integration testing** (8h)
    - End-to-end: voice query → swarm reasoning → voice response
    - Escalations, approvals, memory all flow through the Director

12. **Status: voice-first Director interface is live; Company is its backend**

---

## 6. Testing Strategy

### Unit Tests (no changes needed)
- Existing agent tests mock at `ModelGateway` level; still work with both providers
- Existing orchestrator tests mock the entire gateway; unchanged

### Integration Tests (new)
- `test_async_objective_queue.py`: queue lifecycle (queued → executing → completed)
- `test_anthropic_provider.py`: real Claude calls (optional, gated to CI with API key)
- `test_api_gateway_async.py`: fire-and-forget endpoints, polling result
- `test_voice_director_integration.py`: voice container ↔ Company gateway (in voice repo)

### Backward Compatibility
- Existing `/chat` endpoint continues to exist; new behavior is fire-and-return instead of blocking
- Existing tests that check `/chat` response need updates (now returns `{objective_id}` not `{result}`)
- Suggest: keep `/chat/sync` for testing (blocks, old behavior), `/chat` for production (async, new behavior)

---

## 7. Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Claude API calls fail (rate limit, outage) | Objective stuck in `executing` | Queue worker retries up to 3x with exponential backoff; user can see error in `/objectives/{id}/result` |
| Voice interface out of sync with swarm state | User thinks work is done, it isn't | Voice polls `/activity` live; surfaces `in_flight_objectives` and agent status explicitly |
| Multiple voice clients (you + someone else) compete for Director | Conflicting objectives | Director identity is single-user (you); other users get separate identities. Governance (escalations, approvals) handles conflicts |
| Database grows unbounded (old objective rows) | Query slowdown | Archive completed objectives older than 30 days to a history table; `/activity` only touches recent rows |
| Agent execution hangs (Claude session freezes) | Objective never completes | 10-minute timeout per agent; queue worker marks as `failed` + logs error |

---

## 8. Known Unknowns (Decisions Still Needed)

1. **Objective timeout:** Should an objective timeout at 10 minutes, or per-agent (10m per agent, so multi-agent workflows can take longer)?
   - **Recommendation:** per-agent, but cap total workflow at 30 minutes. Surface estimated time in `/activity`.

2. **Failure retry:** Should a failed objective auto-retry, or require user re-submission?
   - **Recommendation:** no auto-retry in v1; user sees error and can re-submit. Add retry in v2 if needed.

3. **Voice interface location:** Should it run in the same container as The Company gateway, or separate?
   - **Recommendation:** separate (your `C:\My AI` repo). Voice is your primary UI; Company is a backend service. Easier to iterate on voice independently.

4. **Dashboard deprecation:** After voice interface is live, deprecate the web dashboard?
   - **Recommendation:** make dashboard read-only observation (nice-to-have, not critical). Voice is the operational interface; dashboard is for monitoring/understanding.

5. **Billing (resolved 2026-07-19, revised):** Both voice and swarm agents *can* run on your Pro/Max/Team/Enterprise subscription via `claude setup-token` → `CLAUDE_CODE_OAUTH_TOKEN`, as long as (a) they're invoked through the Agent SDK or `claude` CLI rather than the raw `anthropic` API client, (b) they don't run in `--bare` mode, and (c) The Company stays single-Director/personal-use — the moment it serves other users, their traffic needs to move to `ANTHROPIC_API_KEY`. Because subscription usage windows are shared and finite (sized for one interactive user, not N parallel background agents), **decide up front whether the swarm draws from the same subscription budget as your interactive Claude Code use, or gets its own subscription/token.** If subscription usage gets tight under swarm load, the fallback levers are the same as any API-billed system: cheaper models per agent tier (Haiku for low-stakes department agents), prompt caching, and tighter objective/agent timeouts — plus the option to route specific agents to `AnthropicModelProvider` (API key) instead of drawing on the subscription at all.

---

## 9. Success Criteria

- [x] Objective queue persists and survives gateway restart (SQLite file on disk, same as every other table in this dev/test setup)
- [x] `/chat` returns immediately; background worker executes objective
- [x] `/objectives/{id}/result` polls for completion and returns result when ready
- [ ] Voice interface submits an objective and polls until complete (Phase D — no voice interface exists yet)
- [ ] A research objective produces real Claude reasoning (not stub), takes 5–15 seconds (providers exist since Phase A — `AnthropicModelProvider`/`AgentSDKModelProvider` — but `MODEL_PROVIDER` still defaults to `stub`; flipping the default and validating real latency is Phase C)
- [x] Dashboard shows in-flight objectives and their progress (verified end-to-end in-browser, not just unit tests — gateway + queue worker run as separate processes, submitted an objective via the dashboard chat, confirmed the reply and in-flight-then-empty transition)
- [x] All existing tests pass (with endpoint behavior updates) — 202 passed, 2 skipped by design (gated real-API smoke tests)
- [ ] Voice Director can approve/reject Evolution proposals (Phase D)

---

## 10. Summary: What Stays the Same

- COOOrchestrator logic (Interpret → Select → Dispatch → Validate)
- Workflow engine, department routing, agent registry
- Governance (escalations, approvals, memory)
- Database schema (orchestrator/decisions, escalations, etc. — only new queue table)
- Security model (identities, permissions)

---

## 11. Deployment Model

**Current (v1, today):**
```
localhost:8000 = FastAPI gateway + web UI (React dist/)
```

**Post-SDK (v2):**
```
container:8000 = FastAPI gateway + web UI (read-only, optional)
container:AGENT_SDK_PORT = Claude Code sessions (real agent execution)
your_machine:VOICE_PORT = Voice-first interface (Agent SDK container, Director identity)
                          ↓ HTTP to container:8000
                          The Company swarm
```

The Company itself doesn't move or scale differently. It stays a single FastAPI process; the SDK migration just adds:
- Real reasoning (provider swap)
- Async job queue (new table + worker loop)
- Voice interface (separate container in your `C:\My AI` repo)

**Cost note (revised 2026-07-19):** every arrow above that reaches a Claude model draws on either API-key billing or your subscription's usage windows, depending on which provider/credential each component is wired to. With `AgentSDKModelProvider` + `CLAUDE_CODE_OAUTH_TOKEN`, both swarm agent execution and the voice container's session can run against your Pro/Max/Team/Enterprise subscription instead of per-token API cost — genuinely the workable path for a personal, single-Director system. What doesn't change is that *some* budget still gets consumed (subscription usage windows aren't unlimited), and that budget is shared with any interactive Claude Code use on the same account unless you provision a separate token/subscription for the swarm. Size that before Phase D adds a second continuously-running Claude session (voice) on top of swarm agent calls, and revisit `ANTHROPIC_API_KEY` billing only for agents/paths where you'd rather pay per-token than compete for subscription usage.

---

## 12. Timeline & Effort Breakdown

| Phase | Task | Hours | Dependencies |
|-------|------|-------|--------------|
| A | ModelGateway providers (API-key + Agent SDK/subscription) | 14 | None |
| A | ObjectiveQueue schema + CRUD | 10 | None |
| B | Queue worker core loop | 8 | Phase A |
| B | Gateway endpoint refactor | 12 | Phase A, Phase A |
| B | Dashboard update (optional) | 6 | Phase B |
| C | AnthropicModelProvider/AgentSDKModelProvider full | 12 | Phase A, Phase B |
| C | Agent execution via provider | 4 | Phase C |
| D | Voice Director scaffold (separate repo) | 24 | Phase C |
| D | Integration testing (voice ↔ swarm) | 8 | Phase D |
| **Total** | | **98** | |

**Concurrent phases:** A and B can overlap (8h); C can start once B is done. Total calendar time: ~3 weeks at 40h/week.


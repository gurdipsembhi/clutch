# 🐍 Backend Walkthrough — FastAPI, Store, Routers

This walks the backend module by module. We go from the entry point inward, then look
at the data store (the most important file), then each API endpoint.

> The AI agent itself gets its own doc: [03-agent-deep-dive.md](03-agent-deep-dive.md).

---

## 1. Entry point — `app/main.py`

This is where the server is born. It's tiny on purpose.

```python
app = FastAPI(title=..., version=..., debug=...)          # create the app
app.add_middleware(CORSMiddleware, allow_origins=["*"])   # let the browser call us
app.include_router(health.router, prefix="/api")          # mount the 3 routers
app.include_router(tasks.router,  prefix="/api")
app.include_router(agent.router,  prefix="/api")
```

What to understand:

- **`include_router(..., prefix="/api")`** — every endpoint lives under `/api`. A
  router that declares `prefix="/tasks"` (in `tasks.py`) therefore answers at
  `/api/tasks`. Prefixes stack.
- **CORS middleware** — the frontend runs on a different origin (e.g.
  `localhost:3000`) than the backend (`localhost:8000`). Browsers block
  cross-origin calls unless the server explicitly allows them. `allow_origins=["*"]`
  permits any origin (fine for a demo; you'd lock this down in production). The list
  comes from `settings.ALLOWED_ORIGINS` (`core/config.py:8`).
- The `@app.get("/")` root is just a friendly "is this thing on?" message.

You run this file with: `uvicorn app.main:app --reload` (README line 78).
`app.main:app` means "the `app` object inside the `app/main.py` module."

---

## 2. Configuration — `app/core/config.py`

All tunable settings live in one typed class using **pydantic-settings**:

```python
class Settings(BaseSettings):
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GOOGLE_CLOUD_PROJECT: str = ""
    GOOGLE_CLOUD_LOCATION: str = "us-central1"
    TIMEZONE: str = "Asia/Kolkata"
    class Config:
        env_file = ".env"      # values can be overridden by backend/.env
```

Why this pattern is good:

- **One place** for every config value. No magic strings scattered around.
- **Type-checked.** `DEBUG: bool` will reject a non-boolean.
- **Env override.** Anything here can be set in `backend/.env` (the file you have
  open) or as a real environment variable. `extra = "ignore"` means unknown keys in
  `.env` won't crash startup.

Note the commented-out lines (`config.py:9-10`): the project **migrated** from the
old API-key-based Gemini Developer API to **Vertex AI**, which authenticates with a
GCP project instead of an API key. That history matters — see `llm.py` in
[03](03-agent-deep-dive.md). (Your saved note about a "blocked Gemini key" refers to
the old approach; the code now uses Vertex AI credentials.)

---

## 3. The Store — `app/store.py` (read this twice)

This is the **single source of truth**. Everything else just reads/writes it. There
is no database — state lives in three module-level dictionaries:

```python
_tasks:  dict[str, dict] = {}   # task_id  -> task
_blocks: dict[str, dict] = {}   # block_id -> schedule block
_drafts: dict[str, dict] = {}   # draft_id -> drafted message
_lock = RLock()                 # guards all mutations (thread safety)
```

### Why a lock?

FastAPI can handle requests concurrently. If two requests mutate `_tasks` at the same
time you could corrupt it. `with _lock:` wraps every read/write so only one runs at a
time. `RLock` (reentrant) lets the same thread acquire it more than once without
deadlocking.

### The core data shape: a task (`store.py:85`)

```python
task = {
    "id": tid, "title": ..., "notes": ...,
    "deadline": deadline,              # ISO string or None
    "estimated_minutes": ...,          # effort estimate
    "importance": "medium",            # low|medium|high|critical
    "category": "general",
    "status": "todo",
    "subtasks": [],                    # filled in by the agent's break_down_task tool
    "priority_score": None,            # filled in by the agent's triage step
    "priority_reason": None,
    "risk": None,                      # "will slip" flag from triage
    "created_at": now_iso(),
}
```

Notice the fields that start `None`: `priority_score`, `priority_reason`, `risk`, and
empty `subtasks`. **The AI agent fills these in later.** A freshly created task is
"raw"; after a rescue plan runs, it's "enriched." This single shape is the contract
between the data layer, the agent, and the UI (`frontend/lib/types.ts:9` mirrors it).

### The time helpers (the trickiest part of this file)

Deadlines are the whole point of the app, so time handling matters:

| Function | Line | What it does |
|---|---|---|
| `now()` | `store.py:25` | current time in the configured timezone (`Asia/Kolkata`) |
| `parse_dt(value)` | `store.py:38` | parse an ISO string; assume local tz if none given; return `None` if invalid |
| `hours_until(deadline)` | `store.py:51` | hours from now until a deadline — **negative if overdue** |
| `gcal_link(...)` | `store.py:59` | builds a "Add to Google Calendar" URL (no OAuth needed) |

`hours_until` is what powers every countdown ("6h left", "OVERDUE by 2h") in both the
triage prompt and the UI. The Google Calendar link (`gcal_link`) is clever: it just
formats a template URL — no Google login required — so every scheduled block gets a
one-click "add to calendar" button for free.

### CRUD + enrichment functions

- **Create/read/update/delete tasks:** `add_task`, `list_tasks`, `get_task`,
  `update_task`, `delete_task`.
- **Enrichment (used by the agent):** `set_priority` (triage writes score/reason/risk),
  `add_subtasks` (the break-down tool).
- **Schedule & drafts:** `add_block`/`list_blocks`, `add_draft`/`list_drafts`.
- **`snapshot()`** (`store.py:201`) — bundles tasks + schedule + drafts + `now` into
  one object. This is exactly what the UI fetches to render the whole app.

`list_tasks()` sorts by `priority_score` descending (`store.py:107`), so after triage
the most urgent task is naturally first.

### Seeding — `_seed()` (`store.py:219`) and `reset()`

On import (`store.py:276`) the store fills itself with **6 realistic demo tasks**
(assignment due tomorrow, PM interview, electricity bill, mom's gift, dentist, PR
review). The clever bit: deadlines are anchored *relative to `now()`* via the `at()`
helper, so the countdowns are always "live" no matter when you run the demo.
`reset()` clears everything and re-seeds — that's the "↺ Reset demo" button.

> ⚠️ **Important limitation:** because state is in-memory and process-local, it resets
> on every restart and is **not shared across multiple server instances.** The
> docstring even says: "Swap the dict-backed functions for Firestore to make it
> durable." Good to know if you ever deploy more than one instance.

---

## 4. The Routers (the API surface)

Routers are thin: validate input → call store/agent → shape the JSON. Three of them.

### `routers/health.py` — liveness

One endpoint: `GET /api/health` → `{"status": "ok"}`. Used by Cloud Run / load
balancers to check the service is alive. Nothing more.

### `routers/tasks.py` — task management + brain dump

This is the REST CRUD layer. Note the **Pydantic models** at the top (`TaskCreate`,
`TaskUpdate`, `BrainDump`) — these validate and document the request bodies
automatically.

| Method & path | Function | What it does |
|---|---|---|
| `GET /api/tasks` | `get_tasks` | list all tasks (+ `hours_until` added) |
| `GET /api/tasks/snapshot` | `get_snapshot` | the whole app state (tasks+schedule+drafts) |
| `POST /api/tasks` | `create_task` | add one task manually |
| `POST /api/tasks/extract` | `extract` | **brain dump** → Gemini → many tasks |
| `PATCH /api/tasks/{id}` | `patch_task` | edit a task (404 if missing) |
| `DELETE /api/tasks/{id}` | `remove_task` | delete (204 No Content) |
| `POST /api/tasks/reset` | `reset_demo` | wipe + re-seed demo data |

The `_decorate()` helper (`tasks.py:33`) adds a computed `hours_until` to each task
before sending it out, so the frontend doesn't have to recompute "time left."

`/extract` is the only "smart" endpoint here — it delegates to `extract_tasks()` in
the agent package (covered in [03](03-agent-deep-dive.md)).

### `routers/agent.py` — the streaming agent endpoint

Just one endpoint, but it's special because it **streams**:

```python
@router.post("/plan")
async def plan(body: PlanRequest):
    return StreamingResponse(
        _event_stream(body.instruction, body.horizon_hours),
        media_type="text/event-stream",   # ← this makes it SSE
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

How it works:

- `run_plan(...)` (in `agent/graph.py`) is an **async generator** — it `yield`s a dict
  every time the agent makes progress.
- `_event_stream` (`agent.py:17`) wraps each yielded dict as a Server-Sent Event line:
  `data: {json}\n\n`. The blank line is the SSE record separator.
- It ends the stream with `data: [DONE]\n\n` so the client knows it's over.
- `media_type="text/event-stream"` + `X-Accel-Buffering: no` tell browsers and
  proxies "don't buffer this; deliver chunks as they arrive."
- The `try/except` ensures any crash becomes a clean `{"type": "error"}` event instead
  of a broken connection.

This is the backend side of the live "watch the agent work" experience. The frontend
side that reads this stream is in [04-frontend-walkthrough.md](04-frontend-walkthrough.md).

---

## Mental checkpoint

You should now be able to answer:

- *Where does task data live?* → `store.py`, in three in-memory dicts.
- *What's the difference between `/api/tasks` and `/api/agent/plan`?* → the first is a
  normal request/response; the second streams the agent's progress as SSE.
- *How does the agent's work show up in the UI?* → the agent's tools mutate the same
  store, then the final `snapshot()` (or a follow-up `/snapshot` fetch) reflects it.

Now go to [03-agent-deep-dive.md](03-agent-deep-dive.md) for the part that makes this
project actually intelligent.

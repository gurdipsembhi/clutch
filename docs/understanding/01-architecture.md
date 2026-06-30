# 🏛️ Architecture Analysis — The Big Picture

This is the high-level mental model. If you only read one doc, read this.

## The two halves

Clutch is split into two independent applications that talk over HTTP:

```
┌─────────────────────────┐         HTTP / JSON          ┌──────────────────────────┐
│        FRONTEND         │  ──── POST /api/... ───────► │        BACKEND           │
│  Next.js + React + TS   │                              │     FastAPI (Python)     │
│  (frontend/)            │  ◄─── SSE stream / JSON ──── │     (backend/)           │
└─────────────────────────┘                              └──────────────────────────┘
        the UI                                              the brain + data
```

- **Frontend** (`frontend/`) — what the user sees and clicks. Knows nothing about
  Gemini or scheduling logic. It just calls the backend and renders the results.
- **Backend** (`backend/`) — all the intelligence: the AI agent, the task data, the
  scheduling, the message drafting. Exposes a REST + streaming API.

This separation is deliberate: you could swap the React UI for a mobile app and the
backend wouldn't change at all.

## The layers inside the backend

The backend is organized in classic layers, from outside (HTTP) to inside (logic):

```
        HTTP request
             │
             ▼
   ┌──────────────────────┐
   │  Routers (the API)   │   backend/app/routers/*.py
   │  health · tasks ·    │   ← validate input, call logic, shape the response
   │  agent               │
   └──────────┬───────────┘
              │
      ┌───────┴────────┐
      ▼                ▼
┌───────────┐   ┌──────────────────────┐
│  Store    │   │   Agent (the AI)     │   backend/app/agent/*.py
│ (data)    │◄──│  graph · tools ·     │   ← triage→act→review loop
│ store.py  │   │  extract · llm       │
└───────────┘   └──────────┬───────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │  Gemini (Vertex) │   external Google AI
                  └──────────────────┘
```

Key idea: **the Store is the single source of truth.** Both the REST endpoints and
the AI agent's tools read and write the same in-memory store
(`backend/app/store.py`). So when the agent schedules a time block, it appears in the
store, and the next snapshot the UI fetches shows it. No separate database to keep in
sync.

## The request paths (there are really only two interesting ones)

### Path A — "Brain dump → tasks" (a normal request/response)

```
User types text → POST /api/tasks/extract → Gemini structures it
              → tasks saved in store → JSON list returned → UI re-renders
```

### Path B — "Generate rescue plan" (a streaming agent run)

```
User clicks button → POST /api/agent/plan → LangGraph agent starts
   triage  → scores tasks, flags risks      ─┐
   act     → calls tools (schedule, break,   ├─ each step streamed back live
              draft, search)                  │   as Server-Sent Events (SSE)
   review  → checks coverage, loops or ends  ─┘
              → final summary + full snapshot streamed → UI shows schedule & drafts
```

Path B is what makes Clutch "agentic": the AI *takes actions* (via tools), not just
returns text. See [03-agent-deep-dive.md](03-agent-deep-dive.md).

## Folder → responsibility map

```
backend/
  app/
    main.py            ← entry point: creates the FastAPI app, wires CORS + routers
    core/config.py     ← settings (model name, GCP project, timezone) from .env
    store.py           ← THE DATA: tasks, schedule blocks, drafts (in-memory)
    routers/
      health.py        ← GET /api/health  (is the server alive?)
      tasks.py         ← task CRUD + /extract (brain dump) + /snapshot + /reset
      agent.py         ← POST /api/agent/plan  (the streaming agent endpoint)
    agent/
      graph.py         ← the LangGraph triage→act→review loop (the orchestrator)
      tools.py         ← the actions the agent can take (schedule, break down, draft…)
      extract.py       ← brain-dump text → structured tasks (uses Gemini)
      state.py         ← PlanState: the data passed between graph nodes
      llm.py           ← creates the Gemini client (via Vertex AI)

frontend/
  app/
    page.tsx           ← entry point: the whole single-page app layout
    layout.tsx         ← HTML shell / metadata
    globals.css        ← all styling
  components/
    BrainDump.tsx      ← the textarea that extracts tasks
    TaskCard.tsx       ← renders one task (countdown, risk, subtasks)
    RescuePlan.tsx     ← the agent panel: runs the plan, shows live activity/schedule/drafts
  lib/
    api.ts             ← all backend calls + the SSE stream reader
    types.ts           ← TypeScript shapes mirroring the backend's JSON
    format.ts          ← display helpers (countdown text, time ranges, CSS classes)
```

## The tech stack at a glance

| Concern | Technology | Where |
|---|---|---|
| Web API framework | **FastAPI** | `backend/app/main.py` |
| AI orchestration | **LangGraph** (`langgraph`) | `backend/app/agent/graph.py` |
| LLM client | **LangChain + Vertex AI** (`langchain-google-vertexai`) | `backend/app/agent/llm.py` |
| The model | **Gemini 2.5 Flash** | `backend/app/core/config.py:11` |
| Web search tool | **DuckDuckGo** (`duckduckgo_search`) | `backend/app/agent/tools.py:74` |
| Config / settings | **pydantic-settings** | `backend/app/core/config.py` |
| Frontend framework | **Next.js 15** (App Router) + **React 19** | `frontend/` |
| Language (frontend) | **TypeScript** | `frontend/` |
| Live updates | **Server-Sent Events (SSE)** | `agent.py` ↔ `lib/api.ts` |
| Deployment | **Google Cloud Run** (both services) | `DEPLOY.md`, `*/Dockerfile` |

## Three things that will make everything else click

1. **The store is shared.** REST endpoints and AI tools mutate the same dicts in
   `store.py`. That's why the agent's actions instantly show up in the UI.
2. **The agent is a graph, not a script.** `triage → act → review`, and `review` can
   loop back to `act` up to `MAX_ITERATIONS` times. It's a small state machine.
3. **Streaming is the UX.** The agent could take 10–20 seconds. Instead of one slow
   response, it streams each step (triage results, each action, the final summary) so
   the user watches it work.

Next: see these ideas in motion in [05-end-to-end-flow.md](05-end-to-end-flow.md), or
go deep on each half in [02](02-backend-walkthrough.md), [03](03-agent-deep-dive.md),
and [04](04-frontend-walkthrough.md).

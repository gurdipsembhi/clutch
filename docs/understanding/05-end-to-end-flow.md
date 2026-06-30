# 🔄 End-to-End Flow — Tracing Requests Through the System

The fastest way to *truly* understand a codebase is to follow one piece of data on its
full journey. Here we trace the **two** core user actions, step by step, naming the
exact file and function at each hop. Read with the other docs open.

---

## Flow 1: "Brain dump → tasks" (a simple request/response)

**User action:** types tasks into the textarea and clicks **"Extract tasks →"**.

```
┌─ BROWSER ──────────────────────────────────────────────────────────────┐
│ 1. BrainDump.tsx:19  handleExtract()                                     │
│      └─ api.extract(text)                          [lib/api.ts:21]       │
│           └─ POST /api/tasks/extract  body:{text}  [lib/api.ts:5]        │
└───────────────────────────────────────────────│───────────────────────┘
                                                 ▼  HTTP
┌─ BACKEND ──────────────────────────────────────────────────────────────┐
│ 2. routers/tasks.py:54  extract()                                        │
│      └─ extract_tasks(text)                        [agent/extract.py:24] │
│           ├─ get_llm(temperature=0)                [agent/llm.py:22]     │
│           ├─ llm.invoke([system, human+now+text]) ──► Gemini (Vertex AI) │
│           │      └─ returns a JSON array of tasks                        │
│           ├─ strip code fences, json.loads(...)                          │
│           └─ for each item: store.add_task(...)    [store.py:75]         │
│ 3. response: { created:[...tasks...], count:N }   (each + hours_until)   │
└───────────────────────────────────────────────│───────────────────────┘
                                                 ▼  JSON
┌─ BROWSER ──────────────────────────────────────────────────────────────┐
│ 4. BrainDump shows "✓ Added N tasks", calls onAdded()                    │
│      └─ page.tsx refresh() → api.snapshot() → GET /api/tasks/snapshot    │
│           └─ setSnap(...) re-renders the task list with new TaskCards    │
└─────────────────────────────────────────────────────────────────────────┘
```

**What to take away:** the only "smart" hop is step 2, where free text becomes
structured JSON via one Gemini call. Everything else is plumbing. Notice the
**round-trip pattern**: the browser doesn't trust its local copy — after a mutation it
re-fetches the snapshot to stay in sync with the server's source of truth.

---

## Flow 2: "Generate rescue plan" (the streaming agent — the important one)

**User action:** (optionally types an instruction, picks a time horizon) and clicks
**"⚡ Generate rescue plan"**.

### Phase 0 — kickoff

```
BROWSER
  RescuePlan.tsx:29  run()
    └─ streamPlan({instruction, horizon_hours}, onEvent)   [lib/api.ts:37]
         └─ POST /api/agent/plan   (opens a streaming connection)
                                                   │
                                                   ▼  HTTP (stays open)
BACKEND
  routers/agent.py:26  plan()
    └─ StreamingResponse(_event_stream(...), media_type="text/event-stream")
         └─ run_plan(instruction, horizon_hours)           [agent/graph.py:191]
              └─ graph.astream(initial_state)   ← runs the LangGraph
```

The connection stays open. Everything below streams back over it incrementally.

### Phase 1 — `triage` node (`graph.py:69`)

```
_triage(state)
  ├─ store.list_tasks()                          gather all tasks
  ├─ build a catalog line per task (time-left, importance, effort)
  ├─ get_llm().invoke([_TRIAGE_SYSTEM, tasks])   ──► Gemini scores them
  │      └─ returns JSON: [{task_id, priority_score, reason, risk}, ...]
  ├─ store.set_priority(...) for each            ENRICH the store
  └─ state.priorities = sorted ranking
                                                   │
run_plan yields ──► {"type":"triage", "data":[priorities]}
                                                   │  SSE: data: {...}
                                                   ▼
BROWSER  onEvent → setPriorities(...)  → ActivityFeed shows the ranking + ⚠️ risks
```

At this moment the task cards on the left also gain score badges and risk banners
(once the page snapshot refreshes at the end — see Phase 4).

### Phase 2 — `act` node (`graph.py:112`) — the agent takes action

```
_act(state)
  llm = get_llm().bind_tools(ALL_TOOLS)           give Gemini the 6 tools
  messages = [_ACT_SYSTEM, prioritized tasks + time window]

  loop (up to 10 rounds):
    response = llm.invoke(messages)               ──► Gemini decides
    if no tool_calls: break                        (model says "done acting")
    for each tool_call:
       run the tool  e.g. create_time_block(...)  [tools.py] → store.add_block(...)
       append result to state.actions
       feed result back to the model as a "tool" message
                                                   │
run_plan yields one event per NEW action ──► {"type":"action","data":"Scheduled '...'"}
                                                   │  SSE (multiple)
                                                   ▼
BROWSER  onEvent → setActions(prev=>[...])  → each action appears live in the feed
```

This is the agentic core: Gemini autonomously chooses to call `create_time_block`,
`break_down_task`, `draft_message`, etc.; each call mutates the **same store** the UI
reads; each result streams to the browser as it happens. (Deep dive:
[03-agent-deep-dive.md](03-agent-deep-dive.md) §5.)

### Phase 3 — `review` node (`graph.py:145`) — check & decide

```
_review(state)
  snap = store.snapshot()                          current schedule + drafts
  get_llm().invoke([_REVIEW_SYSTEM, snap])         ──► Gemini judges coverage
       └─ returns {"verdict":"done"|"continue", "summary":"..."}

  _should_continue(state)                          [graph.py:171]
     ├─ verdict "done"  OR  iteration_count ≥ 4 (MAX_ITERATIONS) → END
     └─ otherwise                                   → loop back to `act`
```

So the agent can go around `act → review → act` again if the review says critical work
isn't covered yet — bounded by `MAX_ITERATIONS = 4`.

### Phase 4 — finish

```
run_plan (on final review, status=="done") yields:
   {"type":"done", "data":"<plain-English summary>", "snapshot": <full state>}
_event_stream then sends:  data: [DONE]
                                                   │  SSE
                                                   ▼
BROWSER  onEvent (type "done"):
   ├─ setSummary(...)            show the rescue summary
   ├─ onComplete(event.snapshot) → page.tsx setSnap(...)   ← whole UI refreshes:
   │      task cards now show scores/risks/subtasks; Schedule & Drafts tabs fill in
   └─ setTab("schedule")        auto-switch to the schedule
streamPlan sees "[DONE]" → returns → run() finally{ setRunning(false) }
```

Done. The user watched the agent prioritize, schedule, break down, and draft — live —
and now has a schedule with one-click Google Calendar links and ready-to-send drafts.

---

## The one diagram to remember

```
              ┌──────────── the shared STORE (store.py) ────────────┐
              │     _tasks        _blocks        _drafts            │
              └───▲────────────────▲────────────────▲──────────────┘
                  │ read/write      │ write           │ write
        ┌─────────┴──────┐   ┌──────┴───────┐  ┌──────┴────────┐
        │ REST routers   │   │ agent tools  │  │ triage sets   │
        │ (tasks.py)     │   │ (tools.py)   │  │ priorities    │
        └─────────▲──────┘   └──────▲───────┘  └──────▲────────┘
                  │                 │ called by        │ part of
                  │                 └── act node ──────┘  the graph (graph.py)
                  │ HTTP/JSON & SSE
        ┌─────────┴───────────────────────────────────────────────┐
        │                    FRONTEND (Next.js)                    │
        │  page.tsx ──props──► BrainDump / TaskCard / RescuePlan   │
        │  lib/api.ts  (fetch + SSE reader)                        │
        └─────────────────────────────────────────────────────────┘
```

Everything funnels through the store. The REST API and the AI agent are just two
different ways of reading and writing it; the frontend is a live view of it.

---

## Try it yourself (active learning)

Reading is good; poking is better. With both servers running (see the README):

1. Open the FastAPI auto-docs at **http://localhost:8000/docs**. Every endpoint is
   listed and runnable from the browser — hit `GET /api/tasks/snapshot` and read the
   JSON. That JSON shape *is* `types.ts`.
2. Call `POST /api/tasks/extract` with a sentence and watch tasks appear.
3. In the UI, click **Generate rescue plan** with the browser DevTools **Network** tab
   open; find the `plan` request and watch the SSE `data:` lines arrive one by one —
   those are exactly the events from `run_plan`.
4. Set a breakpoint (or add a `print`) inside `_act` (`graph.py:112`) and watch which
   tools Gemini chooses for the seeded demo tasks.

Once you've traced these two flows by hand, you understand Clutch. Keep
[06-glossary.md](06-glossary.md) handy for any unfamiliar term.

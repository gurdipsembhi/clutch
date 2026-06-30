# 🤖 Agent Deep Dive — The LangGraph Brain

This is the heart of Clutch and the reason it's "agentic" rather than "a to-do list
with reminders." Everything here lives in `backend/app/agent/`.

```
agent/
  llm.py       ← creates the Gemini client (the raw intelligence)
  extract.py   ← brain dump text → structured tasks (one LLM call)
  state.py     ← PlanState: the data carried between graph steps
  tools.py     ← the actions the agent can take in the world
  graph.py     ← the orchestrator: triage → act → review loop
```

---

## What does "agentic" mean here?

A plain chatbot returns *text*. An **agent** can **take actions** to achieve a goal,
decide *which* actions and *when*, observe the results, and keep going until done.

Clutch's agent does exactly that: given your tasks, it autonomously decides to
schedule time blocks, break tasks down, draft messages, or search the web — using
**tools** — and loops until a review step says every critical task is covered.

The three ingredients of any agent, and where they are here:

| Ingredient | In Clutch | File |
|---|---|---|
| **An LLM** to reason and decide | Gemini 2.5 Flash | `llm.py` |
| **Tools** it can call to act | schedule / break-down / draft / search | `tools.py` |
| **A control loop** that runs it | LangGraph `triage→act→review` | `graph.py` |

---

## 1. The LLM client — `llm.py`

```python
@lru_cache(maxsize=2)
def get_llm(temperature: float = 0.2) -> ChatVertexAI:
    return ChatVertexAI(
        model=settings.GEMINI_MODEL,         # "gemini-2.5-flash"
        project=settings.GOOGLE_CLOUD_PROJECT,
        location=settings.GOOGLE_CLOUD_LOCATION,
        temperature=temperature,
    )
```

Things to understand:

- **`ChatVertexAI`** — Gemini accessed through Google **Vertex AI**. Crucially, this
  does **not** use an API key. It uses *Application Default Credentials* (ADC):
  locally you run `gcloud auth application-default login`; on Cloud Run it uses the
  service account automatically. (The commented block above shows the *old*
  API-key-based `ChatGoogleGenerativeAI` approach the project moved away from.)
- **`@lru_cache(maxsize=2)`** — the client is expensive to build, so it's cached.
  `maxsize=2` because the code uses two temperatures: `0.2` (default, for the agent)
  and `0` (for deterministic extraction). Each distinct `temperature` argument gets
  its own cached client.
- **`temperature`** — randomness. `0` = deterministic/repeatable (good for parsing
  text into JSON). `0.2` = slightly creative but still focused (good for planning).

This single `get_llm()` function is the *only* place the rest of the code touches the
model. If you wanted to swap models or providers, you'd change just this file.

---

## 2. Brain-dump extraction — `extract.py`

This powers the `POST /api/tasks/extract` endpoint. It's the simplest LLM usage in the
project: **one call in, structured data out.** A good warm-up before the full agent.

The flow (`extract_tasks`, `extract.py:24`):

1. Get a **temperature-0** LLM (deterministic — we want reliable parsing).
2. Send two messages:
   - a **system prompt** (`extract.py:9`) instructing: extract tasks, resolve relative
     dates ("tomorrow", "Friday") into absolute ISO datetimes, and return **only a
     JSON array** with fields `title, deadline, estimated_minutes, importance,
     category, notes`.
   - a **human message** containing the current datetime + the user's raw text.
3. **Strip code fences** if Gemini wrapped the JSON in ```` ```json ```` (`extract.py:31`).
4. `json.loads(...)` the result; on any failure, return `[]` (fail safe, never crash).
5. For each parsed item, call `store.add_task(...)` and collect the created tasks.

Two patterns here that repeat throughout the agent:

- **"Respond with ONLY JSON"** prompting + manual parsing. The model is coaxed into
  returning machine-readable output, then the code defensively parses it.
- **Giving the model the current time.** LLMs don't know "now," so the code always
  passes `store.now_iso()` so it can resolve "tomorrow" correctly.

---

## 3. The state object — `state.py`

LangGraph passes a single state dict from one node to the next. Here it's a typed
`PlanState` (`state.py:6`):

```python
class PlanState(TypedDict):
    instruction: str        # optional user directive ("I only have tonight")
    now: str                # current datetime (ISO)
    horizon_hours: int      # how far ahead to schedule (12/24/48/96)
    tasks: list[dict]       # snapshot of tasks at run start
    priorities: list[dict]  # ranked tasks (filled by triage)
    actions: list[str]      # log of every tool action taken (filled by act)
    summary: str            # final human-readable summary (filled by review)
    status: "running"|"done"|"error"
    iteration_count: int    # how many act→review loops we've done
```

Think of `PlanState` as the **shared notebook** the three nodes write into as the plan
develops. `triage` fills `priorities`; `act` appends to `actions`; `review` writes
`summary` and flips `status` to `"done"`.

---

## 4. The tools — `tools.py`

These are the agent's "hands." Each is a normal Python function decorated with
`@tool` (from LangChain). The `@tool` decorator turns the function — **including its
docstring and type hints** — into a schema the LLM can see and call. **The docstring
is not a comment; it's the instruction manual the model reads to decide when and how
to use the tool.** That's why each one is written so descriptively.

| Tool | Line | What it does | Writes to store? |
|---|---|---|---|
| `get_current_datetime()` | `tools.py:12` | returns ISO "now" so the model can reason about deadlines | no |
| `list_tasks()` | `tools.py:18` | returns all tasks formatted with time-left/risk | no |
| `create_time_block(task_id, title, start, end, focus)` | `tools.py:35` | schedules a focused work block | yes → `_blocks` |
| `break_down_task(task_id, subtasks)` | `tools.py:50` | adds ordered subtasks to a task | yes → task `subtasks` |
| `draft_message(task_id, kind, subject, body)` | `tools.py:59` | writes a message the user can send | yes → `_drafts` |
| `web_search(query)` | `tools.py:73` | DuckDuckGo search for unblocking info | no |

Key insight: **the action tools mutate the same `store` the UI reads.** When
`create_time_block` calls `store.add_block(...)`, that block (with its
auto-generated Google Calendar link, `store.py:166`) is instantly part of the app
state. This is why the agent's work "appears" in the UI — no extra plumbing.

All six are collected into `ALL_TOOLS` (`tools.py:86`), which the graph binds to the
model.

---

## 5. The orchestrator — `graph.py` (the main event)

This file defines the `triage → act → review` loop using LangGraph. Read it
alongside this section.

### The graph shape (`build_graph`, `graph.py:179`)

```python
g = StateGraph(PlanState)
g.add_node("triage", _triage)
g.add_node("act",    _act)
g.add_node("review", _review)
g.set_entry_point("triage")
g.add_edge("triage", "act")          # triage always → act
g.add_edge("act", "review")          # act always → review
g.add_conditional_edges("review", _should_continue, {"act": "act", "end": END})
```

Visually:

```
   START
     │
     ▼
 ┌────────┐     ┌──────┐     ┌────────┐
 │ triage │ ──► │ act  │ ──► │ review │
 └────────┘     └──────┘     └───┬────┘
                   ▲             │ _should_continue?
                   │             ├── "act"  → loop back (not done yet)
                   └─────────────┤
                                 └── "end"  → END (done, or hit MAX_ITERATIONS)
```

The loop (`act ↔ review`) is what makes it iterative. `MAX_ITERATIONS = 4`
(`graph.py:19`) caps it so it can never spin forever.

### Node 1 — `_triage` (`graph.py:69`): score & flag

1. Pull all tasks; build a human-readable **catalog** line per task with importance,
   effort, and time-left ("6h left" / "OVERDUE by 2h").
2. Ask Gemini (system prompt `_TRIAGE_SYSTEM`, `graph.py:21`) to return a JSON array
   ranking every task with `priority_score` (0–100), a one-line `reason`, and a `risk`
   flag if the deadline will likely be **missed at current pace**.
3. Parse the JSON (with a fallback: if parsing fails, give everything score 50 so the
   run still proceeds — `graph.py:94`).
4. Write each score/reason/risk back into the store via `store.set_priority(...)` and
   build the `priorities` list, sorted highest-first.

After triage, every task in the store has a `priority_score`/`risk` — which the UI
shows as the colored score badge and the ⚠️ risk banner on each card.

### Node 2 — `_act` (`graph.py:112`): take action (the agentic core)

This is where tool-calling happens. The pattern is the standard **LLM tool-use loop**:

```python
llm = get_llm().bind_tools(ALL_TOOLS)   # tell Gemini which tools exist
messages = [SystemMessage(_ACT_SYSTEM), HumanMessage(<prioritized tasks + window>)]

for _ in range(10):                      # safety cap on tool rounds
    response = llm.invoke(messages)
    messages.append(response)
    if not response.tool_calls:          # model decided it's done acting
        break
    for tc in response.tool_calls:       # run each tool the model asked for
        matched = next(t for t in ALL_TOOLS if t.name == tc["name"])
        result = matched.invoke(tc["args"])
        actions.append(str(result))
        messages.append({"role": "tool", "tool_call_id": tc["id"], "content": str(result)})
```

Read that loop carefully — it's the essence of an agent:

1. `bind_tools(ALL_TOOLS)` gives the model the tool schemas (from `tools.py` docstrings).
2. The model replies either with **text** ("I'm done") or with **tool calls**
   ("call `create_time_block` with these args").
3. If there are tool calls, the code **executes** each one and feeds the result
   **back** to the model as a `"tool"` message.
4. The model sees the results and decides what to do next — maybe more tools, maybe
   stop. This repeats up to 10 rounds.

The `_ACT_SYSTEM` prompt (`graph.py:36`) is the agent's job description: build a
realistic schedule (blocks after "now", respect fixed appointments, add breaks, cap at
~6 focused hours/day), break down tasks over 120 min, draft messages the user needs to
send, and only web-search if it would unblock something. **The intelligence is in the
prompt + the tools; the Python is just the loop that runs them.**

Every tool result is appended to `state["actions"]` — that log is what streams to the
UI as the "Activity" feed.

### Node 3 — `_review` (`graph.py:145`): check coverage, loop or finish

1. Take a fresh `store.snapshot()` (current schedule + drafts).
2. Ask Gemini (`_REVIEW_SYSTEM`, `graph.py:52`) to judge whether every critical/at-risk
   task has been addressed, returning JSON: `{"verdict": "done"|"continue", "summary":
   "...plain-English rescue summary..."}`.
3. The decision (`graph.py:166`):
   - if verdict is `"done"` **or** we've hit `MAX_ITERATIONS` → set `status="done"`
     and keep the summary.
   - otherwise → keep the summary and let the loop run `act` again.

### The router — `_should_continue` (`graph.py:171`)

The conditional edge function. Returns `"end"` if `status == "done"` or we've hit the
iteration cap, else `"act"`. This is what physically closes or continues the loop.

### Streaming it out — `run_plan` (`graph.py:191`)

This async generator is what the API endpoint (`routers/agent.py`) consumes. It runs
the graph with `graph.astream(initial)` and, **as each node finishes**, yields a typed
event:

| When | Event yielded |
|---|---|
| after `triage` | `{"type": "triage", "data": [priorities]}` |
| after each `act` | one `{"type": "action", "data": "<what the tool did>"}` per new action |
| after final `review` | `{"type": "done", "data": "<summary>", "snapshot": <full state>}` |

The `prev_actions` counter (`graph.py:205`, `214`) ensures only *newly added* actions
are streamed each loop, not the whole log again. This is the live "watch it work" feed.

---

## Putting the agent together (one sentence each)

- **llm.py** makes the Gemini client (Vertex AI, cached, configurable temperature).
- **extract.py** is a one-shot "text → tasks" call (a mini version of the pattern).
- **state.py** is the shared notebook passed between nodes.
- **tools.py** are the agent's hands; their docstrings tell the model how to use them.
- **graph.py** runs `triage → act ⇄ review`, where `act` is a tool-calling loop, and
  streams progress out via `run_plan`.

Next: see how the browser consumes all of this in
[04-frontend-walkthrough.md](04-frontend-walkthrough.md), or follow a full run start
to finish in [05-end-to-end-flow.md](05-end-to-end-flow.md).

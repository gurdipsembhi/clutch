# 📖 Glossary — Terms You'll Meet in This Codebase

Keep this open while reading the other docs. Terms are grouped by area.

## "Understanding a project" — the terms you originally asked about

| Term | Meaning |
|---|---|
| **Codebase exploration / familiarization** | Reading through code to learn how it's structured and works. |
| **Code comprehension** | The general (academic) term for understanding existing code. |
| **Architecture analysis** | Studying the high-level design: components and how they connect. |
| **Control-flow / data-flow tracing** | Following execution, or a piece of data, from start to finish through the system. The most effective technique. |
| **Onboarding** | Getting a new developer up to speed on a project. |
| **Reverse engineering** | Figuring out how something works when documentation is missing/poor. |
| **Walkthrough** | A guided, step-by-step explanation of code (what this folder is). |
| **Technical due diligence** | A formal, detailed assessment of a codebase (e.g. before an acquisition). |

## AI / agent terms

| Term | Meaning | In Clutch |
|---|---|---|
| **LLM** | Large Language Model — the AI that generates text/decisions. | Gemini 2.5 Flash |
| **Gemini** | Google's family of LLMs. | the "brain" |
| **Vertex AI** | Google Cloud's platform for running models. Auth via GCP credentials, *not* an API key. | `agent/llm.py` |
| **Agent** | An LLM that takes *actions* (via tools) toward a goal, observes results, and loops — not just chats. | the whole `agent/` package |
| **Tool / tool-calling / function-calling** | A function the LLM can ask the system to run; the result is fed back to the model. | `agent/tools.py` |
| **Prompt (system / human)** | Instructions to the model. *System* = role/rules; *Human* = the user/task input. | the `_*_SYSTEM` strings in `graph.py` |
| **Temperature** | Randomness of the model's output. 0 = deterministic, higher = more creative. | `0` for extract, `0.2` for the agent |
| **Triage** | Sorting tasks by urgency/importance to decide what matters most. | the first graph node |
| **LangChain** | A Python framework for working with LLMs, tools, and messages. | `langchain_core`, `langchain-google-vertexai` |
| **LangGraph** | LangChain's library for building agents as a **graph** of nodes with state and loops. | `agent/graph.py` |
| **Node / edge / state machine** | A graph node is a step (function); edges connect steps; the agent is a small state machine. | triage/act/review nodes |
| **Conditional edge** | An edge whose destination is decided at runtime by a function. | `_should_continue` (loop or end) |

## Backend / web terms

| Term | Meaning | In Clutch |
|---|---|---|
| **FastAPI** | A modern Python web framework for building APIs. | `app/main.py` |
| **Uvicorn** | The ASGI server that actually runs the FastAPI app. | `uvicorn app.main:app` |
| **Router** | A group of related endpoints. | `app/routers/*.py` |
| **Endpoint / route** | A single URL + HTTP method the API answers. | e.g. `POST /api/tasks` |
| **CRUD** | Create, Read, Update, Delete — the basic data operations. | `routers/tasks.py` |
| **REST** | An API style using HTTP verbs on resource URLs. | the tasks API |
| **Pydantic / pydantic-settings** | Libraries for typed data validation; the latter loads settings from env/.env. | `TaskCreate` models, `core/config.py` |
| **CORS** | Browser security rule controlling cross-origin requests; the server must opt in. | CORS middleware in `main.py` |
| **Middleware** | Code that runs around every request. | the CORS middleware |
| **In-memory store** | Data kept in RAM (here, Python dicts), not a database — lost on restart. | `app/store.py` |
| **Lock / RLock / thread safety** | A guard so concurrent requests don't corrupt shared data. | `_lock` in `store.py` |
| **Snapshot** | A bundled copy of all state (tasks+schedule+drafts) at a moment. | `store.snapshot()` |
| **Seeding** | Pre-filling the store with demo data on startup. | `_seed()` in `store.py` |
| **ADC (Application Default Credentials)** | Google's way of finding credentials automatically (local login or service account) instead of a key. | how Vertex AI authenticates |

## Streaming / frontend terms

| Term | Meaning | In Clutch |
|---|---|---|
| **SSE (Server-Sent Events)** | A one-way stream of text events from server to browser over a single HTTP connection. | `agent.py` ↔ `lib/api.ts` |
| **Streaming response** | A response sent in chunks over time instead of all at once. | `StreamingResponse` |
| **Async generator** | A function that `yield`s values over time with `async`. | `run_plan` |
| **Next.js** | A React framework (routing, build, server rendering). | `frontend/` |
| **App Router** | Next.js's routing system based on the `app/` folder. | `app/layout.tsx`, `app/page.tsx` |
| **React** | A library for building UIs from components. | all `.tsx` files |
| **Component** | A reusable, self-contained piece of UI. | `BrainDump`, `TaskCard`, `RescuePlan` |
| **Props** | Inputs passed from a parent component to a child. | `schedule`, `drafts`, `onComplete` |
| **State / `useState`** | Data a component remembers between renders. | `snap`, `running`, `actions`… |
| **`useEffect`** | Run code after render (e.g. fetch on mount). | initial `refresh()` in `page.tsx` |
| **`useCallback`** | Memoize a function so it isn't recreated each render. | `refresh` in `page.tsx` |
| **Discriminated union** | A TypeScript type that varies by a tag field (`type`). | `AgentEvent` |
| **"Data down, events up"** | React pattern: parent owns data, passes it down; children report changes via callbacks. | `page.tsx` ↔ components |
| **`TextDecoder` / `getReader()`** | Browser APIs to read a streamed response body chunk by chunk. | `streamPlan` |

## Project / domain terms

| Term | Meaning |
|---|---|
| **Clutch** | The product name — your "last-minute life saver." |
| **Brain dump** | The user's raw, unstructured text of everything on their mind. |
| **Task** | A structured to-do: title, deadline, effort, importance, etc. (core data shape). |
| **Time block** | A scheduled focus session for a task (with a Google Calendar link). |
| **Draft** | A message (reminder/email/extension request) the agent writes for the user to send. |
| **Risk flag** | Triage's warning that a task's deadline will likely be missed at current pace. |
| **Priority score** | 0–100 urgency rating assigned to each task by the triage step. |
| **Horizon** | How many hours ahead the agent is allowed to schedule (12/24/48/96). |
| **Rescue plan** | The full output of an agent run: priorities + schedule + breakdowns + drafts + summary. |

---

If a term you hit isn't here, search the codebase for it — and consider adding it to
this file. Keeping the glossary current is part of keeping the project understandable.

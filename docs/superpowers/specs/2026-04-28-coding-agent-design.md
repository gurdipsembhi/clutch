# Coding Agent — Design Spec
**Date:** 2026-04-28
**Status:** Approved

---

## Problem & Goal

Build a coding agent that accepts a plain-English feature request, then autonomously writes code, runs tests, and iterates until the feature is complete. The agent integrates into the existing Next.js + FastAPI boilerplate and streams progress back to the UI in real time.

---

## Framework Decision

**LangGraph** (over CrewAI / AutoGen)

Reasons:
- Fine-grained control over the plan→code→test→fix loop
- Native async support pairs cleanly with FastAPI SSE streaming
- LangSmith tracing for debugging
- First-class LangChain tool ecosystem (including `langchain-google-genai` for Gemini)

---

## Architecture

```
Next.js UI ──POST /api/agent/run──► FastAPI ──► LangGraph Agent
             ◄──SSE stream──                 (Planner→Coder→Reviewer)
                                                      │
                                           ┌──────────┼──────────┐
                                        read_file  run_cmd   web_search
                                        write_file list_files
                                                      │
                                                 Gemini LLM
                                           (gemini-2.0-flash via
                                            langchain-google-genai)
```

### LangGraph Graph

**Nodes:**
1. `planner` — Calls Gemini with the task; returns an ordered list of implementation steps
2. `coder` — Takes the next unfinished step; calls tools to implement it; marks step done
3. `reviewer` — Asks Gemini whether the full task is complete; loops back to `coder` or exits

**Edges:**
```
START → planner → coder → reviewer → coder (if incomplete)
                                   → END   (if complete)
```

**Max iterations:** 10 (safety limit to prevent infinite loops)

### Agent State Schema

```python
class AgentState(TypedDict):
    task: str
    plan: list[str]
    current_step: int
    files_changed: list[str]
    tool_outputs: list[str]
    final_output: str
    status: Literal["running", "done", "error"]
    iteration_count: int
```

---

## Tools

| Tool | Signature | Description |
|---|---|---|
| `read_file` | `(path: str) → str` | Read file content from workspace |
| `write_file` | `(path: str, content: str) → str` | Write or overwrite a file |
| `list_files` | `(directory: str) → list[str]` | List files in a directory |
| `run_command` | `(cmd: str) → str` | Run shell command, return stdout+stderr |
| `web_search` | `(query: str) → str` | Search the web, return top results |

All tools are sandboxed to the configured workspace path. `run_command` has a 30s timeout.

---

## Backend Changes

### New files
- `backend/app/agent/graph.py` — LangGraph graph definition
- `backend/app/agent/state.py` — AgentState TypedDict
- `backend/app/agent/tools.py` — All 5 tool implementations
- `backend/app/agent/llm.py` — Gemini client setup via `langchain-google-genai`
- `backend/app/routers/agent.py` — FastAPI SSE endpoint

### Modified files
- `backend/app/main.py` — Register `agent` router
- `backend/requirements.txt` — Add `langgraph`, `langchain-google-genai`, `google-generativeai`, `langchain-community`
- `backend/.env` — Add `GOOGLE_API_KEY`

### Endpoint

```
POST /api/agent/run
Body: { "task": "...", "workspace_path": "..." }
Response: text/event-stream

Event format:
data: {"type": "plan",   "data": ["step 1", "step 2"]}
data: {"type": "step",   "data": "Writing routes/items.py"}
data: {"type": "tool",   "data": "run_command: pytest → PASSED"}
data: {"type": "done",   "data": "Feature complete. Files changed: [...]"}
data: {"type": "error",  "data": "Max iterations reached"}
```

---

## Frontend Changes

### New files
- `frontend/app/agent/page.tsx` — Agent chat page
- `frontend/components/agent/TaskInput.tsx` — Textarea + submit button
- `frontend/components/agent/AgentStream.tsx` — SSE event renderer (step-by-step)

### Modified files
- `frontend/app/page.tsx` — Add link to `/agent`

### UI Flow

1. User types feature request → clicks "Run Agent"
2. POST to `/api/agent/run` opens SSE connection
3. `AgentStream` renders each event as a card: Plan / Step / Tool output / Done
4. On completion, files changed are listed with links

---

## Dependencies

### Python (add to requirements.txt)
```
langgraph>=0.2.0
langchain-google-genai>=1.0.0
langchain-community>=0.2.0
google-generativeai>=0.8.0
```

### Environment variable
```
GOOGLE_API_KEY=your_gemini_api_key
```

---

## Verification

1. Start backend: `uvicorn app.main:app --reload` — confirm `/api/agent/run` appears in docs
2. Start frontend: `npm run dev` — confirm `/agent` page loads
3. Submit a simple task: "Add a GET /api/ping endpoint that returns `{pong: true}`"
4. Watch stream events: plan → step → tool outputs → done
5. Verify `backend/app/routers/ping.py` was created by the agent
6. `curl localhost:8000/api/ping` → `{"pong": true}`
7. Submit a task that requires web search (e.g., "Add rate limiting using slowapi") — verify search tool fires

---

## Out of Scope (v1)

- Authentication / API key management for multi-user
- Persistent run history / database storage
- Docker sandboxing for `run_command`
- Support for multiple LLM providers (Gemini only in v1)

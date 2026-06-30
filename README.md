# 🛟 Clutch — Your AI Last-Minute Life Saver

An **autonomous productivity agent** that goes beyond passive reminders. You brain-dump
everything on your mind (by typing **or voice**); Clutch prioritizes it, builds a realistic
time-blocked schedule, breaks down what's at risk of slipping, and drafts the messages you
need to send — then tracks what you actually finish, so you *complete* the work before
deadlines hit.

Built for the **Last-Minute Life Saver** problem statement.

> ⚠️ **Setup note:** add a valid Gemini API key from
> [aistudio.google.com/apikey](https://aistudio.google.com/apikey) to `backend/.env`
> (`GOOGLE_API_KEY=...`). The bundled key is a placeholder and will fail with
> `API_KEY_INVALID`.

---

## What makes it agentic

A 3-node **LangGraph** loop — `triage → act → review` — that *takes action*, not just text:

| Node | What it does |
|---|---|
| **triage** | Gemini scores every *outstanding* task by urgency × importance × effort-vs-time-left, and flags what will be **missed** at current pace |
| **act** | Gemini autonomously calls tools: `create_time_block` (schedules focus time), `break_down_task` (decomposes at-risk work), `draft_message` (writes the email/reminder), `web_search` |
| **review** | Gemini checks every critical task is covered, then loops back or finishes with a plain-English rescue summary |

The agent is **completion-aware**: tasks you mark done (and finished subtasks) are dropped
from triage and scheduling, so re-running the plan reschedules only what's left.

Progress streams to the UI live over **Server-Sent Events**.

## Google technologies

- **Gemini** (`gemini-2.5-flash` via `langchain-google-genai`, AI Studio Developer API) —
  triage, tool-use, and the brain-dump → structured-task extractor
- **Google Calendar** — every scheduled block produces a one-click *Add to Google Calendar* link
- **Google Cloud Run** — both services deploy here (see [DEPLOY.md](DEPLOY.md))

## Architecture

```
Next.js UI ──POST /api/agent/plan──► FastAPI ──► LangGraph agent
           ◄──── SSE stream ───────             (triage → act → review)
                                                       │
                         get_current_datetime · list_tasks · create_time_block
                         break_down_task · draft_message · web_search
                                                       │
                                                  Gemini 2.0 Flash
```

## Project structure

```
backend/
  app/
    store.py            # shared in-memory tasks/schedule/drafts + Google Calendar links
    agent/
      graph.py          # LangGraph triage → act → review loop
      tools.py          # the agent's action tools (operate on the store)
      extract.py        # Gemini brain-dump → structured tasks
      state.py, llm.py
    routers/
      tasks.py          # task CRUD + /extract + /snapshot + /reset
      agent.py          # POST /agent/plan  (SSE stream)
      health.py
    main.py, core/config.py
frontend/
  app/page.tsx          # the whole app: brain-dump, task board, rescue agent
  components/           # BrainDump, TaskCard, RescuePlan (streaming)
  lib/                  # api client, SSE stream reader, types, formatters
```

## Run locally

**Quick start (both services from the repo root):**
```bash
npm install                 # installs the root orchestrator (concurrently)
npm run setup               # frontend deps + backend venv & requirements
# add your key: backend/.env -> GOOGLE_API_KEY=your_key
npm run dev                 # backend :8000 + frontend :3000 together
```

<details><summary>Or run each service manually</summary>

**Backend**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
echo "GOOGLE_API_KEY=your_key" > .env
uvicorn app.main:app --reload        # http://localhost:8000  (docs at /docs)
```

**Frontend**
```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev                          # http://localhost:3000
```
</details>

## Try it

1. The app seeds realistic demo tasks (assignment due tomorrow, interview prep, bill, etc.).
2. Or **brain-dump** your own — type it, or hit **🎤 Speak** to dictate: *"CS assignment due
   tomorrow night, PM interview Thursday, pay bill today, mom's gift this weekend."* → Gemini
   structures it into tasks.
3. Hit **Generate rescue plan** and watch the agent prioritize, schedule, break down, and draft.
4. Click **Add to Google Calendar** on any scheduled block.
5. **Check off** subtasks and **Mark done** as you finish — then re-run the plan; the agent
   reschedules only what's left.

## Deployment

See **[DEPLOY.md](DEPLOY.md)** for Google Cloud Run instructions.

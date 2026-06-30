# Clutch — Your AI Last-Minute Life Saver

> Copy this into a Google Doc (set sharing to **"Anyone with the link → Viewer"**) for the submission.

---

## Problem Statement Selected

**The Last-Minute Life Saver.** Students, professionals, and entrepreneurs constantly
miss deadlines, assignments, interviews, and bill payments. Existing tools rely on
*passive reminders* that are easy to ignore and do nothing to help the user actually
finish the work. The challenge: build an AI companion that proactively helps users plan,
prioritize, and **complete** tasks before deadlines are missed.

## Solution Overview

**Clutch** is an autonomous productivity agent that does the work *around* your work.
You brain-dump everything on your mind in plain English. Clutch's AI agent then:

1. **Triages** — ranks every task by urgency × importance × effort-vs-time-remaining, and
   flags exactly which deadlines you will *miss* at your current pace.
2. **Acts** — autonomously builds a realistic, time-blocked schedule, breaks at-risk tasks
   into concrete subtasks, and drafts the messages you need to send (reminders, an honest
   extension request when something truly can't be finished in time).
3. **Reviews** — verifies every critical task is covered, then hands you a plain-English
   rescue plan and one-click *Add to Google Calendar* links.

It moves beyond reminders to **meaningful action** — the explicit evaluation focus of the
problem statement.

## Key Features

- **AI brain-dump → structured tasks.** Type *or speak* messy thoughts; Gemini extracts
  titles, resolves relative dates ("tomorrow", "Friday", "end of month") into real
  datetimes, estimates effort, and assigns importance and category.
- **Voice-enabled capture.** Dictate your brain-dump hands-free via the browser Web Speech
  API — the transcript flows straight into the Gemini extractor.
- **Autonomous rescue agent.** A LangGraph `triage → act → review` loop that calls real
  tools to schedule, decompose, and draft — not a chatbot.
- **At-risk detection.** Surfaces tasks that won't make their deadline given the time left.
- **Time-blocked scheduling** with **Google Calendar** add-event links (no OAuth friction).
- **Auto-drafted messages** so the user only has to hit send.
- **Completion tracking that closes the loop.** Check off subtasks and mark tasks done; the
  agent is completion-aware, so re-running the plan reschedules only the work that remains —
  the difference between *reminding* and helping you *finish*.
- **Live agent transparency.** The agent's reasoning and every action stream to the UI in
  real time via Server-Sent Events.

## Technologies Used

- **Backend:** Python, FastAPI, LangGraph (agent orchestration), Server-Sent Events for
  streaming, Pydantic.
- **Frontend:** Next.js 15 (App Router), React 19, TypeScript.
- **AI:** Google Gemini via `langchain-google-genai`.
- **Tooling:** DuckDuckGo search (agent web-research tool), Docker.

## Google Technologies Utilized

- **Google Gemini (`gemini-2.5-flash`)** — powers task triage/prioritization, autonomous
  tool-calling in the agent loop, and the natural-language brain-dump extractor.
- **Google Calendar** — every scheduled focus block generates a one-click "Add to Google
  Calendar" event link.
- **Google Cloud Run** — both the FastAPI backend and the Next.js frontend are deployed as
  containerized Cloud Run services (built with Google Cloud Build + Artifact Registry).

## How It Maps to the Evaluation Matrix

- **Problem Solving & Impact (20%)** — converts deadline anxiety into a concrete, executed
  plan, then **tracks completion** to actually get the user across the line; tackles the
  exact "passive reminders don't work" pain.
- **Agentic Depth (20%)** — a real multi-node agent that perceives (triage), acts (tools),
  and self-checks (review) in a loop, with autonomous tool selection — and is
  **completion-aware**, re-planning around the work you've already finished.
- **Innovation & Creativity (20%)** — the agent *executes* (schedules, decomposes, drafts)
  rather than just notifying; at-risk prediction; **voice** brain-dump → plan in one step.
- **Usage of Google Technologies (15%)** — Gemini + Google Calendar + Cloud Run.
- **Product Experience & Design (10%)** — clean dark UI, voice capture, interactive
  completion tracking, live-streaming agent activity.
- **Technical Implementation (10%)** — typed FastAPI + Next.js, streaming, containerized.
- **Completeness & Usability (5%)** — seeded demo data, one-command run (`npm run dev`),
  deployed link.

## Links

- **Deployed app:** https://clutch-frontend-78884710887.asia-south1.run.app
  (backend API: https://clutch-backend-78884710887.asia-south1.run.app)
- **GitHub repo:** https://github.com/gurdipsembhi/clutch
- **Demo video (optional):** _<add link>_

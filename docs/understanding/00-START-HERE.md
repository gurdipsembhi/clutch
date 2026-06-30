# 🧭 Understanding Clutch — Start Here

This folder is a guided tour of the **Clutch** codebase. The goal: take you from
"I have a folder of files" to "I understand how every part works and why."

## What is Clutch (one paragraph)

Clutch is an **autonomous productivity agent**. You type a messy "brain dump" of
everything on your mind; Gemini turns it into structured tasks. Then an AI agent
(built on **LangGraph**) runs a `triage → act → review` loop: it scores every task
by urgency, builds a time-blocked schedule, breaks big tasks into subtasks, and
drafts the messages you need to send. The whole process streams to the browser
live. Backend is **FastAPI (Python)**, frontend is **Next.js (React/TypeScript)**,
the brain is **Gemini via Google Vertex AI**.

## The technical terms for "understanding a project"

You asked what we *call* it when you study a project in detail. Here are the terms,
which double as the different lenses this folder uses:

| Term | Meaning | Which doc covers it |
|---|---|---|
| **Architecture analysis** | Understanding the high-level design & how pieces connect | [01-architecture.md](01-architecture.md) |
| **Codebase exploration / code comprehension** | Reading the code module by module to learn how it works | [02](02-backend-walkthrough.md), [03](03-agent-deep-dive.md), [04](04-frontend-walkthrough.md) |
| **Control-flow / data-flow tracing** | Following one request from start to finish | [05-end-to-end-flow.md](05-end-to-end-flow.md) |
| **Onboarding** | Everything a new developer needs to get productive | this whole folder |
| **Glossary / domain modelling** | The vocabulary and core data shapes | [06-glossary.md](06-glossary.md) |

## Suggested reading order

1. **[01-architecture.md](01-architecture.md)** — the big picture. Read this first.
2. **[05-end-to-end-flow.md](05-end-to-end-flow.md)** — trace one click through the
   whole system. This is the fastest way to "get it."
3. **[02-backend-walkthrough.md](02-backend-walkthrough.md)** — the FastAPI server,
   data store, and REST endpoints.
4. **[03-agent-deep-dive.md](03-agent-deep-dive.md)** — the heart of the project: the
   LangGraph agent and its tools.
5. **[04-frontend-walkthrough.md](04-frontend-walkthrough.md)** — the Next.js UI and
   how it consumes the live stream.
6. **[06-glossary.md](06-glossary.md)** — keep this open as a reference.

## How to read code effectively (a method, not just these docs)

When you open *any* unfamiliar project, do these in order:

1. **Read the README + run instructions.** Learn what it claims to do.
2. **Find the entry points.** Where does execution start?
   - Backend: `backend/app/main.py`
   - Frontend: `frontend/app/page.tsx`
3. **Map the folders to responsibilities** (see [01](01-architecture.md)).
4. **Trace one feature end-to-end** instead of reading every file (see [05](05-end-to-end-flow.md)).
5. **Identify the core data structures.** In Clutch it's the `task` dict
   (`backend/app/store.py:85`) and the `PlanState` (`backend/app/agent/state.py:6`).
   Once you know the data, the code makes sense.
6. **Note the external dependencies** (Gemini, Vertex AI, DuckDuckGo search).

> 💡 The single most important skill is *tracing*, not *reading*. You will never
> understand a codebase by reading files top to bottom. You understand it by
> following one piece of data on its journey through the system.

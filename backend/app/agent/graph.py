"""Deadline-rescue agent: triage -> act -> review.

triage   Gemini scores every task by urgency x importance and flags what's at risk.
act      Gemini takes real action via tools: time-blocks the schedule, breaks down
         at-risk tasks, and drafts messages the user needs to send.
review   Gemini checks that every critical/at-risk task is covered, then loops or finishes.
"""
import json
from typing import AsyncGenerator

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from app import store
from app.agent.state import PlanState
from app.agent.llm import get_llm
from app.agent.tools import ALL_TOOLS

MAX_ITERATIONS = 4

_TRIAGE_SYSTEM = """You are an elite executive assistant and productivity strategist.
Given the user's tasks, rank them so the most deadline-critical, high-impact work comes first.

For EACH task assign:
- priority_score: integer 0-100 (100 = drop everything and do this now)
- reason: one short sentence on why it ranks where it does
- risk: a short flag if the deadline is likely to be MISSED at current pace
  (e.g. "Only 6h left for 4h of unstarted work"), else "" (empty string)

Weigh: time remaining until the deadline, estimated effort vs. time left, stated
importance, and whether work has started. Overdue or about-to-slip items rank highest.

Respond with ONLY a JSON array, no prose:
[{"task_id": "...", "priority_score": 95, "reason": "...", "risk": "..."}]"""

_ACT_SYSTEM = """You are an autonomous productivity agent. You don't just remind — you ACT.
You have tools: get_current_datetime, list_tasks, create_time_block, break_down_task,
draft_message, web_search.

Your job, for the user's prioritized tasks within the available time window:
1. Build a REALISTIC time-blocked schedule with create_time_block for the most urgent
   and at-risk tasks. Start blocks after the current time. Respect fixed-time items
   (appointments). Add short breaks. Don't overload a day beyond ~6 focused hours.
2. break_down_task any large (>120 min) or critical task into concrete, ordered subtasks.
3. draft_message for anything the user clearly needs to send — a self-reminder, or an
   honest extension request ONLY if a deadline genuinely cannot be met in the time left.
4. Use web_search only if specific external info would unblock a task.

Be decisive and concrete. Use real task_ids from the list. Take all needed actions, then
briefly state what you did."""

_REVIEW_SYSTEM = """You are reviewing a rescue plan. Decide if every critical or at-risk
task has been addressed (scheduled, broken down, or drafted).

Respond with ONLY JSON:
{"verdict": "done" | "continue", "summary": "<2-4 sentence plain-English rescue summary
addressed to the user, naming the most urgent thing to start first>"}"""


def _extract_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()


def _triage(state: PlanState) -> PlanState:
    # Only rescue work that's still outstanding — completed tasks need no plan.
    tasks = [t for t in store.list_tasks() if t["status"] != "done"]
    catalog = []
    for t in tasks:
        h = store.hours_until(t["deadline"])
        when = "no deadline" if h is None else (f"{h}h left" if h >= 0 else f"OVERDUE by {-h}h")
        subs = t["subtasks"]
        progress = f" | subtasks {sum(s['done'] for s in subs)}/{len(subs)} done" if subs else ""
        catalog.append(
            f'task_id={t["id"]}: "{t["title"]}" | importance={t["importance"]} | '
            f'effort=~{t["estimated_minutes"] or "?"}min | {when} | status={t["status"]}{progress}'
            + (f' | notes: {t["notes"]}' if t["notes"] else "")
        )

    llm = get_llm()
    response = llm.invoke([
        SystemMessage(content=_TRIAGE_SYSTEM),
        HumanMessage(content=(
            f"Current time: {state['now']}\n"
            f"User note: {state['instruction'] or '(none)'}\n\n"
            "Tasks:\n" + "\n".join(catalog)
        )),
    ])

    try:
        ranked = json.loads(_extract_json(response.content))
    except Exception:
        ranked = [{"task_id": t["id"], "priority_score": 50, "reason": "", "risk": ""} for t in tasks]

    priorities = []
    title_by_id = {t["id"]: t["title"] for t in tasks}
    for item in ranked:
        tid = str(item.get("task_id", ""))
        if tid not in title_by_id:
            continue
        score = int(item.get("priority_score", 50))
        reason = str(item.get("reason", ""))
        risk = str(item.get("risk", "")) or None
        store.set_priority(tid, score, reason, risk)
        priorities.append({"task_id": tid, "title": title_by_id[tid], "priority_score": score, "reason": reason, "risk": risk})

    priorities.sort(key=lambda p: -p["priority_score"])
    return {**state, "tasks": tasks, "priorities": priorities, "status": "running"}


def _act(state: PlanState) -> PlanState:
    llm = get_llm().bind_tools(ALL_TOOLS)
    ranked_lines = [
        f'{i + 1}. task_id={p["task_id"]} | {p["title"]} | priority={p["priority_score"]}'
        + (f' | RISK: {p["risk"]}' if p["risk"] else "")
        for i, p in enumerate(state["priorities"])
    ]

    messages = [
        SystemMessage(content=_ACT_SYSTEM),
        HumanMessage(content=(
            f"Current time: {state['now']}\n"
            f"Available scheduling window: next {state['horizon_hours']} hours\n"
            f"User note: {state['instruction'] or '(none)'}\n\n"
            "Prioritized tasks:\n" + "\n".join(ranked_lines)
        )),
    ]

    actions = list(state.get("actions", []))
    for _ in range(10):
        response = llm.invoke(messages)
        messages.append(response)
        if not response.tool_calls:
            break
        for tc in response.tool_calls:
            matched = next((t for t in ALL_TOOLS if t.name == tc["name"]), None)
            result = matched.invoke(tc["args"]) if matched else f"Unknown tool: {tc['name']}"
            actions.append(str(result))
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": str(result)})

    return {**state, "actions": actions, "iteration_count": state.get("iteration_count", 0) + 1}


def _review(state: PlanState) -> PlanState:
    snap = store.snapshot()
    llm = get_llm()
    response = llm.invoke([
        SystemMessage(content=_REVIEW_SYSTEM),
        HumanMessage(content=(
            f"Tasks (with priority + risk): {json.dumps(state['priorities'])}\n\n"
            f"Scheduled blocks: {json.dumps([{k: b[k] for k in ('title', 'start', 'end')} for b in snap['schedule']])}\n\n"
            f"Drafts created: {json.dumps([d['subject'] for d in snap['drafts']])}\n\n"
            f"Actions log:\n" + "\n".join(state.get("actions", [])[-12:])
        )),
    ])

    verdict, summary = "done", ""
    try:
        parsed = json.loads(_extract_json(response.content))
        verdict = str(parsed.get("verdict", "done")).lower()
        summary = str(parsed.get("summary", ""))
    except Exception:
        summary = response.content.strip()

    if verdict == "done" or state.get("iteration_count", 0) >= MAX_ITERATIONS:
        return {**state, "status": "done", "summary": summary or "Rescue plan ready."}
    return {**state, "summary": summary}


def _should_continue(state: PlanState) -> str:
    if state["status"] == "done":
        return "end"
    if state.get("iteration_count", 0) >= MAX_ITERATIONS:
        return "end"
    return "act"


def build_graph():
    g = StateGraph(PlanState)
    g.add_node("triage", _triage)
    g.add_node("act", _act)
    g.add_node("review", _review)
    g.set_entry_point("triage")
    g.add_edge("triage", "act")
    g.add_edge("act", "review")
    g.add_conditional_edges("review", _should_continue, {"act": "act", "end": END})
    return g.compile()


async def run_plan(instruction: str = "", horizon_hours: int = 48) -> AsyncGenerator[dict, None]:
    graph = build_graph()
    initial: PlanState = {
        "instruction": instruction,
        "now": store.now_iso(),
        "horizon_hours": horizon_hours,
        "tasks": [],
        "priorities": [],
        "actions": [],
        "summary": "",
        "status": "running",
        "iteration_count": 0,
    }

    prev_actions = 0
    async for event in graph.astream(initial):
        node = list(event.keys())[0]
        state: PlanState = event[node]

        if node == "triage" and state.get("priorities"):
            yield {"type": "triage", "data": state["priorities"]}

        if node == "act":
            new_actions = state.get("actions", [])[prev_actions:]
            for a in new_actions:
                yield {"type": "action", "data": a}
            prev_actions = len(state.get("actions", []))

        if node == "review" and state.get("status") == "done":
            yield {"type": "done", "data": state.get("summary", "Rescue plan ready."), "snapshot": store.snapshot()}

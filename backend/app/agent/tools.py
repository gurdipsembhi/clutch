"""Tools the rescue agent can call to take real action on the user's behalf.

Everything operates on the shared in-memory store, so changes the agent makes
(schedule blocks, subtasks, drafts) are immediately visible in the UI.
"""
from langchain_core.tools import tool
from duckduckgo_search import DDGS

from app import store


@tool
def get_current_datetime() -> str:
    """Return the current local date and time (ISO 8601). Use this to reason about deadlines."""
    return store.now_iso()


@tool
def list_tasks() -> str:
    """List the user's OUTSTANDING tasks (completed ones are omitted) with deadlines,
    effort, importance, and any remaining subtasks still to do."""
    tasks = [t for t in store.list_tasks() if t["status"] != "done"]
    if not tasks:
        return "(no outstanding tasks)"
    lines = []
    for t in tasks:
        h = store.hours_until(t["deadline"])
        when = "no deadline" if h is None else (f"{h}h left" if h >= 0 else f"OVERDUE by {-h}h")
        line = (
            f"- id={t['id']} | {t['title']} | importance={t['importance']} | "
            f"~{t['estimated_minutes'] or '?'}min | {when} | status={t['status']}"
        )
        todo = [s["title"] for s in t["subtasks"] if not s["done"]]
        if todo:
            line += " | remaining subtasks: " + "; ".join(todo)
        lines.append(line)
    return "\n".join(lines)


@tool
def create_time_block(task_id: str, title: str, start: str, end: str, focus: str = "") -> str:
    """Schedule a focused work block for a task.

    Args:
        task_id: the task this block is for (use '' for a generic block).
        title: short label for the calendar event.
        start: ISO datetime for when the block starts (e.g. 2026-06-27T19:00:00).
        end: ISO datetime for when the block ends.
        focus: what specifically to accomplish in this block.
    """
    block = store.add_block(task_id or None, title, start, end, focus)
    return f"Scheduled '{title}' {start} -> {end}. Add-to-calendar link ready."


@tool
def break_down_task(task_id: str, subtasks: list[str]) -> str:
    """Break a large or at-risk task into concrete, ordered subtasks the user can act on."""
    task = store.add_subtasks(task_id, subtasks)
    if task is None:
        return f"ERROR: no task with id={task_id}"
    return f"Added {len(subtasks)} subtasks to '{task['title']}'."


@tool
def draft_message(task_id: str, kind: str, subject: str, body: str) -> str:
    """Draft a message the user likely needs to send (so they only have to hit send).

    Args:
        task_id: related task id (use '' if none).
        kind: one of 'reminder', 'email', 'extension_request', 'message', 'note'.
        subject: subject line / title.
        body: the full drafted message.
    """
    store.add_draft(task_id or None, kind, subject, body)
    return f"Drafted {kind}: '{subject}'."


@tool
def web_search(query: str) -> str:
    """Search the web for information that helps complete a task (how-tos, references, facts)."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=4))
        if not results:
            return "No results found."
        return "\n".join(f"- {r.get('title', '')}: {r.get('body', '')}" for r in results)
    except Exception as e:  # noqa: BLE001
        return f"ERROR: {e}"


ALL_TOOLS = [
    get_current_datetime,
    list_tasks,
    create_time_block,
    break_down_task,
    draft_message,
    web_search,
]

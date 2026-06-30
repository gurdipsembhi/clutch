"""In-memory data store for tasks, schedule blocks, and drafts.

Single source of truth shared by the REST endpoints and the agent's tools.
State is process-local and resets on restart — fine for a single-instance demo.
Swap the dict-backed functions for Firestore to make it durable.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from threading import RLock
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

from app.core.config import settings

_lock = RLock()
_tasks: dict[str, dict] = {}
_blocks: dict[str, dict] = {}
_drafts: dict[str, dict] = {}

_TZ = ZoneInfo(settings.TIMEZONE)


def now() -> datetime:
    """Current time in the configured local timezone."""
    return datetime.now(_TZ)


def now_iso() -> str:
    return now().isoformat()


def _id() -> str:
    return uuid.uuid4().hex[:12]


def parse_dt(value: str | None) -> datetime | None:
    """Parse an ISO datetime; assume local tz if no offset is given."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_TZ)
    return dt


def hours_until(deadline: str | None) -> float | None:
    """Hours from now until the deadline (negative if overdue)."""
    dt = parse_dt(deadline)
    if dt is None:
        return None
    return round((dt - now()).total_seconds() / 3600, 1)


def gcal_link(title: str, start: str, end: str, details: str = "") -> str:
    """Build a Google Calendar 'add event' template link (no OAuth required)."""
    s, e = parse_dt(start), parse_dt(end)
    if not s or not e:
        return ""
    fmt = "%Y%m%dT%H%M%SZ"
    dates = f"{s.astimezone(timezone.utc).strftime(fmt)}/{e.astimezone(timezone.utc).strftime(fmt)}"
    base = "https://calendar.google.com/calendar/render?action=TEMPLATE"
    return (
        f"{base}&text={quote_plus(title)}&dates={dates}"
        f"&details={quote_plus(details)}"
    )


# --- Tasks -----------------------------------------------------------------

def add_task(
    title: str,
    deadline: str | None = None,
    estimated_minutes: int | None = None,
    importance: str = "medium",
    category: str = "general",
    notes: str = "",
) -> dict:
    with _lock:
        tid = _id()
        task = {
            "id": tid,
            "title": title,
            "notes": notes,
            "deadline": deadline,
            "estimated_minutes": estimated_minutes,
            "importance": importance,
            "category": category,
            "status": "todo",
            "subtasks": [],
            "priority_score": None,
            "priority_reason": None,
            "risk": None,
            "created_at": now_iso(),
        }
        _tasks[tid] = task
        return task


def list_tasks() -> list[dict]:
    with _lock:
        items = list(_tasks.values())
    items.sort(key=lambda t: (t["priority_score"] is None, -(t["priority_score"] or 0)))
    return items


def get_task(task_id: str) -> dict | None:
    with _lock:
        return _tasks.get(task_id)


def update_task(task_id: str, **fields) -> dict | None:
    with _lock:
        task = _tasks.get(task_id)
        if not task:
            return None
        for k, v in fields.items():
            if v is not None and k in task:
                task[k] = v
        return task


def delete_task(task_id: str) -> bool:
    with _lock:
        return _tasks.pop(task_id, None) is not None


def set_priority(task_id: str, score: float, reason: str, risk: str | None = None) -> dict | None:
    with _lock:
        task = _tasks.get(task_id)
        if not task:
            return None
        task["priority_score"] = score
        task["priority_reason"] = reason
        if risk is not None:
            task["risk"] = risk
        return task


def add_subtasks(task_id: str, titles: list[str]) -> dict | None:
    with _lock:
        task = _tasks.get(task_id)
        if not task:
            return None
        for title in titles:
            task["subtasks"].append({"id": _id(), "title": title, "done": False})
        return task


def toggle_subtask(task_id: str, subtask_id: str) -> dict | None:
    """Flip a subtask's done flag. Returns the parent task, or None if not found."""
    with _lock:
        task = _tasks.get(task_id)
        if not task:
            return None
        for sub in task["subtasks"]:
            if sub["id"] == subtask_id:
                sub["done"] = not sub["done"]
                return task
        return None


# --- Schedule blocks -------------------------------------------------------

def add_block(task_id: str | None, title: str, start: str, end: str, focus: str = "") -> dict:
    with _lock:
        bid = _id()
        block = {
            "id": bid,
            "task_id": task_id,
            "title": title,
            "start": start,
            "end": end,
            "focus": focus,
            "gcal_link": gcal_link(title, start, end, focus),
        }
        _blocks[bid] = block
        return block


def list_blocks() -> list[dict]:
    with _lock:
        items = list(_blocks.values())
    items.sort(key=lambda b: b["start"] or "")
    return items


# --- Drafts ----------------------------------------------------------------

def add_draft(task_id: str | None, kind: str, subject: str, body: str) -> dict:
    with _lock:
        did = _id()
        draft = {
            "id": did,
            "task_id": task_id,
            "kind": kind,
            "subject": subject,
            "body": body,
            "created_at": now_iso(),
        }
        _drafts[did] = draft
        return draft


def list_drafts() -> list[dict]:
    with _lock:
        return list(_drafts.values())


def snapshot() -> dict:
    return {
        "tasks": list_tasks(),
        "schedule": list_blocks(),
        "drafts": list_drafts(),
        "now": now_iso(),
    }


def reset(seed: bool = True) -> None:
    with _lock:
        _tasks.clear()
        _blocks.clear()
        _drafts.clear()
    if seed:
        _seed()


def _seed() -> None:
    """Realistic demo tasks anchored relative to 'now' so countdowns stay live."""
    base = now()

    def at(days: float, hour: int, minute: int = 0) -> str:
        d = (base + timedelta(days=days)).replace(hour=hour, minute=minute, second=0, microsecond=0)
        return d.isoformat()

    add_task(
        title="Submit Data Structures assignment (Graphs)",
        deadline=at(1, 23, 59),
        estimated_minutes=240,
        importance="critical",
        category="college",
        notes="Implement Dijkstra + writeup. Haven't started the report section.",
    )
    add_task(
        title="Prepare for Product Manager interview at Acme",
        deadline=at(2, 10, 0),
        estimated_minutes=180,
        importance="critical",
        category="career",
        notes="Behavioral + a product design round. Review STAR stories.",
    )
    add_task(
        title="Pay electricity bill",
        deadline=at(0, 20, 0),
        estimated_minutes=10,
        importance="high",
        category="finance",
        notes="Late fee kicks in after due date.",
    )
    add_task(
        title="Buy Mom a birthday gift",
        deadline=at(3, 18, 0),
        estimated_minutes=60,
        importance="high",
        category="personal",
    )
    add_task(
        title="Dentist appointment",
        deadline=at(2, 15, 30),
        estimated_minutes=45,
        importance="medium",
        category="health",
        notes="Fixed time — cannot move.",
    )
    add_task(
        title="Review teammate's pull request",
        deadline=at(1, 17, 0),
        estimated_minutes=30,
        importance="medium",
        category="work",
    )


# Seed on import so the demo has data immediately.
_seed()

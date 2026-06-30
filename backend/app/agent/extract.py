"""Turn a free-text brain-dump into structured tasks using Gemini."""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from app import store
from app.agent.llm import get_llm

_SYSTEM = """You extract actionable tasks from a messy brain-dump.
The current date-time is provided; resolve relative dates ("tomorrow", "Friday",
"end of month", "in 3 days") into absolute ISO 8601 datetimes in the user's local time.

For each task return:
- title: short imperative title
- deadline: ISO 8601 datetime, or null if none implied
- estimated_minutes: your best estimate of effort in minutes (integer), or null
- importance: one of "low" | "medium" | "high" | "critical"
- category: short label (e.g. college, work, finance, health, personal, career)
- notes: any extra detail from the text, else ""

Respond with ONLY a JSON array of task objects. No prose, no code fences."""


def extract_tasks(text: str) -> list[dict]:
    llm = get_llm(temperature=0)
    response = llm.invoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=f"Current date-time: {store.now_iso()}\n\nBrain-dump:\n{text}"),
    ])

    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        parsed = json.loads(raw.strip())
    except Exception:
        return []

    created = []
    for item in parsed if isinstance(parsed, list) else []:
        if not item.get("title"):
            continue
        created.append(store.add_task(
            title=str(item["title"]),
            deadline=item.get("deadline") or None,
            estimated_minutes=item.get("estimated_minutes"),
            importance=str(item.get("importance", "medium")),
            category=str(item.get("category", "general")),
            notes=str(item.get("notes", "")),
        ))
    return created

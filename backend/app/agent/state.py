from typing import Literal

from typing_extensions import TypedDict


class PlanState(TypedDict):
    """State for the deadline-rescue agent (triage -> act -> review)."""

    instruction: str          # optional user directive, e.g. "I only have tonight"
    now: str                  # current local datetime (ISO)
    horizon_hours: int        # how far ahead to schedule
    tasks: list[dict]         # snapshot of tasks at run start
    priorities: list[dict]    # ranked tasks with scores + reasons
    actions: list[str]        # log of tool actions taken
    summary: str              # final human-readable rescue summary
    status: Literal["running", "done", "error"]
    iteration_count: int

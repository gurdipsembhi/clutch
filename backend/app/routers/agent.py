import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agent.graph import run_plan

router = APIRouter(prefix="/agent", tags=["agent"])


class PlanRequest(BaseModel):
    instruction: str = ""
    horizon_hours: int = 48


async def _event_stream(instruction: str, horizon_hours: int):
    try:
        async for event in run_plan(instruction, horizon_hours):
            yield f"data: {json.dumps(event)}\n\n"
    except Exception as e:  # noqa: BLE001
        yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/plan")
async def plan(body: PlanRequest):
    """Run the autonomous rescue agent and stream its progress as Server-Sent Events."""
    return StreamingResponse(
        _event_stream(body.instruction, body.horizon_hours),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

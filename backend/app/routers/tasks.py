from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import store
from app.agent.extract import extract_tasks

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    title: str
    deadline: str | None = None
    estimated_minutes: int | None = None
    importance: str = "medium"
    category: str = "general"
    notes: str = ""


class TaskUpdate(BaseModel):
    title: str | None = None
    deadline: str | None = None
    estimated_minutes: int | None = None
    importance: str | None = None
    category: str | None = None
    notes: str | None = None
    status: str | None = None


class BrainDump(BaseModel):
    text: str


def _decorate(task: dict) -> dict:
    return {**task, "hours_until": store.hours_until(task["deadline"])}


@router.get("")
async def get_tasks():
    return {"tasks": [_decorate(t) for t in store.list_tasks()], "now": store.now_iso()}


@router.get("/snapshot")
async def get_snapshot():
    snap = store.snapshot()
    snap["tasks"] = [_decorate(t) for t in snap["tasks"]]
    return snap


@router.post("", status_code=201)
async def create_task(body: TaskCreate):
    return _decorate(store.add_task(**body.model_dump()))


@router.post("/extract", status_code=201)
async def extract(body: BrainDump):
    created = extract_tasks(body.text)
    return {"created": [_decorate(t) for t in created], "count": len(created)}


@router.patch("/{task_id}")
async def patch_task(task_id: str, body: TaskUpdate):
    task = store.update_task(task_id, **body.model_dump())
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _decorate(task)


@router.patch("/{task_id}/subtasks/{subtask_id}")
async def toggle_subtask(task_id: str, subtask_id: str):
    task = store.toggle_subtask(task_id, subtask_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task or subtask not found")
    return _decorate(task)


@router.delete("/{task_id}", status_code=204)
async def remove_task(task_id: str):
    if not store.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/reset", status_code=200)
async def reset_demo():
    store.reset(seed=True)
    return {"ok": True, "tasks": len(store.list_tasks())}

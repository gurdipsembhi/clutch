"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { Task } from "@/lib/types";
import { countdown, effort, importanceClass, scoreClass } from "@/lib/format";

export function TaskCard({
  task,
  onDelete,
  onChange,
}: {
  task: Task;
  onDelete: (id: string) => void;
  onChange: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const cd = countdown(task.hours_until);
  const eff = effort(task.estimated_minutes);
  const isDone = task.status === "done";
  const doneCount = task.subtasks.filter((s) => s.done).length;

  async function withBusy(fn: () => Promise<unknown>) {
    setBusy(true);
    try {
      await fn();
      onChange();
    } finally {
      setBusy(false);
    }
  }

  const toggleSubtask = (subtaskId: string) =>
    withBusy(() => api.toggleSubtask(task.id, subtaskId));

  const toggleDone = () =>
    withBusy(() => api.updateTask(task.id, { status: isDone ? "todo" : "done" }));

  return (
    <div className={`task ${importanceClass(task.importance)} ${isDone ? "is-done" : ""}`}>
      {task.priority_score !== null && (
        <span className={`score ${scoreClass(task.priority_score)}`}>{task.priority_score}</span>
      )}

      <div className="row between" style={{ paddingRight: task.priority_score !== null ? 38 : 24 }}>
        <span className="task-title">{task.title}</span>
      </div>

      <div className="task-meta">
        <span className={`chip ${cd.tone === "none" ? "" : cd.tone}`}>{cd.text}</span>
        {eff && <span className="chip">~{eff}</span>}
        <span className="chip cat">{task.category}</span>
        <span className="chip">{task.importance}</span>
        <button
          className={`done-btn ${isDone ? "active" : ""}`}
          onClick={toggleDone}
          disabled={busy}
          title={isDone ? "Mark as not done" : "Mark task done"}
        >
          {isDone ? "✓ Done" : "Mark done"}
        </button>
      </div>

      {task.risk && !isDone && (
        <div className="risk">
          <span>⚠️</span>
          <span>{task.risk}</span>
        </div>
      )}
      {task.priority_reason && <div className="reason">{task.priority_reason}</div>}

      {task.subtasks.length > 0 && (
        <div className="subtasks">
          <div className="subtasks-head">
            <span className="progress">
              {doneCount}/{task.subtasks.length} done
            </span>
          </div>
          {task.subtasks.map((s) => (
            <div
              key={s.id}
              className={`subtask clickable ${s.done ? "sub-done" : ""}`}
              onClick={() => !busy && toggleSubtask(s.id)}
              role="checkbox"
              aria-checked={s.done}
            >
              <span className="check">{s.done ? "●" : "○"}</span>
              <span>{s.title}</span>
            </div>
          ))}
        </div>
      )}

      <button
        className="del"
        onClick={() => onDelete(task.id)}
        style={{ position: "absolute", bottom: 8, right: 8 }}
        title="Delete task"
      >
        ×
      </button>
    </div>
  );
}

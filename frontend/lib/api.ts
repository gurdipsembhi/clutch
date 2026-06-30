import type { AgentEvent, Snapshot, Task } from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(error || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  snapshot: () => request<Snapshot>("/api/tasks/snapshot"),

  extract: (text: string) =>
    request<{ created: Task[]; count: number }>("/api/tasks/extract", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),

  addTask: (task: Partial<Task>) =>
    request<Task>("/api/tasks", { method: "POST", body: JSON.stringify(task) }),

  updateTask: (id: string, fields: Partial<Task>) =>
    request<Task>(`/api/tasks/${id}`, { method: "PATCH", body: JSON.stringify(fields) }),

  toggleSubtask: (taskId: string, subtaskId: string) =>
    request<Task>(`/api/tasks/${taskId}/subtasks/${subtaskId}`, { method: "PATCH" }),

  deleteTask: (id: string) =>
    request<void>(`/api/tasks/${id}`, { method: "DELETE" }),

  resetDemo: () => request<{ ok: boolean }>("/api/tasks/reset", { method: "POST" }),
};

/** Stream the rescue agent's progress as Server-Sent Events. */
export async function streamPlan(
  body: { instruction: string; horizon_hours: number },
  onEvent: (event: AgentEvent) => void,
): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/agent/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.body) throw new Error("No response body from agent");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const raw = line.slice(6).trim();
      if (raw === "[DONE]") return;
      try {
        onEvent(JSON.parse(raw) as AgentEvent);
      } catch {
        /* skip malformed line */
      }
    }
  }
}

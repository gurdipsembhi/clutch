export type Importance = "low" | "medium" | "high" | "critical";

export interface Subtask {
  id: string;
  title: string;
  done: boolean;
}

export interface Task {
  id: string;
  title: string;
  notes: string;
  deadline: string | null;
  estimated_minutes: number | null;
  importance: Importance;
  category: string;
  status: string;
  subtasks: Subtask[];
  priority_score: number | null;
  priority_reason: string | null;
  risk: string | null;
  created_at: string;
  hours_until: number | null;
}

export interface Block {
  id: string;
  task_id: string | null;
  title: string;
  start: string;
  end: string;
  focus: string;
  gcal_link: string;
}

export interface Draft {
  id: string;
  task_id: string | null;
  kind: string;
  subject: string;
  body: string;
  created_at: string;
}

export interface Snapshot {
  tasks: Task[];
  schedule: Block[];
  drafts: Draft[];
  now: string;
}

export interface Priority {
  task_id: string;
  title: string;
  priority_score: number;
  reason: string;
  risk: string | null;
}

export type AgentEvent =
  | { type: "triage"; data: Priority[] }
  | { type: "action"; data: string }
  | { type: "done"; data: string; snapshot: Snapshot }
  | { type: "error"; data: string };

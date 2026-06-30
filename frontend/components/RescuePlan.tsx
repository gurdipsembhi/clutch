"use client";

import { useState } from "react";
import { streamPlan } from "@/lib/api";
import type { AgentEvent, Block, Draft, Priority, Snapshot } from "@/lib/types";
import { timeRange } from "@/lib/format";

type Tab = "activity" | "schedule" | "drafts";

export function RescuePlan({
  schedule,
  drafts,
  onComplete,
}: {
  schedule: Block[];
  drafts: Draft[];
  onComplete: (snap: Snapshot) => void;
}) {
  const [instruction, setInstruction] = useState("");
  const [horizon, setHorizon] = useState(48);
  const [running, setRunning] = useState(false);
  const [actions, setActions] = useState<string[]>([]);
  const [priorities, setPriorities] = useState<Priority[]>([]);
  const [summary, setSummary] = useState("");
  const [error, setError] = useState("");
  const [tab, setTab] = useState<Tab>("activity");
  const [started, setStarted] = useState(false);

  async function run() {
    setRunning(true);
    setStarted(true);
    setActions([]);
    setPriorities([]);
    setSummary("");
    setError("");
    setTab("activity");

    try {
      await streamPlan({ instruction, horizon_hours: horizon }, (event: AgentEvent) => {
        if (event.type === "triage") setPriorities(event.data);
        else if (event.type === "action") setActions((prev) => [...prev, event.data]);
        else if (event.type === "error") setError(event.data);
        else if (event.type === "done") {
          setSummary(event.data);
          onComplete(event.snapshot);
          setTab("schedule");
        }
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Agent failed");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="card">
      <div className="card-head">
        <h2>⚡ Rescue agent</h2>
        <span className="sub">plan → act → review</span>
      </div>
      <div className="card-body">
        <div className="controls">
          <input
            type="text"
            placeholder="Optional: 'I only have tonight' or 'focus on college'"
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            disabled={running}
            style={{ flex: 1, minWidth: 160 }}
          />
          <select value={horizon} onChange={(e) => setHorizon(Number(e.target.value))} disabled={running}>
            <option value={12}>next 12h</option>
            <option value={24}>next 24h</option>
            <option value={48}>next 2 days</option>
            <option value={96}>next 4 days</option>
          </select>
        </div>
        <button className="primary-btn big-btn mt12" onClick={run} disabled={running}>
          {running ? (
            <>
              <span className="spinner" /> &nbsp;Agent is working…
            </>
          ) : (
            "⚡ Generate rescue plan"
          )}
        </button>

        {started && (
          <>
            <div className="tabs mt16">
              <button className={`tab ${tab === "activity" ? "active" : ""}`} onClick={() => setTab("activity")}>
                Activity
              </button>
              <button className={`tab ${tab === "schedule" ? "active" : ""}`} onClick={() => setTab("schedule")}>
                Schedule<span className="count-pill">{schedule.length}</span>
              </button>
              <button className={`tab ${tab === "drafts" ? "active" : ""}`} onClick={() => setTab("drafts")}>
                Drafts<span className="count-pill">{drafts.length}</span>
              </button>
            </div>

            <div className="mt12">
              {tab === "activity" && (
                <ActivityFeed priorities={priorities} actions={actions} summary={summary} error={error} running={running} />
              )}
              {tab === "schedule" && <ScheduleView blocks={schedule} />}
              {tab === "drafts" && <DraftsView drafts={drafts} />}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function ActivityFeed({
  priorities,
  actions,
  summary,
  error,
  running,
}: {
  priorities: Priority[];
  actions: string[];
  summary: string;
  error: string;
  running: boolean;
}) {
  return (
    <div className="stream">
      {priorities.length > 0 && (
        <div className="evt action">
          <div className="evt-label">Triage · ranked {priorities.length} tasks</div>
          {priorities.slice(0, 3).map((p) => (
            <p key={p.task_id} style={{ marginTop: 4 }}>
              <strong>{p.priority_score}</strong> · {p.title}
              {p.risk ? <span style={{ color: "var(--critical)" }}> — {p.risk}</span> : ""}
            </p>
          ))}
        </div>
      )}

      {actions.map((a, i) => (
        <div key={i} className="evt action">
          <div className="evt-label">Action</div>
          <p>{a}</p>
        </div>
      ))}

      {running && (
        <div className="evt action">
          <span className="spinner" /> &nbsp;<span style={{ fontSize: 13, color: "var(--muted)" }}>thinking…</span>
        </div>
      )}

      {summary && (
        <div className="evt summary">
          <div className="evt-label">Rescue summary</div>
          <p>{summary}</p>
        </div>
      )}

      {error && (
        <div className="evt error">
          <div className="evt-label">Error</div>
          <p>{error}</p>
        </div>
      )}

      {!running && actions.length === 0 && priorities.length === 0 && !error && (
        <div className="empty">No activity yet.</div>
      )}
    </div>
  );
}

function ScheduleView({ blocks }: { blocks: Block[] }) {
  if (blocks.length === 0) return <div className="empty">No time blocks scheduled yet.</div>;
  return (
    <div className="stream">
      {blocks.map((b) => (
        <div key={b.id} className="block-item">
          <div className="block-time">🕑 {timeRange(b.start, b.end)}</div>
          <div className="block-title">{b.title}</div>
          {b.focus && <div className="block-focus">{b.focus}</div>}
          {b.gcal_link && (
            <a className="gcal" href={b.gcal_link} target="_blank" rel="noreferrer">
              📅 Add to Google Calendar
            </a>
          )}
        </div>
      ))}
    </div>
  );
}

function DraftsView({ drafts }: { drafts: Draft[] }) {
  if (drafts.length === 0) return <div className="empty">No drafts created yet.</div>;
  return (
    <div className="stream">
      {drafts.map((d) => (
        <div key={d.id} className="draft-item">
          <div className="draft-kind">{d.kind.replace("_", " ")}</div>
          <div className="draft-subject">{d.subject}</div>
          <div className="draft-body">{d.body}</div>
        </div>
      ))}
    </div>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Snapshot } from "@/lib/types";
import { BrainDump } from "@/components/BrainDump";
import { TaskCard } from "@/components/TaskCard";
import { RescuePlan } from "@/components/RescuePlan";

const EMPTY: Snapshot = { tasks: [], schedule: [], drafts: [], now: "" };

export default function Home() {
  const [snap, setSnap] = useState<Snapshot>(EMPTY);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setSnap(await api.snapshot());
    } catch {
      /* backend may be waking up */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function handleDelete(id: string) {
    await api.deleteTask(id);
    refresh();
  }

  async function handleReset() {
    await api.resetDemo();
    refresh();
  }

  const atRisk = snap.tasks.filter((t) => t.risk).length;

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <div className="logo">🛟</div>
          <div>
            <h1>Clutch</h1>
            <p>Your AI last-minute life saver</p>
          </div>
        </div>
        <button className="ghost-btn" onClick={handleReset}>
          ↺ Reset demo
        </button>
      </header>

      <div className="grid">
        <div>
          <BrainDump onAdded={refresh} />

          <div className="card mt16">
            <div className="card-head">
              <h2>📋 Your tasks</h2>
              <span className="sub">
                {snap.tasks.length} total{atRisk > 0 && <span style={{ color: "var(--critical)" }}> · {atRisk} at risk</span>}
              </span>
            </div>
            <div className="card-body">
              {loading ? (
                <div className="empty">
                  <span className="spinner" /> &nbsp;Loading…
                </div>
              ) : snap.tasks.length === 0 ? (
                <div className="empty">No tasks yet — brain-dump above to get started.</div>
              ) : (
                snap.tasks.map((t) => (
                  <TaskCard key={t.id} task={t} onDelete={handleDelete} onChange={refresh} />
                ))
              )}
            </div>
          </div>
        </div>

        <RescuePlan schedule={snap.schedule} drafts={snap.drafts} onComplete={setSnap} />
      </div>
    </div>
  );
}

# 🎨 Frontend Walkthrough — Next.js + React

The frontend is a **single-page app** built with **Next.js 15** (App Router),
**React 19**, and **TypeScript**. It has no state management library and no UI
framework — just React state and plain CSS. That keeps it easy to read.

```
frontend/
  app/
    layout.tsx     ← the HTML shell (runs once, wraps everything)
    page.tsx       ← the actual page: layout + top-level state
    globals.css    ← all the styling (one file)
  components/
    BrainDump.tsx  ← textarea → extract tasks
    TaskCard.tsx   ← one task row
    RescuePlan.tsx ← the agent panel (the most complex component)
  lib/
    api.ts         ← every backend call + the SSE reader
    types.ts       ← TypeScript types mirroring the backend JSON
    format.ts      ← display helpers (countdowns, time ranges, CSS classes)
```

> **Mental model:** `page.tsx` owns the data (the `snapshot`). Components receive it
> as props and call back up when something changes (`onAdded`, `onDelete`,
> `onComplete`). This is React's standard "data down, events up" flow.

---

## 1. The API client — `lib/api.ts` (start here)

Everything the frontend knows about the backend is in this one file. Two parts:

### Part A — the `api` object (normal request/response)

`request<T>()` (`api.ts:5`) is a thin wrapper around `fetch` that:
- prepends `BASE_URL` (`NEXT_PUBLIC_API_URL`, default `http://localhost:8000`),
- sets the JSON content-type,
- throws on non-OK responses,
- returns `undefined` for `204 No Content` (e.g. delete), else parses JSON.

The `api` object then exposes typed methods that map 1:1 to backend endpoints:

```ts
api.snapshot()       → GET  /api/tasks/snapshot
api.extract(text)    → POST /api/tasks/extract
api.addTask(task)    → POST /api/tasks
api.deleteTask(id)   → DELETE /api/tasks/{id}
api.resetDemo()      → POST /api/tasks/reset
```

### Part B — `streamPlan()` (the SSE reader) — `api.ts:37`

This is the frontend counterpart to the backend's streaming endpoint. It does **not**
use `EventSource` (which only supports GET); instead it `fetch`es `POST /api/agent/plan`
and reads the response body as a stream:

```ts
const reader = res.body.getReader();
const decoder = new TextDecoder();
let buffer = "";
while (true) {
  const { done, value } = await reader.read();   // pull the next chunk
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  const lines = buffer.split("\n");
  buffer = lines.pop() ?? "";                     // keep the incomplete tail
  for (const line of lines) {
    if (!line.startsWith("data: ")) continue;     // SSE lines start with "data: "
    const raw = line.slice(6).trim();
    if (raw === "[DONE]") return;                 // backend's end sentinel
    onEvent(JSON.parse(raw) as AgentEvent);       // hand each event to the caller
  }
}
```

Why the `buffer` dance? Network chunks don't align to lines — a chunk might end
mid-JSON. So it accumulates text, splits on newlines, processes complete lines, and
**keeps the leftover partial line** (`buffer = lines.pop()`) for the next chunk. This
is the standard way to parse a streaming text protocol. Each parsed event is passed to
the caller's `onEvent` callback — that's how `RescuePlan` updates the UI live.

---

## 2. The types — `lib/types.ts`

This file is a TypeScript **mirror of the backend's JSON shapes**. `Task`
(`types.ts:9`) matches the task dict from `store.py:85`; `Block`, `Draft`, and
`Snapshot` match their store counterparts.

The most instructive type is `AgentEvent` (`types.ts:60`), a **discriminated union**:

```ts
export type AgentEvent =
  | { type: "triage"; data: Priority[] }
  | { type: "action"; data: string }
  | { type: "done"; data: string; snapshot: Snapshot }
  | { type: "error"; data: string };
```

Each SSE event the backend sends has a `type`. This union lets TypeScript know that if
`event.type === "done"`, then `event.snapshot` exists. It's the exact mirror of the
events `run_plan` yields in `graph.py`. Keeping these in sync is how the two halves of
the app "agree" on the protocol.

---

## 3. Display helpers — `lib/format.ts`

Pure functions that turn raw data into display strings/classes. No React here. Examples:

- `countdown(hours)` (`format.ts:1`) → `{ text: "6h left", tone: "soon" }`. Handles
  overdue (negative), `<1h`, hours, and days, and picks a color "tone."
- `effort(minutes)` → `"4h"` / `"45m"`.
- `timeRange(start, end)` → `"Mon, Jun 28 · 7:00 PM – 9:00 PM"` (used on schedule blocks).
- `importanceClass` / `scoreClass` → map a value to a CSS class for coloring.

Keeping these as separate pure functions makes components cleaner and the logic
testable in isolation.

---

## 4. The page — `app/page.tsx` (the top-level owner)

This component owns the single piece of shared state: the **`snapshot`** (all tasks,
schedule, drafts).

```tsx
const [snap, setSnap] = useState<Snapshot>(EMPTY);
const refresh = useCallback(async () => { setSnap(await api.snapshot()); ... }, []);
useEffect(() => { refresh(); }, [refresh]);   // fetch once on mount
```

- On mount, `useEffect` calls `refresh()` → fetches `/api/tasks/snapshot` → fills the
  UI with the seeded demo tasks.
- It renders a two-column `grid`: left = `BrainDump` + the task list (`TaskCard`s);
  right = `RescuePlan`.
- It passes callbacks down: `onAdded={refresh}` (re-fetch after extraction),
  `onDelete={handleDelete}`, and `onComplete={setSnap}` (the agent returns a fresh
  snapshot when it finishes, so the page just swaps it in).
- `atRisk` (`page.tsx:40`) counts tasks with a `risk` flag to show the "· N at risk"
  badge.

---

## 5. The components

### `BrainDump.tsx` — text → tasks

A textarea + button. On submit it calls `api.extract(text)`, shows "✓ Added N tasks,"
and calls `onAdded()` so the page re-fetches and the new tasks appear. Local state is
just `text`, `loading`, and a status `msg`. Simple and self-contained.

### `TaskCard.tsx` — one task

Pure presentation of a `Task`. Worth noting how it visualizes the **agent's
enrichment**:

- the **score badge** (`task.priority_score`) — only shown after triage ran
  (`TaskCard.tsx:12`);
- the **⚠️ risk banner** (`task.risk`) — the "will slip" flag from triage;
- the **priority reason** line;
- the **subtasks** list — populated by the agent's `break_down_task` tool.

So a task card literally renders raw data before a plan, and richer data after. It uses
the `format.ts` helpers for the countdown chip and importance coloring.

### `RescuePlan.tsx` — the agent panel (most complex)

This drives the streaming agent and shows its output across three tabs. Local state:
`instruction`, `horizon`, `running`, `actions`, `priorities`, `summary`, `error`,
`tab`, `started`.

The core is the `run()` function (`RescuePlan.tsx:29`):

```tsx
await streamPlan({ instruction, horizon_hours: horizon }, (event) => {
  if (event.type === "triage") setPriorities(event.data);
  else if (event.type === "action") setActions((prev) => [...prev, event.data]);
  else if (event.type === "error") setError(event.data);
  else if (event.type === "done") {
    setSummary(event.data);
    onComplete(event.snapshot);   // ← push the fresh snapshot up to page.tsx
    setTab("schedule");           // auto-switch to the schedule when finished
  }
});
```

This is the payoff of the whole streaming design: **as each SSE event arrives, a piece
of UI updates.** Triage results fill the activity feed; each action appends a row in
real time; on "done" the summary appears, the page's snapshot is refreshed (so the
schedule/drafts tabs populate), and the view jumps to the Schedule tab.

The three sub-views (defined in the same file):
- **`ActivityFeed`** (`RescuePlan.tsx:117`) — live log: triage ranking, each action,
  a "thinking…" spinner while running, the final summary, errors.
- **`ScheduleView`** (`RescuePlan.tsx:178`) — the time blocks, each with the
  **"📅 Add to Google Calendar"** link (that URL came from `store.gcal_link`).
- **`DraftsView`** (`RescuePlan.tsx:198`) — the drafted messages.

`schedule` and `drafts` come in as props from `page.tsx` (part of the snapshot), while
`actions`/`priorities`/`summary` are local streaming state. That split is why the
Activity feed updates *during* the run, while Schedule/Drafts fill in *at the end* when
the fresh snapshot arrives.

---

## 6. `layout.tsx` & `globals.css`

- `layout.tsx` is the App Router root layout — the `<html>`/`<body>` shell and page
  metadata, rendered once around every page.
- `globals.css` holds all styling (the CSS variables like `--critical`, `--success`
  referenced in components, plus card/chip/tab styles). No Tailwind, no CSS modules —
  one global stylesheet.

---

## The frontend's job, summarized

1. **Fetch** the snapshot and render tasks (`page.tsx` + `TaskCard`).
2. **Send** brain-dump text and re-fetch (`BrainDump`).
3. **Stream** the agent run and render its progress live (`RescuePlan` + `streamPlan`).
4. **Reflect** the agent's results — schedule, drafts, scores, subtasks — by swapping
   in the fresh snapshot.

It contains zero business logic; it's a thin, reactive view over the backend's state.
Now tie both halves together in [05-end-to-end-flow.md](05-end-to-end-flow.md).

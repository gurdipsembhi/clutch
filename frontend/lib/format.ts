export function countdown(hours: number | null): { text: string; tone: "overdue" | "soon" | "deadline" | "none" } {
  if (hours === null) return { text: "no deadline", tone: "none" };
  if (hours < 0) {
    const h = Math.abs(hours);
    return { text: h >= 24 ? `overdue ${Math.round(h / 24)}d` : `overdue ${Math.round(h)}h`, tone: "overdue" };
  }
  if (hours < 24) return { text: hours < 1 ? "due <1h" : `${Math.round(hours)}h left`, tone: hours < 12 ? "soon" : "deadline" };
  return { text: `${Math.round(hours / 24)}d left`, tone: "deadline" };
}

export function effort(minutes: number | null): string {
  if (!minutes) return "";
  if (minutes < 60) return `${minutes}m`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m ? `${h}h${m}m` : `${h}h`;
}

export function timeRange(start: string, end: string): string {
  const s = new Date(start);
  const e = new Date(end);
  const day = s.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
  const fmt = (d: Date) => d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  return `${day} · ${fmt(s)} – ${fmt(e)}`;
}

export function importanceClass(importance: string): string {
  return { critical: "crit", high: "high", medium: "med", low: "low" }[importance] ?? "med";
}

export function scoreClass(score: number | null): string {
  if (score === null) return "med";
  if (score >= 80) return "crit";
  if (score >= 55) return "high";
  return "med";
}

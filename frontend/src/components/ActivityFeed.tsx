import { useEffect, useRef } from "react";
import type { RunEvent } from "../types";

const KIND_COLOR: Record<string, string> = {
  run_started: "text-brand-soft",
  intake_complete: "text-brand-soft",
  tool_call: "text-amber-400",
  tool_return: "text-slate-500",
  assistant_text: "text-slate-300",
  agent_request_started: "text-slate-500",
  agent_finished: "text-emerald-400",
  run_complete: "text-emerald-400",
  run_failed: "text-red-400",
};

export function ActivityFeed({ events }: { events: RunEvent[] }) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [events]);

  return (
    <div className="max-h-64 overflow-y-auto rounded-xl border border-edge bg-canvas/60 p-3 font-mono text-xs">
      {events.length === 0 ? (
        <p className="text-slate-600">Waiting for events…</p>
      ) : (
        events.map((e) => (
          <div key={e.id} className="flex gap-2 py-0.5">
            <span className={`shrink-0 ${KIND_COLOR[e.kind] ?? "text-slate-500"}`}>
              {e.agent ? `[${e.agent}]` : `·`}
            </span>
            <span className="text-slate-300">{e.message ?? e.kind}</span>
          </div>
        ))
      )}
      <div ref={endRef} />
    </div>
  );
}

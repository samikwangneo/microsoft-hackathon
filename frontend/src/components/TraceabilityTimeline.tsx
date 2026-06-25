import type { TimelineStep } from "../types";

function Dot({ state }: { state: TimelineStep["state"] }) {
  if (state === "pending") {
    return <span className="h-3.5 w-3.5 rounded-full border-2 border-slate-600 bg-canvas" />;
  }
  return (
    <span
      className={`h-3.5 w-3.5 rounded-full ${
        state === "current" ? "bg-brand-soft ring-4 ring-brand/25" : "bg-brand-soft"
      }`}
    />
  );
}

export function TraceabilityTimeline({
  prId,
  steps,
}: {
  prId: number;
  steps: TimelineStep[];
}) {
  return (
    <section className="rounded-2xl border border-edge bg-surface p-6">
      <h3 className="mb-8 text-xs font-semibold uppercase tracking-wider text-slate-400">
        Traceability Timeline — PR #{prId}
      </h3>

      <div className="flex justify-between">
        {steps.map((step, i) => {
          const prevDone = i === 0 || steps[i - 1].state !== "pending";
          return (
            <div key={step.label} className="relative flex flex-1 flex-col items-center text-center">
              {/* connector to previous dot */}
              {i > 0 && (
                <span
                  className={`absolute right-1/2 top-[7px] h-0.5 w-full ${
                    prevDone ? "bg-brand-soft/70" : "bg-slate-700"
                  }`}
                />
              )}
              <div className="relative z-10">
                <Dot state={step.state} />
              </div>
              <p className="mt-3 text-sm font-semibold text-slate-100">{step.label}</p>
              <p className="mt-1 text-xs text-slate-500">{step.timestamp}</p>
              <p className="text-xs text-slate-600">{step.sublabel}</p>
            </div>
          );
        })}
      </div>
    </section>
  );
}

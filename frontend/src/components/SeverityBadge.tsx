import type { Severity } from "../types";

const STYLES: Record<Severity, string> = {
  CRITICAL: "bg-red-500 text-white",
  HIGH: "bg-red-500/15 text-red-400",
  MEDIUM: "bg-amber-500/15 text-amber-400",
  LOW: "text-slate-400",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold tracking-wide ${STYLES[severity]}`}
    >
      {severity}
    </span>
  );
}

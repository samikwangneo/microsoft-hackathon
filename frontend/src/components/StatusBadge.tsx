import type { Status } from "../types";

const STYLES: Record<Status, string> = {
  OPEN: "text-brand-soft font-semibold",
  MERGED: "bg-emerald-500/15 text-emerald-400 px-2 py-0.5 rounded-md font-semibold",
  BLOCKED: "bg-red-500/15 text-red-400 px-2 py-0.5 rounded-md font-semibold",
};

export function StatusBadge({ status }: { status: Status }) {
  return <span className={`inline-flex items-center text-xs ${STYLES[status]}`}>{status}</span>;
}

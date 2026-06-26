import {
  Check,
  ChevronRight,
  FileText,
  GitPullRequest,
  Loader2,
  Package,
  ScanLine,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { RunEvent } from "../types";

type StageState = "pending" | "active" | "done" | "failed";

interface Stage {
  key: string;
  label: string;
  icon: LucideIcon;
  state: StageState;
  detail?: string;
}

function lastRequest(events: RunEvent[], agent: string): string | undefined {
  const reqs = events.filter(
    (e) => e.agent === agent && e.kind === "agent_request_started"
  );
  const last = reqs[reqs.length - 1];
  const data = last?.data as { request?: number; max_requests?: number } | undefined;
  if (data?.request && data?.max_requests) return `req ${data.request}/${data.max_requests}`;
  return undefined;
}

function deriveStages(events: RunEvent[]): Stage[] {
  const seen = (kind: string) => events.some((e) => e.kind === kind);
  const fromAgent = (agent: string) => events.some((e) => e.agent === agent);
  const finished = (agent: string) =>
    events.some((e) => e.kind === "agent_finished" && e.agent === agent);
  const failed = seen("run_failed");
  const complete = seen("run_complete");

  const agentState = (agent: string): StageState => {
    if (finished(agent)) return "done";
    if (fromAgent(agent)) return failed ? "failed" : "active";
    return "pending";
  };

  const scanState: StageState = seen("intake_complete")
    ? "done"
    : seen("run_started")
      ? failed
        ? "failed"
        : "active"
      : "pending";

  const deliverState: StageState = complete
    ? "done"
    : finished("vulnerability") || finished("summary")
      ? failed
        ? "failed"
        : "active"
      : "pending";

  return [
    { key: "scan", label: "Scan", icon: ScanLine, state: scanState, detail: "OSV" },
    {
      key: "summary",
      label: "Summary",
      icon: FileText,
      state: agentState("summary"),
      detail: lastRequest(events, "summary"),
    },
    {
      key: "package",
      label: "Package",
      icon: Package,
      state: agentState("package"),
      detail: lastRequest(events, "package"),
    },
    {
      key: "vulnerability",
      label: "Vuln Fix",
      icon: ShieldCheck,
      state: agentState("vulnerability"),
      detail: lastRequest(events, "vulnerability"),
    },
    { key: "deliver", label: "PR & Email", icon: GitPullRequest, state: deliverState },
  ];
}

const RING: Record<StageState, string> = {
  pending: "border-edge bg-surface-2 text-slate-600",
  active: "border-brand-soft bg-brand/10 text-brand-soft animate-pulse",
  done: "border-emerald-500/50 bg-emerald-500/10 text-emerald-400",
  failed: "border-red-500/50 bg-red-500/10 text-red-400",
};

export function AgentPipeline({ events }: { events: RunEvent[] }) {
  const stages = deriveStages(events);

  return (
    <div className="mb-3 flex items-center gap-1 overflow-x-auto rounded-xl border border-edge bg-canvas/40 p-3">
      {stages.map((stage, i) => {
        const Icon =
          stage.state === "done" ? Check : stage.state === "failed" ? XCircle : stage.icon;
        return (
          <div key={stage.key} className="flex items-center gap-1">
            <div className="flex min-w-[72px] flex-col items-center gap-1.5">
              <div
                className={`flex h-10 w-10 items-center justify-center rounded-xl border ${RING[stage.state]}`}
              >
                {stage.state === "active" ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <Icon size={18} />
                )}
              </div>
              <span
                className={`text-[11px] font-medium ${
                  stage.state === "pending" ? "text-slate-600" : "text-slate-300"
                }`}
              >
                {stage.label}
              </span>
              <span className="h-3 font-mono text-[10px] text-slate-500">
                {stage.state === "active" ? stage.detail ?? "" : ""}
              </span>
            </div>
            {i < stages.length - 1 && (
              <ChevronRight size={16} className="shrink-0 text-slate-700" />
            )}
          </div>
        );
      })}
    </div>
  );
}

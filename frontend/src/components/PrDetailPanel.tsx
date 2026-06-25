import { CheckCircle2, GitBranch, ShieldAlert, XCircle } from "lucide-react";
import type { PullRequest } from "../types";
import { StatusBadge } from "./StatusBadge";

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h4 className="mb-2 text-sm font-semibold text-slate-200">{children}</h4>;
}

export function PrDetailPanel({ pr }: { pr: PullRequest }) {
  const { detail } = pr;
  return (
    <aside className="flex flex-col rounded-2xl border border-edge bg-surface p-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-xl font-bold text-white">PR #{pr.id}</h3>
        <StatusBadge status={pr.status} />
      </div>

      <div className="mt-3 inline-flex w-fit items-center gap-1.5 rounded-md bg-surface-2 px-2.5 py-1 text-xs text-slate-300 ring-1 ring-edge">
        <GitBranch size={13} className="text-slate-500" />
        {detail.branch}
      </div>

      <div className="my-4 border-t border-edge" />

      {/* Why this PR exists */}
      <SectionTitle>
        <span className="flex items-center gap-1.5">
          <ShieldAlert size={15} className="text-red-400" />
          Why this PR exists
        </span>
      </SectionTitle>
      <span className="mb-2 inline-flex w-fit items-center rounded-md bg-violet-600/90 px-2.5 py-1 font-mono text-xs font-medium text-white">
        {detail.why.osv_id}
      </span>
      <p className="text-sm leading-relaxed text-slate-400">{detail.why.text}</p>

      {/* Change summary */}
      <div className="mt-5">
        <SectionTitle>Change Summary</SectionTitle>
        <ul className="space-y-1.5">
          {detail.change_summary.map((item) => (
            <li key={item} className="flex items-center gap-2 text-sm text-slate-300">
              <CheckCircle2 size={15} className="shrink-0 text-emerald-400" />
              {item}
            </li>
          ))}
        </ul>
      </div>

      {/* Files changed */}
      <div className="mt-5">
        <SectionTitle>Files Changed ({detail.files_changed.length})</SectionTitle>
        <div className="flex flex-wrap gap-2">
          {detail.files_changed.map((f) => (
            <span
              key={f}
              className="rounded-md bg-surface-2 px-2 py-1 font-mono text-xs text-slate-300 ring-1 ring-edge"
            >
              {f}
            </span>
          ))}
        </div>
      </div>

      {/* Validation checks */}
      <div className="mt-5">
        <SectionTitle>Validation Checks</SectionTitle>
        <ul className="space-y-2">
          {detail.validation_checks.map((c) => (
            <li key={c.label} className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-2 text-slate-300">
                {c.ok ? (
                  <CheckCircle2 size={15} className="text-emerald-400" />
                ) : (
                  <XCircle size={15} className="text-red-400" />
                )}
                {c.label}
              </span>
              <span className={c.ok ? "text-emerald-400" : "text-red-400"}>{c.status}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Actions */}
      <div className="mt-6 flex gap-3">
        <a
          href={detail.pr_url}
          target="_blank"
          rel="noreferrer"
          className="flex-1 rounded-lg bg-brand px-4 py-2.5 text-center text-sm font-semibold text-white transition-colors hover:bg-blue-500"
        >
          Open PR
        </a>
        <button className="flex-1 rounded-lg border border-edge px-4 py-2.5 text-center text-sm font-semibold text-slate-200 transition-colors hover:bg-white/5">
          View Diff
        </button>
      </div>
    </aside>
  );
}

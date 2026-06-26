import { useState } from "react";
import { CheckCircle2, ExternalLink, GitBranch, ShieldAlert, XCircle } from "lucide-react";
import type { PullRequest } from "../types";
import { StatusBadge } from "./StatusBadge";
import { DiffModal } from "./DiffModal";

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h4 className="mb-2 text-sm font-semibold text-slate-200">{children}</h4>;
}

/** Link an OSV / GHSA / CVE identifier to its advisory page. */
function advisoryUrl(id: string): string {
  return id.toUpperCase().startsWith("CVE-")
    ? `https://nvd.nist.gov/vuln/detail/${id}`
    : `https://osv.dev/vulnerability/${id}`;
}

export function PrDetailPanel({ pr }: { pr: PullRequest }) {
  const { detail } = pr;
  const [showDiff, setShowDiff] = useState(false);
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
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <a
          href={advisoryUrl(detail.why.osv_id)}
          target="_blank"
          rel="noreferrer"
          className="inline-flex w-fit items-center gap-1 rounded-md bg-violet-600/90 px-2.5 py-1 font-mono text-xs font-medium text-white transition-colors hover:bg-violet-500"
        >
          {detail.why.osv_id}
          <ExternalLink size={11} />
        </a>
        {detail.why.cve && detail.why.cve !== detail.why.osv_id && (
          <a
            href={advisoryUrl(detail.why.cve)}
            target="_blank"
            rel="noreferrer"
            className="inline-flex w-fit items-center gap-1 rounded-md bg-surface-2 px-2.5 py-1 font-mono text-xs font-medium text-slate-300 ring-1 ring-edge transition-colors hover:text-white"
          >
            {detail.why.cve}
            <ExternalLink size={11} />
          </a>
        )}
      </div>
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
        <button
          onClick={() => setShowDiff(true)}
          disabled={!detail.diff}
          className="flex-1 rounded-lg border border-edge px-4 py-2.5 text-center text-sm font-semibold text-slate-200 transition-colors hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-40"
        >
          View Diff
        </button>
      </div>

      {showDiff && (
        <DiffModal
          title={`PR #${pr.id} · ${pr.package.name}`}
          diff={detail.diff}
          onClose={() => setShowDiff(false)}
        />
      )}
    </aside>
  );
}

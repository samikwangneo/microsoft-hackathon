import { Download, User } from "lucide-react";
import type { PullRequest } from "../types";
import { SeverityBadge } from "./SeverityBadge";
import { StatusBadge } from "./StatusBadge";
import { PackageChip } from "./PackageChip";

interface Props {
  pullRequests: PullRequest[];
  totalPrs: number;
  selectedId: number | null;
  onSelect: (id: number) => void;
  onExport: () => void;
}

const COLS = ["PR", "REPO", "SEVERITY", "STATUS", "ASSIGNED TO", "CREATED", "PACKAGE AFFECTED"];

export function PullRequestTable({
  pullRequests,
  totalPrs,
  selectedId,
  onSelect,
  onExport,
}: Props) {
  return (
    <section className="rounded-2xl border border-edge bg-surface">
      <div className="flex items-center justify-between px-5 py-4">
        <div className="flex items-center gap-3">
          <h2 className="text-xl font-bold text-white">Pull Requests</h2>
          <span className="rounded-md bg-surface-2 px-2 py-0.5 text-xs font-medium text-slate-400 ring-1 ring-edge">
            {totalPrs} total
          </span>
        </div>
        <button
          onClick={onExport}
          className="flex items-center gap-1.5 text-sm font-medium text-brand-soft transition-colors hover:text-blue-300"
        >
          <Download size={15} />
          Export CSV
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-y border-edge text-[11px] uppercase tracking-wider text-slate-500">
              {COLS.map((c) => (
                <th key={c} className="px-5 py-3 font-medium">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pullRequests.map((pr) => {
              const selected = pr.id === selectedId;
              return (
                <tr
                  key={pr.id}
                  onClick={() => onSelect(pr.id)}
                  className={`cursor-pointer border-b border-edge/60 transition-colors ${
                    selected ? "bg-brand/10" : "hover:bg-white/[0.03]"
                  }`}
                >
                  <td className="relative px-5 py-4 font-mono text-brand-soft">
                    {selected && (
                      <span className="absolute inset-y-0 left-0 w-0.5 bg-brand-soft" />
                    )}
                    #{pr.id}
                  </td>
                  <td className="px-5 py-4 text-slate-200">{pr.repo}</td>
                  <td className="px-5 py-4">
                    <SeverityBadge severity={pr.severity} />
                  </td>
                  <td className="px-5 py-4">
                    <StatusBadge status={pr.status} />
                  </td>
                  <td className="px-5 py-4">
                    <span className="inline-flex items-center gap-1.5 text-slate-300">
                      <User size={14} className="text-slate-500" />
                      {pr.assigned_to}
                    </span>
                  </td>
                  <td className="px-5 py-4 text-slate-400">{pr.created_relative}</td>
                  <td className="px-5 py-4">
                    <PackageChip pkg={pr.package} />
                  </td>
                </tr>
              );
            })}
            {pullRequests.length === 0 && (
              <tr>
                <td colSpan={COLS.length} className="px-5 py-10 text-center text-slate-500">
                  No pull requests match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

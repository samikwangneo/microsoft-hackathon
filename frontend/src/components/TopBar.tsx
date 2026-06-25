import { Bell, Calendar, Shield } from "lucide-react";
import { FilterPill } from "./FilterPill";

interface TopBarProps {
  repos: string[];
  severities: string[];
  repoFilter: string;
  severityFilter: string;
  onRepoChange: (v: string) => void;
  onSeverityChange: (v: string) => void;
}

export function TopBar({
  repos,
  severities,
  repoFilter,
  severityFilter,
  onRepoChange,
  onSeverityChange,
}: TopBarProps) {
  return (
    <header className="flex flex-wrap items-center justify-between gap-4">
      {/* Brand */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand">
          <Shield size={22} className="text-white" fill="white" strokeWidth={1.5} />
        </div>
        <div>
          <h1 className="text-lg font-bold leading-tight text-white">Sentinel</h1>
          <p className="text-xs text-slate-500">Security Dashboard</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <FilterPill label="Repo" value={repoFilter} options={repos} onChange={onRepoChange} />
        <FilterPill
          label="Severity"
          value={severityFilter}
          options={severities}
          onChange={onSeverityChange}
        />
        <button className="flex items-center gap-2 rounded-full border border-edge bg-surface px-4 py-2 text-sm text-slate-300">
          <Calendar size={15} className="text-slate-500" />
          <span className="font-medium text-slate-100">Last 7 days</span>
        </button>
      </div>

      {/* Right cluster */}
      <div className="flex items-center gap-4">
        <button className="relative text-slate-400 transition-colors hover:text-slate-200">
          <Bell size={20} />
          <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-brand-soft ring-2 ring-canvas" />
        </button>
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-surface-2 text-xs font-semibold text-slate-200 ring-1 ring-edge">
            JD
          </div>
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
        </div>
      </div>
    </header>
  );
}

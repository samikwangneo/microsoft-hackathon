import { ArrowUp, Zap } from "lucide-react";
import type { Kpis } from "../types";
import { DonutRing } from "./DonutRing";

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-edge bg-surface p-5">{children}</div>
  );
}

function Delta({ pct }: { pct: number }) {
  return (
    <span className="inline-flex items-center gap-0.5 text-sm font-medium text-emerald-400">
      <ArrowUp size={14} />
      {pct}%
    </span>
  );
}

export function KpiCards({ kpis }: { kpis: Kpis }) {
  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
      <Card>
        <p className="text-sm text-slate-400">Alerts Matched</p>
        <div className="mt-3 flex items-end gap-2">
          <span className="text-4xl font-bold text-white">{kpis.alerts_matched.value}</span>
          <Delta pct={kpis.alerts_matched.delta_pct} />
        </div>
        <p className="mt-2 text-sm text-slate-500">{kpis.alerts_matched.caption}</p>
      </Card>

      <Card>
        <p className="text-sm text-slate-400">PRs Generated</p>
        <div className="mt-3 flex items-end gap-2">
          <span className="text-4xl font-bold text-white">{kpis.prs_generated.value}</span>
          <Delta pct={kpis.prs_generated.delta_pct} />
        </div>
        <p className="mt-2 text-sm text-slate-500">{kpis.prs_generated.caption}</p>
      </Card>

      <Card>
        <div className="flex items-start justify-between">
          <p className="text-sm text-slate-400">Merge Rate</p>
          <DonutRing percent={kpis.merge_rate.percent} />
        </div>
        <div className="mt-1 text-4xl font-bold text-white">{kpis.merge_rate.percent}%</div>
        <p className="mt-2 text-sm text-slate-500">{kpis.merge_rate.caption}</p>
      </Card>

      <Card>
        <div className="flex items-start justify-between">
          <p className="text-sm text-slate-400">Median Alert-to-PR</p>
          <Zap size={18} className="text-brand-soft" fill="currentColor" />
        </div>
        <div className="mt-3 text-4xl font-bold text-white">{kpis.median_alert_to_pr.value}</div>
        <p className="mt-2 text-sm text-slate-500">{kpis.median_alert_to_pr.caption}</p>
      </Card>
    </div>
  );
}

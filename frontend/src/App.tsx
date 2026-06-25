import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import type { DashboardPayload, Severity } from "./types";
import { fetchDashboard } from "./lib/api";
import { downloadFile, prsToCsv } from "./lib/format";
import { TopBar } from "./components/TopBar";
import { KpiCards } from "./components/KpiCards";
import { PullRequestTable } from "./components/PullRequestTable";
import { PrDetailPanel } from "./components/PrDetailPanel";
import { TraceabilityTimeline } from "./components/TraceabilityTimeline";

const SEVERITIES: (Severity | "All")[] = ["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"];

export default function App() {
  const [payload, setPayload] = useState<DashboardPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [repoFilter, setRepoFilter] = useState("All Repos");
  const [severityFilter, setSeverityFilter] = useState("All");

  useEffect(() => {
    const ctrl = new AbortController();
    fetchDashboard(ctrl.signal)
      .then((data) => {
        setPayload(data);
        setSelectedId(data.pull_requests[0]?.id ?? null);
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => ctrl.abort();
  }, []);

  const filtered = useMemo(() => {
    if (!payload) return [];
    return payload.pull_requests.filter((pr) => {
      const repoOk = repoFilter === "All Repos" || pr.repo === repoFilter;
      const sevOk = severityFilter === "All" || pr.severity === severityFilter;
      return repoOk && sevOk;
    });
  }, [payload, repoFilter, severityFilter]);

  // Keep a valid selection as filters change.
  useEffect(() => {
    if (filtered.length && !filtered.some((pr) => pr.id === selectedId)) {
      setSelectedId(filtered[0].id);
    }
  }, [filtered, selectedId]);

  if (error) {
    return (
      <Centered>
        <AlertTriangle className="text-amber-400" size={36} />
        <p className="mt-4 text-lg font-semibold text-slate-100">Couldn’t reach the backend</p>
        <p className="mt-1 max-w-md text-center text-sm text-slate-400">{error}</p>
        <p className="mt-4 text-center text-sm text-slate-500">
          Start it with{" "}
          <code className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-slate-300">
            uvicorn app.main:app --reload
          </code>{" "}
          in <span className="font-mono">backend/</span>.
        </p>
      </Centered>
    );
  }

  if (!payload) {
    return (
      <Centered>
        <Loader2 className="animate-spin text-brand-soft" size={32} />
        <p className="mt-4 text-sm text-slate-400">Loading dashboard…</p>
      </Centered>
    );
  }

  const selected = payload.pull_requests.find((pr) => pr.id === selectedId) ?? null;

  return (
    <div className="mx-auto max-w-[1500px] px-6 py-6 lg:px-10">
      <TopBar
        repos={["All Repos", ...payload.repos]}
        severities={SEVERITIES}
        repoFilter={repoFilter}
        severityFilter={severityFilter}
        onRepoChange={setRepoFilter}
        onSeverityChange={setSeverityFilter}
      />

      <div className="mt-7">
        <KpiCards kpis={payload.kpis} />
      </div>

      <div className="mt-7 grid grid-cols-1 gap-6 xl:grid-cols-[1fr_400px]">
        <PullRequestTable
          pullRequests={filtered}
          totalPrs={payload.total_prs}
          selectedId={selectedId}
          onSelect={setSelectedId}
          onExport={() => downloadFile("pull-requests.csv", prsToCsv(filtered))}
        />
        {selected && <PrDetailPanel pr={selected} />}
      </div>

      {selected && (
        <div className="mt-6">
          <TraceabilityTimeline prId={selected.id} steps={selected.timeline} />
        </div>
      )}
    </div>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-full min-h-screen flex-col items-center justify-center px-6">
      {children}
    </div>
  );
}

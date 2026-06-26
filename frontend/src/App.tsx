import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, Loader2, X } from "lucide-react";
import type { DashboardPayload, RunEvent, RunRequest, Severity } from "./types";
import { fetchDashboard, startRun, subscribeRunEvents } from "./lib/api";
import { downloadFile, prsToCsv } from "./lib/format";
import { TopBar } from "./components/TopBar";
import { KpiCards } from "./components/KpiCards";
import { RunPanel } from "./components/RunPanel";
import { PullRequestTable } from "./components/PullRequestTable";
import { PrDetailPanel } from "./components/PrDetailPanel";
import { TraceabilityTimeline } from "./components/TraceabilityTimeline";
import { Confetti } from "./components/Confetti";

const SEVERITIES: (Severity | "All")[] = ["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"];

export default function App() {
  const [payload, setPayload] = useState<DashboardPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [repoFilter, setRepoFilter] = useState("All Repos");
  const [severityFilter, setSeverityFilter] = useState("All");

  // Remediation run (live SSE)
  const [running, setRunning] = useState(false);
  const [runStatus, setRunStatus] = useState<string | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [runEvents, setRunEvents] = useState<RunEvent[]>([]);
  const [celebrate, setCelebrate] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const refetchDashboard = useCallback(async () => {
    try {
      const data = await fetchDashboard();
      setPayload(data);
      setSelectedId(data.pull_requests[0]?.id ?? null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  const handleRun = useCallback(
    async (req: RunRequest) => {
      setRunError(null);
      setRunEvents([]);
      setRunStatus("starting");
      try {
        const runId = await startRun(req);
        setRunning(true);
        setRunStatus("running");
        subscribeRunEvents(
          runId,
          (e) => setRunEvents((prev) => [...prev, e]),
          (status) => {
            setRunning(false);
            setRunStatus(status);
            void refetchDashboard();
            if (status === "completed") {
              setCelebrate(true);
              setToast("Remediation complete — pull request opened");
              window.setTimeout(() => setCelebrate(false), 2800);
              window.setTimeout(() => setToast(null), 6000);
            }
          }
        );
      } catch (e) {
        setRunning(false);
        setRunStatus("failed");
        setRunError((e as Error).message);
      }
    },
    [refetchDashboard]
  );

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

      <div className="mt-7">
        <RunPanel
          running={running}
          status={runStatus}
          error={runError}
          events={runEvents}
          onRun={handleRun}
        />
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

      {celebrate && <Confetti />}

      {toast && (
        <div className="fixed bottom-6 right-6 z-[70] flex items-center gap-3 rounded-xl border border-emerald-500/30 bg-surface px-4 py-3 shadow-2xl">
          <CheckCircle2 size={20} className="shrink-0 text-emerald-400" />
          <span className="text-sm font-medium text-slate-100">{toast}</span>
          <button
            onClick={() => setToast(null)}
            className="rounded-md p-0.5 text-slate-500 transition-colors hover:text-white"
            aria-label="Dismiss"
          >
            <X size={16} />
          </button>
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

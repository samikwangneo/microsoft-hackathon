import { useState } from "react";
import { Loader2, Play } from "lucide-react";
import type { RunEvent, RunRequest } from "../types";
import { ActivityFeed } from "./ActivityFeed";
import { AgentPipeline } from "./AgentPipeline";

interface RunPanelProps {
  running: boolean;
  status: string | null;
  error: string | null;
  events: RunEvent[];
  onRun: (req: RunRequest) => void;
}

export function RunPanel({ running, status, error, events, onRun }: RunPanelProps) {
  const [repoPath, setRepoPath] = useState("");
  const [manifest, setManifest] = useState("package.json");
  const [email, setEmail] = useState("");

  const canRun = repoPath.trim() && email.trim() && !running;

  return (
    <section className="rounded-2xl border border-edge bg-surface p-5">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-white">Run remediation</h2>
        {status && (
          <span className="text-xs font-medium text-slate-400">
            status: <span className="text-brand-soft">{status}</span>
          </span>
        )}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-[1fr_180px_1fr_auto]">
        <Field label="Repo path" value={repoPath} onChange={setRepoPath}
               placeholder="/path/to/local/checkout" disabled={running} />
        <Field label="Manifest" value={manifest} onChange={setManifest}
               placeholder="package.json" disabled={running} />
        <Field label="Notify email" value={email} onChange={setEmail}
               placeholder="you@example.com" disabled={running} />
        <div className="flex items-end">
          <button
            onClick={() =>
              onRun({ repo_path: repoPath.trim(), package_source_file: manifest.trim(), email: email.trim() })
            }
            disabled={!canRun}
            className="flex h-[42px] w-full items-center justify-center gap-2 rounded-lg bg-brand px-5 text-sm font-semibold text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-40 md:w-auto"
          >
            {running ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
            {running ? "Running…" : "Run"}
          </button>
        </div>
      </div>

      {error && <p className="mt-3 text-sm text-red-400">{error}</p>}

      {(running || events.length > 0) && (
        <div className="mt-4">
          <AgentPipeline events={events} />
          <ActivityFeed events={events} />
        </div>
      )}
    </section>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  disabled,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  disabled: boolean;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs text-slate-500">{label}</span>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className="rounded-lg border border-edge bg-canvas px-3 py-2 text-sm text-slate-100 placeholder:text-slate-600 focus:border-brand-soft focus:outline-none disabled:opacity-50"
      />
    </label>
  );
}

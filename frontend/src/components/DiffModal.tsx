import { useEffect } from "react";
import { X } from "lucide-react";

function lineClass(line: string): string {
  if (line.startsWith("+++") || line.startsWith("---") || line.startsWith("diff "))
    return "text-slate-500";
  if (line.startsWith("@@")) return "text-cyan-400";
  if (line.startsWith("+")) return "bg-emerald-500/10 text-emerald-300";
  if (line.startsWith("-")) return "bg-red-500/10 text-red-300";
  return "text-slate-400";
}

export function DiffModal({
  title,
  diff,
  onClose,
}: {
  title: string;
  diff: string;
  onClose: () => void;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const lines = diff.split("\n");

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="flex max-h-[80vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-edge bg-surface shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-edge px-5 py-3">
          <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-slate-400 transition-colors hover:bg-white/5 hover:text-white"
            aria-label="Close diff"
          >
            <X size={18} />
          </button>
        </div>
        <div className="overflow-auto bg-canvas/60 px-4 py-3 font-mono text-xs leading-relaxed">
          {diff.trim() ? (
            lines.map((line, i) => (
              <pre key={i} className={`whitespace-pre-wrap px-1 ${lineClass(line)}`}>
                {line || " "}
              </pre>
            ))
          ) : (
            <p className="text-slate-500">No diff available for this PR.</p>
          )}
        </div>
      </div>
    </div>
  );
}

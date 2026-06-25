import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";

interface FilterPillProps {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
  icon?: React.ReactNode;
}

/** A pill-shaped dropdown like the Repo / Severity filters in the design. */
export function FilterPill({ label, value, options, onChange, icon }: FilterPillProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-full border border-edge bg-surface px-4 py-2 text-sm text-slate-300 transition-colors hover:border-slate-600"
      >
        {icon}
        <span className="text-slate-500">{label}:</span>
        <span className="font-medium text-slate-100">{value}</span>
        <ChevronDown size={15} className="text-slate-500" />
      </button>

      {open && (
        <div className="absolute z-20 mt-2 min-w-[180px] overflow-hidden rounded-lg border border-edge bg-surface-2 py-1 shadow-xl shadow-black/40">
          {options.map((opt) => (
            <button
              key={opt}
              onClick={() => {
                onChange(opt);
                setOpen(false);
              }}
              className={`block w-full px-4 py-2 text-left text-sm transition-colors hover:bg-white/5 ${
                opt === value ? "text-brand-soft" : "text-slate-300"
              }`}
            >
              {opt}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

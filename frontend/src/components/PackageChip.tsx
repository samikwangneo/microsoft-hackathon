import { Package } from "lucide-react";
import type { AffectedPackage } from "../types";

export function PackageChip({ pkg }: { pkg: AffectedPackage }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md bg-surface-2 px-2 py-1 font-mono text-xs text-slate-300 ring-1 ring-edge">
      <Package size={12} className="text-brand-soft" />
      {pkg.name}@{pkg.spec}
    </span>
  );
}

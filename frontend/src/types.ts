// Mirrors backend/app/dashboard/models.py (snake_case, as emitted by FastAPI).

export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
export type Status = "OPEN" | "MERGED" | "BLOCKED";
export type StepState = "done" | "current" | "pending";

export interface DeltaStat {
  value: number;
  delta_pct: number;
  caption: string;
}
export interface PercentStat {
  percent: number;
  caption: string;
}
export interface TextStat {
  value: string;
  caption: string;
}

export interface Kpis {
  alerts_matched: DeltaStat;
  prs_generated: DeltaStat;
  merge_rate: PercentStat;
  median_alert_to_pr: TextStat;
}

export interface AffectedPackage {
  name: string;
  spec: string;
}
export interface WhyThisPr {
  osv_id: string;
  cve: string;
  text: string;
}
export interface ValidationCheck {
  label: string;
  status: string;
  ok: boolean;
}
export interface PrDetail {
  branch: string;
  why: WhyThisPr;
  change_summary: string[];
  files_changed: string[];
  validation_checks: ValidationCheck[];
  pr_url: string;
}
export interface TimelineStep {
  label: string;
  timestamp: string;
  sublabel: string;
  state: StepState;
}
export interface PullRequest {
  id: number;
  repo: string;
  severity: Severity;
  status: Status;
  assigned_to: string;
  created_relative: string;
  package: AffectedPackage;
  detail: PrDetail;
  timeline: TimelineStep[];
}

export interface DashboardPayload {
  kpis: Kpis;
  total_prs: number;
  repos: string[];
  pull_requests: PullRequest[];
}

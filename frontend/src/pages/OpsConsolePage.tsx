import { Activity, Workflow } from "lucide-react";
import { FormEvent } from "react";

import { StatusPill } from "../components/StatusPill";
import { type DashboardData, type IncidentFeedItem, type ObservabilitySnapshot, type RunResponse } from "../lib/api";

type OpsConsolePageProps = {
  requestText: string;
  preferredTool: string;
  setRequestText: (value: string) => void;
  setPreferredTool: (value: string) => void;
  onRun: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  loading: boolean;
  runResult: RunResponse | null;
  observability: ObservabilitySnapshot | null;
  dashboard: DashboardData | null;
  incidentFeed: IncidentFeedItem[];
};

export function OpsConsolePage({
  requestText,
  preferredTool,
  setRequestText,
  setPreferredTool,
  onRun,
  loading,
  runResult,
  observability,
  dashboard,
  incidentFeed
}: OpsConsolePageProps): JSX.Element {
  return (
    <section className="grid grid-cols-12 gap-4">
      <article className="panel col-span-12 xl:col-span-8">
        <h2 className="panel-title">
          <Workflow size={16} />
          Request to Decision to Outcome
        </h2>
        <form onSubmit={onRun} className="mt-3 space-y-3">
          <textarea className="field-input min-h-28" value={requestText} onChange={(event) => setRequestText(event.target.value)} />
          <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
            <input className="field-input" value={preferredTool} onChange={(event) => setPreferredTool(event.target.value)} placeholder="preferred tool (optional)" />
            <button className="btn-primary" type="submit" disabled={loading}>
              Run Decision
            </button>
          </div>
        </form>

        {runResult ? (
          <div className="mt-4 space-y-3">
            <div className="decision-banner-grid rounded-lg border border-border bg-panel p-3">
              <div>
                <p className="decision-label">Request</p>
                <p className="decision-value font-mono">{runResult.request_id.slice(0, 8)}</p>
              </div>
              <div>
                <p className="decision-label">Intent</p>
                <p className="decision-value">{runResult.intent}</p>
              </div>
              <div>
                <p className="decision-label">Route</p>
                <p className="decision-value">{runResult.route}</p>
              </div>
              <div>
                <p className="decision-label">Risk</p>
                <p className={`risk-badge risk-${runResult.risk}`}>{runResult.risk}</p>
              </div>
              <div>
                <p className="decision-label">Policy</p>
                <p className="decision-value">{runResult.policy.allowed ? "allow" : "block"}</p>
              </div>
              <div>
                <p className="decision-label">Tool</p>
                <p className="decision-value safe-wrap">{String(runResult.tool_results.tool ?? "none")}</p>
              </div>
            </div>
            <div className="rounded-lg border border-border bg-panel p-3">
              <p className="mb-2 text-xs font-semibold tracking-wide text-muted">Policy Explainability</p>
              <p className="text-sm safe-wrap">{runResult.policy.reason}</p>
              {runResult.policy.blocked_rules.length > 0 ? (
                <ul className="mt-2 list-disc pl-4 text-xs">
                  {runResult.policy.blocked_rules.map((rule) => (
                    <li key={rule} className="safe-wrap">
                      {rule}
                    </li>
                  ))}
                </ul>
              ) : null}
              <details className="mt-2">
                <summary className="cursor-pointer text-xs font-semibold">Raw structured output</summary>
                <pre className="mt-2 max-h-56 overflow-auto text-[11px]">{JSON.stringify(runResult, null, 2)}</pre>
              </details>
            </div>
          </div>
        ) : null}
      </article>

      <article className="panel col-span-12 xl:col-span-4">
        <h2 className="panel-title">
          <Activity size={16} />
          Live Safety KPIs
        </h2>
        <div className="mt-3 grid grid-cols-2 gap-3">
          <div className="kpi-card">
            <p className="kpi-label">P95 ms</p>
            <p className="kpi-value">{observability?.latency_percentiles_ms.p95 ?? 0}</p>
          </div>
          <div className="kpi-card">
            <p className="kpi-label">Incidents</p>
            <p className="kpi-value">{dashboard?.incident_summary.total_incidents ?? 0}</p>
          </div>
          <div className="kpi-card">
            <p className="kpi-label">Fallback/h</p>
            <p className="kpi-value">{observability?.fallback_frequency_trend.at(-1)?.fallback_requests ?? 0}</p>
          </div>
          <div className="kpi-card">
            <p className="kpi-label">Open</p>
            <p className="kpi-value">{incidentFeed.filter((item) => item.status === "open").length}</p>
          </div>
        </div>
        {runResult ? (
          <div className="mt-3 flex flex-wrap gap-2">
            <StatusPill label={runResult.status} tone={runResult.status === "success" ? "ok" : "warn"} />
            <StatusPill label={`fallback:${runResult.fallback_used ? "yes" : "no"}`} tone={runResult.fallback_used ? "warn" : "ok"} />
          </div>
        ) : null}
      </article>
    </section>
  );
}

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertOctagon,
  BarChart3,
  CircleSlash2,
  Database,
  Gauge,
  ListChecks,
  Play,
  RefreshCw,
  ShieldCheck,
  Trash2,
  Wrench
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import {
  fetchDashboard,
  fetchIncidentDetail,
  fetchIncidentFeed,
  fetchPolicies,
  resetApplicationState,
  runAgent,
  type DashboardData,
  type IncidentDetail,
  type IncidentFeedItem,
  type ResetResponse,
  type RunResponse
} from "./lib/api";
import { ThemeToggle } from "./components/ThemeToggle";
import { StatusPill } from "./components/StatusPill";

type Theme = "light" | "dark";

function readInitialTheme(): Theme {
  if (typeof window === "undefined") {
    return "light";
  }
  const saved = localStorage.getItem("agent-ui-theme");
  if (saved === "light" || saved === "dark") {
    return saved;
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function shortId(requestId: string): string {
  return requestId.slice(0, 8);
}

export default function App(): JSX.Element {
  const [theme, setTheme] = useState<Theme>(readInitialTheme);
  const [text, setText] = useState("calculate 16 * 4");
  const [preferredTool, setPreferredTool] = useState("");
  const [runLoading, setRunLoading] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [runResult, setRunResult] = useState<RunResponse | null>(null);
  const [policies, setPolicies] = useState<Record<string, unknown> | null>(null);
  const [policyLoading, setPolicyLoading] = useState(false);
  const [policyError, setPolicyError] = useState<string | null>(null);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const [incidentFeed, setIncidentFeed] = useState<IncidentFeedItem[]>([]);
  const [incidentFeedLoading, setIncidentFeedLoading] = useState(false);
  const [incidentFeedError, setIncidentFeedError] = useState<string | null>(null);
  const [selectedRequestId, setSelectedRequestId] = useState<string | null>(null);
  const [incidentDetail, setIncidentDetail] = useState<IncidentDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [resetLoading, setResetLoading] = useState(false);
  const [resetError, setResetError] = useState<string | null>(null);
  const [resetSummary, setResetSummary] = useState<ResetResponse | null>(null);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", theme === "dark");
    localStorage.setItem("agent-ui-theme", theme);
  }, [theme]);

  async function loadPolicies(): Promise<void> {
    setPolicyLoading(true);
    setPolicyError(null);
    try {
      const data = await fetchPolicies();
      setPolicies(data);
    } catch (error) {
      setPolicyError((error as Error).message);
    } finally {
      setPolicyLoading(false);
    }
  }

  async function loadDashboard(): Promise<void> {
    setDashboardLoading(true);
    setDashboardError(null);
    try {
      const data = await fetchDashboard();
      setDashboard(data);
    } catch (error) {
      setDashboardError((error as Error).message);
    } finally {
      setDashboardLoading(false);
    }
  }

  async function loadIncidentFeed(): Promise<void> {
    setIncidentFeedLoading(true);
    setIncidentFeedError(null);
    try {
      const data = await fetchIncidentFeed(50);
      setIncidentFeed(data.items);
      if (!selectedRequestId && data.items.length > 0) {
        const requestId = data.items[0].request_id;
        setSelectedRequestId(requestId);
        await loadIncidentDetail(requestId);
      }
    } catch (error) {
      setIncidentFeedError((error as Error).message);
    } finally {
      setIncidentFeedLoading(false);
    }
  }

  async function loadIncidentDetail(requestId: string): Promise<void> {
    setDetailLoading(true);
    setDetailError(null);
    try {
      const data = await fetchIncidentDetail(requestId);
      setIncidentDetail(data);
      setSelectedRequestId(requestId);
    } catch (error) {
      setDetailError((error as Error).message);
    } finally {
      setDetailLoading(false);
    }
  }

  async function refreshObservability(): Promise<void> {
    await Promise.all([loadDashboard(), loadIncidentFeed()]);
  }

  useEffect(() => {
    void loadPolicies();
    void refreshObservability();
  }, []);

  async function onSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setRunLoading(true);
    setRunError(null);
    try {
      const payload = {
        text,
        ...(preferredTool.trim() ? { preferred_tool: preferredTool.trim() } : {})
      };
      const data = await runAgent(payload);
      setRunResult(data);
      await refreshObservability();
    } catch (error) {
      setRunError((error as Error).message);
    } finally {
      setRunLoading(false);
    }
  }

  async function onReset(): Promise<void> {
    const confirmed = window.confirm("Reset all current data? This will clear incidents, metrics files, and task mock state.");
    if (!confirmed) {
      return;
    }
    setResetLoading(true);
    setResetError(null);
    try {
      const result = await resetApplicationState();
      setResetSummary(result);
      setRunResult(null);
      setRunError(null);
      setIncidentDetail(null);
      setSelectedRequestId(null);
      setIncidentFeed([]);
      await refreshObservability();
    } catch (error) {
      setResetError((error as Error).message);
    } finally {
      setResetLoading(false);
    }
  }

  const resultTone = useMemo(() => {
    if (!runResult) {
      return "neutral";
    }
    return runResult.status === "success" ? "ok" : "warn";
  }, [runResult]);

  const summaryMetrics = dashboard?.metrics_summary ?? {};
  const incidentSummary = dashboard?.incident_summary;
  const taskSuccessRate = Number(summaryMetrics.task_success_rate ?? 0);
  const fallbackActivationRate = Number(summaryMetrics.fallback_activation_rate ?? 0);
  const blockedUnsafeActions = Number(summaryMetrics.blocked_unsafe_actions_count ?? 0);
  const precisionProxy = Number(summaryMetrics.policy_precision_proxy ?? 0);

  const performanceData = useMemo(() => {
    return (dashboard?.performance_24h ?? []).map((point) => ({
      ...point,
      hourLabel: point.hour.slice(11, 16)
    }));
  }, [dashboard]);

  return (
    <div className="min-h-screen bg-surface text-ink transition-colors">
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="blob blob-a" />
        <div className="blob blob-b" />
      </div>
      <main className="relative mx-auto w-full max-w-7xl px-4 pb-8 pt-6 sm:px-6 lg:px-8">
        <header className="mb-6 flex items-start justify-between gap-4">
          <div>
            <p className="mb-2 inline-flex items-center gap-2 rounded-full border border-bluecore-300/80 bg-bluecore-100/60 px-3 py-1 text-xs font-semibold tracking-wide text-bluecore-900 dark:border-bluecore-700/70 dark:bg-bluecore-900/50 dark:text-bluecore-100">
              <ShieldCheck size={14} />
              Agent Guardrails Console
            </p>
            <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
              Safe Routing, Policy Decisions, and Incident Visibility
            </h1>
          </div>
          <div className="flex items-center">
            <button type="button" className="btn-danger mr-2" onClick={() => void onReset()} disabled={resetLoading}>
              <Trash2 size={14} />
              {resetLoading ? "Resetting..." : "Reset Data"}
            </button>
            <ThemeToggle theme={theme} onToggle={() => setTheme((prev) => (prev === "dark" ? "light" : "dark"))} />
          </div>
        </header>
        {resetError ? (
          <div className="mb-4 rounded-xl border border-red-300/70 bg-red-100/60 p-3 text-sm text-red-900 dark:border-red-500/50 dark:bg-red-900/40 dark:text-red-100">
            {resetError}
          </div>
        ) : null}
        {resetSummary ? (
          <div className="mb-4 rounded-xl border border-bluecore-300/70 bg-bluecore-100/60 p-3 text-sm text-bluecore-900 dark:border-bluecore-700/70 dark:bg-bluecore-900/45 dark:text-bluecore-100">
            Reset complete. Cleared {resetSummary.telemetry_deleted_events} telemetry events and {resetSummary.tasks_cleared} task records.
          </div>
        ) : null}

        <section className="grid gap-4 lg:grid-cols-3">
          <article className="panel lg:col-span-2">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="panel-title">
                <Play size={16} />
                Run Request
              </h2>
            </div>
            <form onSubmit={onSubmit} className="space-y-3">
              <label className="field-label" htmlFor="request-text">
                User request
              </label>
              <textarea
                id="request-text"
                value={text}
                onChange={(event) => setText(event.target.value)}
                rows={4}
                className="field-input min-h-28"
                placeholder="Ask for retrieval, tool use, or a direct answer..."
              />
              <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
                <div>
                  <label className="field-label" htmlFor="preferred-tool">
                    Preferred tool (optional)
                  </label>
                  <input
                    id="preferred-tool"
                    value={preferredTool}
                    onChange={(event) => setPreferredTool(event.target.value)}
                    className="field-input"
                    placeholder="calculator | doc_search | task_mock"
                  />
                </div>
                <button type="submit" disabled={runLoading} className="btn-primary self-end">
                  {runLoading ? "Running..." : "Run Agent"}
                </button>
              </div>
            </form>

            {runError ? (
              <div className="mt-4 rounded-xl border border-red-300/70 bg-red-100/60 p-3 text-sm text-red-900 dark:border-red-500/50 dark:bg-red-900/40 dark:text-red-100">
                {runError}
              </div>
            ) : null}

            {runResult ? (
              <div className="mt-4 space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusPill label={runResult.status} tone={resultTone} />
                  <StatusPill label={`route:${runResult.route}`} />
                  <StatusPill label={`intent:${runResult.intent}`} />
                  <StatusPill label={`risk:${runResult.risk}`} tone={runResult.risk === "low" ? "ok" : "warn"} />
                </div>
                <div className="rounded-xl border border-border bg-card p-3 text-sm">
                  <p className="mb-2 font-semibold">Message</p>
                  <p>{runResult.message}</p>
                </div>
                <div className="rounded-xl border border-border bg-card p-3 text-sm">
                  <p className="mb-2 flex items-center gap-2 font-semibold">
                    <Wrench size={14} />
                    Tool / Policy Output
                  </p>
                  <pre className="overflow-auto rounded-lg bg-panel p-3 text-xs">
                    {JSON.stringify(runResult, null, 2)}
                  </pre>
                </div>
              </div>
            ) : null}
          </article>

          <article className="panel">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="panel-title">
                <Database size={16} />
                Policies
              </h2>
              <button type="button" className="btn-ghost" onClick={() => void loadPolicies()} disabled={policyLoading}>
                <RefreshCw size={14} className={policyLoading ? "animate-spin" : ""} />
              </button>
            </div>
            {policyError ? <p className="text-sm text-red-600 dark:text-red-300">{policyError}</p> : null}
            <pre className="h-[26rem] overflow-auto rounded-lg border border-border bg-panel p-3 text-xs">
              {JSON.stringify(policies ?? {}, null, 2)}
            </pre>
          </article>
        </section>

        <section className="mt-4">
          <article className="panel mb-4">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="panel-title">
                <BarChart3 size={16} />
                Performance Snapshot (Rolling 24h)
              </h2>
              <button type="button" className="btn-ghost" onClick={() => void refreshObservability()} disabled={dashboardLoading}>
                <RefreshCw size={14} className={dashboardLoading ? "animate-spin" : ""} />
              </button>
            </div>
            {dashboardError ? <p className="text-sm text-red-600 dark:text-red-300">{dashboardError}</p> : null}

            <div className="grid gap-3 md:grid-cols-4">
              <div className="metric-card">
                <p className="metric-label">Task Success</p>
                <p className="metric-value">{(taskSuccessRate * 100).toFixed(1)}%</p>
              </div>
              <div className="metric-card">
                <p className="metric-label">Fallback Rate</p>
                <p className="metric-value">{(fallbackActivationRate * 100).toFixed(1)}%</p>
              </div>
              <div className="metric-card">
                <p className="metric-label">Blocked Unsafe</p>
                <p className="metric-value">{blockedUnsafeActions}</p>
              </div>
              <div className="metric-card">
                <p className="metric-label">Policy Precision</p>
                <p className="metric-value">{(precisionProxy * 100).toFixed(1)}%</p>
              </div>
            </div>

            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <div className="chart-card">
                <p className="mb-2 flex items-center gap-2 text-sm font-semibold">
                  <Gauge size={14} />
                  Request Throughput and Outcomes
                </p>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={performanceData}>
                      <CartesianGrid strokeDasharray="4 4" stroke="rgba(148,163,184,.25)" />
                      <XAxis dataKey="hourLabel" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Legend />
                      <Area type="monotone" dataKey="requests" name="Requests" stroke="#3b82f6" fill="#93c5fd" fillOpacity={0.55} />
                      <Area type="monotone" dataKey="successful" name="Successful" stroke="#16a34a" fill="#86efac" fillOpacity={0.35} />
                      <Area type="monotone" dataKey="fallback_requests" name="Fallbacks" stroke="#f59e0b" fill="#fde68a" fillOpacity={0.45} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="chart-card">
                <p className="mb-2 flex items-center gap-2 text-sm font-semibold">
                  <Activity size={14} />
                  Incident Type Distribution
                </p>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={performanceData}>
                      <CartesianGrid strokeDasharray="4 4" stroke="rgba(148,163,184,.25)" />
                      <XAxis dataKey="hourLabel" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="policy_blocks" stackId="incidents" name="Policy Blocks" fill="#1d4ed8" />
                      <Bar dataKey="tool_failures" stackId="incidents" name="Tool Failures" fill="#f97316" />
                      <Bar dataKey="timeouts" stackId="incidents" name="Timeouts" fill="#eab308" />
                      <Bar dataKey="invalid_outputs" stackId="incidents" name="Invalid Outputs" fill="#dc2626" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </article>

          <article className="panel">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="panel-title">
                <AlertOctagon size={16} />
                Incident Explorer
              </h2>
              <button type="button" className="btn-ghost" onClick={() => void refreshObservability()} disabled={incidentFeedLoading}>
                <RefreshCw size={14} className={incidentFeedLoading ? "animate-spin" : ""} />
              </button>
            </div>
            {incidentFeedError ? <p className="text-sm text-red-600 dark:text-red-300">{incidentFeedError}</p> : null}
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <StatusPill label={`total:${incidentSummary?.total_incidents ?? 0}`} tone="warn" />
              {Object.entries(incidentSummary?.by_type ?? {}).map(([type, count]) => (
                <StatusPill key={type} label={`${type}:${count}`} />
              ))}
            </div>

            <div className="grid gap-4 lg:grid-cols-[1.2fr_.8fr]">
              <div className="overflow-auto rounded-xl border border-border">
                <table className="min-w-full text-left text-xs sm:text-sm">
                  <thead className="bg-panel">
                    <tr>
                      <th className="px-3 py-2 font-semibold">Type</th>
                      <th className="px-3 py-2 font-semibold">Request</th>
                      <th className="px-3 py-2 font-semibold">Why Blocked/Failed</th>
                      <th className="px-3 py-2 font-semibold">Last Seen</th>
                    </tr>
                  </thead>
                  <tbody>
                    {incidentFeed.length === 0 ? (
                      <tr>
                        <td className="px-3 py-4 text-center text-sm text-muted" colSpan={4}>
                          <span className="inline-flex items-center gap-2">
                            <CircleSlash2 size={14} />
                            No incidents recorded yet.
                          </span>
                        </td>
                      </tr>
                    ) : (
                      incidentFeed.map((item) => (
                        <tr
                          key={item.request_id}
                          className={`cursor-pointer border-t border-border transition ${
                            selectedRequestId === item.request_id ? "bg-bluecore-100/40 dark:bg-bluecore-900/40" : "hover:bg-panel/60"
                          }`}
                          onClick={() => void loadIncidentDetail(item.request_id)}
                        >
                          <td className="px-3 py-2">
                            <span className="inline-flex items-center gap-1">
                              <AlertOctagon size={13} />
                              {item.incident_type}
                            </span>
                          </td>
                          <td className="px-3 py-2">
                            <p className="max-w-xs truncate font-medium">{item.request_text || "(no text captured)"}</p>
                            <p className="font-mono text-[11px] text-muted">{shortId(item.request_id)}</p>
                          </td>
                          <td className="px-3 py-2 max-w-sm truncate">{item.reason_summary}</td>
                          <td className="px-3 py-2">{item.last_seen_ts}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              <div className="rounded-xl border border-border bg-card p-3">
                <p className="mb-2 text-sm font-semibold">Incident Detail</p>
                {detailError ? <p className="text-xs text-red-600 dark:text-red-300">{detailError}</p> : null}
                {detailLoading ? <p className="text-xs text-muted">Loading incident detail...</p> : null}
                {!detailLoading && !incidentDetail ? <p className="text-xs text-muted">Select an incident row to inspect reasons and timeline.</p> : null}

                {incidentDetail ? (
                  <div className="space-y-3 text-xs">
                    <div className="rounded-lg border border-border bg-panel p-2">
                      <p className="mb-1 font-semibold">Request Text</p>
                      <p>{incidentDetail.request_text || "(no text captured)"}</p>
                    </div>
                    <div className="rounded-lg border border-border bg-panel p-2">
                      <p className="mb-1 font-semibold">Why Blocked / Failed</p>
                      {incidentDetail.block_reasons.length === 0 ? (
                        <p className="text-muted">No explicit reasons captured.</p>
                      ) : (
                        <ul className="list-disc space-y-1 pl-4">
                          {incidentDetail.block_reasons.map((reason, index) => (
                            <li key={`${reason}-${index}`}>{reason}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                    <div className="rounded-lg border border-border bg-panel p-2">
                      <p className="mb-1 font-semibold">Timeline</p>
                      <div className="max-h-44 overflow-auto">
                        {incidentDetail.timeline.map((event) => (
                          <div key={event.id} className="mb-2 rounded border border-border bg-card p-2">
                            <p className="font-semibold">
                              {event.event_type} ({event.step})
                            </p>
                            <p className="text-muted">{event.ts}</p>
                            <pre className="mt-1 overflow-auto text-[11px]">{JSON.stringify(event.details, null, 2)}</pre>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div className="info-box">
                <p className="info-title">
                  <ShieldCheck size={14} />
                  Guardrails
                </p>
                <p className="info-copy">Policy checks execute before tools to block unsafe or unallowlisted operations.</p>
              </div>
              <div className="info-box">
                <p className="info-title">
                  <ListChecks size={14} />
                  Reliability
                </p>
                <p className="info-copy">Timeouts and tool failures resolve into deterministic safe-fallback outputs.</p>
              </div>
              <div className="info-box">
                <p className="info-title">
                  <AlertOctagon size={14} />
                  Remediation
                </p>
                <p className="info-copy">Use incident trends to update policy rules, tool schemas, and fallback thresholds.</p>
              </div>
            </div>
          </article>
        </section>
      </main>
    </div>
  );
}

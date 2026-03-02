import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertOctagon,
  CircleSlash2,
  Database,
  ListChecks,
  Play,
  RefreshCw,
  ShieldCheck,
  Wrench
} from "lucide-react";
import { fetchIncidents, fetchPolicies, runAgent, type IncidentSummary, type RunResponse } from "./lib/api";
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
  const [incidents, setIncidents] = useState<IncidentSummary | null>(null);
  const [incidentLoading, setIncidentLoading] = useState(false);
  const [incidentError, setIncidentError] = useState<string | null>(null);

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

  async function loadIncidents(): Promise<void> {
    setIncidentLoading(true);
    setIncidentError(null);
    try {
      const data = await fetchIncidents();
      setIncidents(data);
    } catch (error) {
      setIncidentError((error as Error).message);
    } finally {
      setIncidentLoading(false);
    }
  }

  useEffect(() => {
    void loadPolicies();
    void loadIncidents();
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
      await loadIncidents();
    } catch (error) {
      setRunError((error as Error).message);
    } finally {
      setRunLoading(false);
    }
  }

  const resultTone = useMemo(() => {
    if (!runResult) {
      return "neutral";
    }
    return runResult.status === "success" ? "ok" : "warn";
  }, [runResult]);

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
            <ThemeToggle theme={theme} onToggle={() => setTheme((prev) => (prev === "dark" ? "light" : "dark"))} />
          </div>
        </header>

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
          <article className="panel">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="panel-title">
                <Activity size={16} />
                Incidents
              </h2>
              <button
                type="button"
                className="btn-ghost"
                onClick={() => void loadIncidents()}
                disabled={incidentLoading}
              >
                <RefreshCw size={14} className={incidentLoading ? "animate-spin" : ""} />
              </button>
            </div>

            {incidentError ? <p className="text-sm text-red-600 dark:text-red-300">{incidentError}</p> : null}
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <StatusPill label={`total:${incidents?.total_incidents ?? 0}`} tone="warn" />
              {Object.entries(incidents?.by_type ?? {}).map(([type, count]) => (
                <StatusPill key={type} label={`${type}:${count}`} tone="neutral" />
              ))}
            </div>

            <div className="overflow-auto rounded-xl border border-border">
              <table className="min-w-full text-left text-xs sm:text-sm">
                <thead className="bg-panel">
                  <tr>
                    <th className="px-3 py-2 font-semibold">Type</th>
                    <th className="px-3 py-2 font-semibold">Step</th>
                    <th className="px-3 py-2 font-semibold">Request</th>
                    <th className="px-3 py-2 font-semibold">Timestamp</th>
                    <th className="px-3 py-2 font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {(incidents?.recent_events ?? []).length === 0 ? (
                    <tr>
                      <td className="px-3 py-4 text-center text-sm text-muted" colSpan={5}>
                        <span className="inline-flex items-center gap-2">
                          <CircleSlash2 size={14} />
                          No incidents recorded yet.
                        </span>
                      </td>
                    </tr>
                  ) : (
                    incidents?.recent_events.map((event) => (
                      <tr key={`${event.request_id}-${event.ts}`} className="border-t border-border">
                        <td className="px-3 py-2">
                          <span className="inline-flex items-center gap-1">
                            <AlertOctagon size={13} />
                            {event.event_type}
                          </span>
                        </td>
                        <td className="px-3 py-2">{event.step}</td>
                        <td className="px-3 py-2 font-mono text-[11px]">{event.request_id.slice(0, 8)}</td>
                        <td className="px-3 py-2">{event.ts}</td>
                        <td className="px-3 py-2">{event.success ? "ok" : "failed"}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
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

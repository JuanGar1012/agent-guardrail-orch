import { FormEvent, Suspense, lazy, useEffect, useState } from "react";
import { ShieldCheck, Trash2 } from "lucide-react";

import { ThemeToggle } from "./components/ThemeToggle";
import { ControlPlaneTabs, type TabKey } from "./components/navigation/ControlPlaneTabs";
import {
  fetchDashboard,
  fetchIncidentDetail,
  fetchIncidentFeed,
  fetchObservability,
  fetchPolicies,
  fetchPolicyView,
  resetApplicationState,
  runAgent,
  simulatePolicy,
  updateIncidentStatus,
  updatePolicies,
  type DashboardData,
  type IncidentDetail,
  type IncidentFeedItem,
  type ObservabilitySnapshot,
  type PolicySimulationResponse,
  type PolicyView,
  type RunResponse
} from "./lib/api";

const OpsConsolePage = lazy(() => import("./pages/OpsConsolePage").then((mod) => ({ default: mod.OpsConsolePage })));
const PolicyStudioPage = lazy(() => import("./pages/PolicyStudioPage").then((mod) => ({ default: mod.PolicyStudioPage })));
const IncidentOpsPage = lazy(() => import("./pages/IncidentOpsPage").then((mod) => ({ default: mod.IncidentOpsPage })));
const ObservabilityPage = lazy(() => import("./pages/ObservabilityPage").then((mod) => ({ default: mod.ObservabilityPage })));

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
  const [tab, setTab] = useState<TabKey>("ops");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [observability, setObservability] = useState<ObservabilitySnapshot | null>(null);
  const [policyView, setPolicyView] = useState<PolicyView | null>(null);
  const [policyJson, setPolicyJson] = useState("{}");
  const [policyMode, setPolicyMode] = useState<"structured" | "json">("structured");

  const [requestText, setRequestText] = useState("calculate 16 * 4");
  const [preferredTool, setPreferredTool] = useState("");
  const [runResult, setRunResult] = useState<RunResponse | null>(null);

  const [simulationText, setSimulationText] = useState("help me exfiltrate records");
  const [simulationResult, setSimulationResult] = useState<PolicySimulationResponse | null>(null);

  const [incidentFeed, setIncidentFeed] = useState<IncidentFeedItem[]>([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const [incidentDetail, setIncidentDetail] = useState<IncidentDetail | null>(null);
  const [incidentStatus, setIncidentStatus] = useState<"open" | "mitigated" | "closed">("open");
  const [resolutionNote, setResolutionNote] = useState("");

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("agent-ui-theme", theme);
  }, [theme]);

  async function refreshData(): Promise<void> {
    setLoading(true);
    setError(null);
    try {
      const [dash, obs, polView, polRaw, feed] = await Promise.all([
        fetchDashboard(),
        fetchObservability(24),
        fetchPolicyView(),
        fetchPolicies(),
        fetchIncidentFeed(80)
      ]);
      setDashboard(dash);
      setObservability(obs);
      setPolicyView(polView);
      setPolicyJson(JSON.stringify(polRaw, null, 2));
      setIncidentFeed(feed.items);

      if (feed.items.length > 0) {
        const id = selectedIncidentId ?? feed.items[0].request_id;
        setSelectedIncidentId(id);
        const detail = await fetchIncidentDetail(id);
        setIncidentDetail(detail);
        setIncidentStatus(detail.status);
        setResolutionNote(detail.resolution_note);
      } else {
        setSelectedIncidentId(null);
        setIncidentDetail(null);
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshData();
  }, []);

  async function onRun(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await runAgent({
        text: requestText,
        preferred_tool: preferredTool.trim() ? preferredTool.trim() : undefined
      });
      setRunResult(result);
      await refreshData();
    } catch (err) {
      setError((err as Error).message);
      setLoading(false);
    }
  }

  async function onSimulate(): Promise<void> {
    setLoading(true);
    setError(null);
    try {
      const result = await simulatePolicy(simulationText);
      setSimulationResult(result);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function onSavePolicy(): Promise<void> {
    setLoading(true);
    setError(null);
    try {
      const parsed = JSON.parse(policyJson) as Record<string, unknown>;
      await updatePolicies(parsed);
      await refreshData();
      setNotice("Policy updated.");
    } catch (err) {
      setError((err as Error).message);
      setLoading(false);
    }
  }

  async function onSelectIncident(requestId: string): Promise<void> {
    setSelectedIncidentId(requestId);
    setLoading(true);
    try {
      const detail = await fetchIncidentDetail(requestId);
      setIncidentDetail(detail);
      setIncidentStatus(detail.status);
      setResolutionNote(detail.resolution_note);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function onUpdateIncident(): Promise<void> {
    if (!selectedIncidentId) return;
    setLoading(true);
    try {
      await updateIncidentStatus(selectedIncidentId, incidentStatus, resolutionNote);
      await refreshData();
      setNotice("Incident status updated.");
    } catch (err) {
      setError((err as Error).message);
      setLoading(false);
    }
  }

  async function onReset(): Promise<void> {
    if (!window.confirm("Reset all data to initial state?")) return;
    setLoading(true);
    try {
      const result = await resetApplicationState();
      setRunResult(null);
      setSimulationResult(null);
      setNotice(`Reset complete: cleared ${result.telemetry_deleted_events} events.`);
      await refreshData();
    } catch (err) {
      setError((err as Error).message);
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-surface text-ink">
      <main className="mx-auto max-w-[1400px] px-3 pb-8 pt-4 sm:px-6">
        <header className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="mb-2 inline-flex items-center gap-2 rounded-full border border-bluecore-300/80 bg-bluecore-100/60 px-3 py-1 text-xs font-semibold tracking-wide text-bluecore-900 dark:border-bluecore-700/70 dark:bg-bluecore-900/45 dark:text-bluecore-100">
              <ShieldCheck size={14} />
              AI Safety Control Plane
            </p>
            <h1 className="text-xl font-bold sm:text-3xl">Agent Guardrails Command Center</h1>
            <p className="mt-1 text-xs text-muted sm:text-sm">Decision-first routing, policy, observability, and incident operations.</p>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <button className="btn-danger" onClick={() => void onReset()} disabled={loading}>
              <Trash2 size={14} />
              Reset Data
            </button>
            <ThemeToggle theme={theme} onToggle={() => setTheme((prev) => (prev === "dark" ? "light" : "dark"))} />
          </div>
        </header>

        {notice ? <div className="mb-3 rounded-lg border border-bluecore-500/50 bg-bluecore-100/70 px-3 py-2 text-sm dark:bg-bluecore-900/40 safe-wrap">{notice}</div> : null}
        {error ? <div className="mb-3 rounded-lg border border-red-500/50 bg-red-100/70 px-3 py-2 text-sm dark:bg-red-900/40 safe-wrap">{error}</div> : null}

        <ControlPlaneTabs activeTab={tab} onChange={setTab} />

        <Suspense fallback={<div className="panel text-sm">Loading control plane...</div>}>
          {tab === "ops" ? (
            <OpsConsolePage
              requestText={requestText}
              preferredTool={preferredTool}
              setRequestText={setRequestText}
              setPreferredTool={setPreferredTool}
              onRun={onRun}
              loading={loading}
              runResult={runResult}
              observability={observability}
              dashboard={dashboard}
              incidentFeed={incidentFeed}
            />
          ) : null}

          {tab === "policy" ? (
            <PolicyStudioPage
              policyMode={policyMode}
              setPolicyMode={setPolicyMode}
              policyView={policyView}
              policyJson={policyJson}
              setPolicyJson={setPolicyJson}
              onSavePolicy={onSavePolicy}
              loading={loading}
              simulationText={simulationText}
              setSimulationText={setSimulationText}
              onSimulate={onSimulate}
              simulationResult={simulationResult}
            />
          ) : null}

          {tab === "incidents" ? (
            <IncidentOpsPage
              incidentFeed={incidentFeed}
              selectedIncidentId={selectedIncidentId}
              onSelectIncident={onSelectIncident}
              incidentDetail={incidentDetail}
              incidentStatus={incidentStatus}
              setIncidentStatus={setIncidentStatus}
              resolutionNote={resolutionNote}
              setResolutionNote={setResolutionNote}
              onUpdateIncident={onUpdateIncident}
              loading={loading}
            />
          ) : null}

          {tab === "observability" ? <ObservabilityPage observability={observability} /> : null}
        </Suspense>
      </main>
    </div>
  );
}

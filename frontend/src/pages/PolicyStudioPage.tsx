import { FileJson, FileText, ShieldCheck, SlidersHorizontal } from "lucide-react";

import { StatusPill } from "../components/StatusPill";
import { type PolicySimulationResponse, type PolicyView } from "../lib/api";

type PolicyStudioPageProps = {
  policyMode: "structured" | "json";
  setPolicyMode: (mode: "structured" | "json") => void;
  policyView: PolicyView | null;
  policyJson: string;
  setPolicyJson: (value: string) => void;
  onSavePolicy: () => Promise<void>;
  loading: boolean;
  simulationText: string;
  setSimulationText: (value: string) => void;
  onSimulate: () => Promise<void>;
  simulationResult: PolicySimulationResponse | null;
};

export function PolicyStudioPage({
  policyMode,
  setPolicyMode,
  policyView,
  policyJson,
  setPolicyJson,
  onSavePolicy,
  loading,
  simulationText,
  setSimulationText,
  onSimulate,
  simulationResult
}: PolicyStudioPageProps): JSX.Element {
  return (
    <section className="grid grid-cols-12 gap-4">
      <article className="panel col-span-12 xl:col-span-7">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="panel-title">
            <SlidersHorizontal size={16} />
            Policy Management
          </h2>
          <div className="inline-flex flex-wrap gap-2">
            <button className={`tab-mini ${policyMode === "structured" ? "tab-mini-active" : ""}`} onClick={() => setPolicyMode("structured")}>
              <FileText size={14} />
              Structured
            </button>
            <button className={`tab-mini ${policyMode === "json" ? "tab-mini-active" : ""}`} onClick={() => setPolicyMode("json")}>
              <FileJson size={14} />
              JSON
            </button>
          </div>
        </div>

        {policyMode === "structured" ? (
          <div className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="metric-card">
                <p className="metric-label">Allowed Tools</p>
                <p className="metric-value">{policyView?.summary.allowed_tool_count ?? 0}</p>
              </div>
              <div className="metric-card">
                <p className="metric-label">Blocked Intents</p>
                <p className="metric-value">{policyView?.summary.blocked_intent_count ?? 0}</p>
              </div>
              <div className="metric-card">
                <p className="metric-label">Keyword Rules</p>
                <p className="metric-value">{policyView?.summary.blocked_keyword_count ?? 0}</p>
              </div>
            </div>
            <div className="rounded-lg border border-border bg-panel p-3">
              <p className="mb-2 text-xs font-semibold tracking-wide text-muted">Risk Cap Matrix</p>
              <table className="w-full text-xs">
                <tbody>
                  {(policyView?.risk_caps ?? []).map((row) => (
                    <tr key={row.intent}>
                      <td className="py-1">{row.intent}</td>
                      <td className="py-1">
                        <span className={`risk-badge risk-${row.max_risk}`}>{row.max_risk}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <textarea className="field-input min-h-[420px] font-mono text-xs" value={policyJson} onChange={(event) => setPolicyJson(event.target.value)} />
            <button className="btn-primary" onClick={() => void onSavePolicy()} disabled={loading}>
              Save Policy
            </button>
          </div>
        )}
      </article>

      <article className="panel col-span-12 xl:col-span-5">
        <h2 className="panel-title">
          <ShieldCheck size={16} />
          Policy Simulation
        </h2>
        <textarea className="field-input mt-3 min-h-24" value={simulationText} onChange={(event) => setSimulationText(event.target.value)} />
        <button className="btn-primary mt-3" onClick={() => void onSimulate()} disabled={loading}>
          Simulate
        </button>
        {simulationResult ? (
          <div className="mt-3 rounded-lg border border-border bg-panel p-3">
            <div className="flex flex-wrap gap-2">
              <StatusPill label={`intent:${simulationResult.classification.intent}`} />
              <StatusPill label={`risk:${simulationResult.classification.risk}`} />
              <StatusPill label={simulationResult.policy_decision.allowed ? "allow" : "block"} tone={simulationResult.policy_decision.allowed ? "ok" : "warn"} />
            </div>
            {simulationResult.policy_decision.blocked_rules.length > 0 ? (
              <ul className="mt-2 list-disc pl-4 text-xs">
                {simulationResult.policy_decision.blocked_rules.map((rule) => (
                  <li key={rule}>{rule}</li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}
      </article>
    </section>
  );
}

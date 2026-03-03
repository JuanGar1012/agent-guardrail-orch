import { AlertTriangle, ShieldAlert } from "lucide-react";

import { StatusPill } from "../components/StatusPill";
import { type IncidentDetail, type IncidentFeedItem } from "../lib/api";

function severityClass(severity: string): string {
  if (severity === "high") return "severity-high";
  if (severity === "medium") return "severity-medium";
  return "severity-low";
}

type IncidentOpsPageProps = {
  incidentFeed: IncidentFeedItem[];
  selectedIncidentId: string | null;
  onSelectIncident: (requestId: string) => Promise<void>;
  incidentDetail: IncidentDetail | null;
  incidentStatus: "open" | "mitigated" | "closed";
  setIncidentStatus: (status: "open" | "mitigated" | "closed") => void;
  resolutionNote: string;
  setResolutionNote: (value: string) => void;
  onUpdateIncident: () => Promise<void>;
  loading: boolean;
};

export function IncidentOpsPage({
  incidentFeed,
  selectedIncidentId,
  onSelectIncident,
  incidentDetail,
  incidentStatus,
  setIncidentStatus,
  resolutionNote,
  setResolutionNote,
  onUpdateIncident,
  loading
}: IncidentOpsPageProps): JSX.Element {
  return (
    <section className="grid grid-cols-12 gap-4">
      <article className="panel col-span-12 xl:col-span-7">
        <h2 className="panel-title">
          <ShieldAlert size={16} />
          Incident Queue
        </h2>
        <div className="mt-3 space-y-2 sm:hidden">
          {incidentFeed.map((item) => (
            <button
              key={item.request_id}
              type="button"
              className={`w-full rounded-lg border border-border bg-panel p-3 text-left ${selectedIncidentId === item.request_id ? "ring-2 ring-bluecore-500/50" : ""}`}
              onClick={() => void onSelectIncident(item.request_id)}
            >
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span className={`severity-chip ${severityClass(item.severity)}`}>{item.severity}</span>
                <StatusPill label={item.status} tone={item.status === "open" ? "warn" : "ok"} />
              </div>
              <p className="text-xs font-semibold">{item.incident_type}</p>
              <p className="mt-1 text-xs safe-wrap">{item.reason_summary}</p>
            </button>
          ))}
        </div>

        <div className="mt-3 hidden overflow-auto rounded-lg border border-border sm:block">
          <table className="min-w-full text-left text-xs">
            <thead className="bg-panel">
              <tr>
                <th className="px-2 py-2">Severity</th>
                <th className="px-2 py-2">Status</th>
                <th className="px-2 py-2">Type</th>
                <th className="px-2 py-2">Reason</th>
              </tr>
            </thead>
            <tbody>
              {incidentFeed.map((item) => (
                <tr
                  key={item.request_id}
                  className={`cursor-pointer border-t border-border ${selectedIncidentId === item.request_id ? "bg-bluecore-100/40 dark:bg-bluecore-900/40" : ""}`}
                  onClick={() => void onSelectIncident(item.request_id)}
                >
                  <td className="px-2 py-2">
                    <span className={`severity-chip ${severityClass(item.severity)}`}>{item.severity}</span>
                  </td>
                  <td className="px-2 py-2">
                    <StatusPill label={item.status} tone={item.status === "open" ? "warn" : "ok"} />
                  </td>
                  <td className="px-2 py-2">{item.incident_type}</td>
                  <td className="max-w-[340px] px-2 py-2 safe-wrap">{item.reason_summary}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>

      <article className="panel col-span-12 xl:col-span-5">
        <h2 className="panel-title">
          <AlertTriangle size={16} />
          Incident Detail
        </h2>
        {!incidentDetail ? <p className="mt-3 text-sm text-muted">Select an incident for root-cause and remediation workflow.</p> : null}
        {incidentDetail ? (
          <div className="mt-3 space-y-3">
            <div className="rounded-lg border border-border bg-panel p-3">
              <p className="text-xs text-muted safe-wrap">{incidentDetail.request_text}</p>
              <p className="mt-1 text-sm font-semibold safe-wrap">{incidentDetail.root_cause_summary}</p>
            </div>
            <div className="rounded-lg border border-border bg-panel p-3">
              <div className="grid gap-2 sm:grid-cols-[auto_1fr]">
                <select className="field-input" value={incidentStatus} onChange={(event) => setIncidentStatus(event.target.value as "open" | "mitigated" | "closed")}>
                  <option value="open">open</option>
                  <option value="mitigated">mitigated</option>
                  <option value="closed">closed</option>
                </select>
                <input className="field-input" value={resolutionNote} onChange={(event) => setResolutionNote(event.target.value)} placeholder="resolution note" />
              </div>
              <button className="btn-primary mt-2" onClick={() => void onUpdateIncident()} disabled={loading}>
                Update Status
              </button>
            </div>
          </div>
        ) : null}
      </article>
    </section>
  );
}

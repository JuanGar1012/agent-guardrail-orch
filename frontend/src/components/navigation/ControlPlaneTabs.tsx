import { BarChart3, ShieldAlert, SlidersHorizontal, Workflow } from "lucide-react";

export type TabKey = "ops" | "policy" | "incidents" | "observability";

const TAB_LIST: Array<{ key: TabKey; label: string; icon: JSX.Element }> = [
  { key: "ops", label: "Ops Console", icon: <Workflow size={14} /> },
  { key: "policy", label: "Policy Studio", icon: <SlidersHorizontal size={14} /> },
  { key: "incidents", label: "Incident Ops", icon: <ShieldAlert size={14} /> },
  { key: "observability", label: "Observability", icon: <BarChart3 size={14} /> }
];

type ControlPlaneTabsProps = {
  activeTab: TabKey;
  onChange: (tab: TabKey) => void;
};

export function ControlPlaneTabs({ activeTab, onChange }: ControlPlaneTabsProps): JSX.Element {
  return (
    <nav className="mb-4 overflow-x-auto">
      <div className="inline-flex min-w-full gap-2 rounded-xl border border-border bg-card p-2 sm:min-w-0">
        {TAB_LIST.map((item) => (
          <button key={item.key} className={`tab-btn ${activeTab === item.key ? "tab-btn-active" : ""}`} onClick={() => onChange(item.key)}>
            {item.icon}
            {item.label}
          </button>
        ))}
      </div>
    </nav>
  );
}

import { Activity, AlertTriangle, Database, ShieldCheck } from "lucide-react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { type ObservabilitySnapshot } from "../lib/api";

type ObservabilityPageProps = {
  observability: ObservabilitySnapshot | null;
};

export function ObservabilityPage({ observability }: ObservabilityPageProps): JSX.Element {
  const fallbackTrend = (observability?.fallback_frequency_trend ?? []).map((point) => ({
    ...point,
    label: point.hour.slice(11, 16)
  }));
  const precisionTrend = (observability?.policy_precision_proxy_over_time ?? []).map((point) => ({
    ...point,
    label: point.hour.slice(11, 16),
    precisionPct: point.precision_proxy * 100
  }));

  return (
    <section className="grid grid-cols-12 gap-4">
      <article className="panel col-span-12 xl:col-span-8">
        <h2 className="panel-title">
          <Activity size={16} />
          Fallback Frequency Trend
        </h2>
        <div className="mt-3 h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={fallbackTrend}>
              <CartesianGrid strokeDasharray="4 4" stroke="rgba(148,163,184,.25)" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Area type="monotone" dataKey="fallback_requests" stroke="#f59e0b" fill="#fcd34d" fillOpacity={0.45} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </article>

      <article className="panel col-span-12 xl:col-span-4">
        <h2 className="panel-title">
          <Database size={16} />
          Tool Selection
        </h2>
        <div className="mt-3 h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={observability?.tool_selection_distribution ?? []}>
              <CartesianGrid strokeDasharray="4 4" stroke="rgba(148,163,184,.25)" />
              <XAxis dataKey="tool" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#2563eb" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </article>

      <article className="panel col-span-12 xl:col-span-6">
        <h2 className="panel-title">
          <AlertTriangle size={16} />
          Risk Histogram
        </h2>
        <div className="mt-3 h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={observability?.risk_distribution_histogram ?? []}>
              <CartesianGrid strokeDasharray="4 4" stroke="rgba(148,163,184,.25)" />
              <XAxis dataKey="risk" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count">
                {(observability?.risk_distribution_histogram ?? []).map((item) => (
                  <Cell key={item.risk} fill={item.risk === "low" ? "#22c55e" : item.risk === "medium" ? "#f59e0b" : item.risk === "high" ? "#f97316" : "#dc2626"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </article>

      <article className="panel col-span-12 xl:col-span-6">
        <h2 className="panel-title">
          <ShieldCheck size={16} />
          Policy Precision Proxy
        </h2>
        <div className="mt-3 h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={precisionTrend}>
              <CartesianGrid strokeDasharray="4 4" stroke="rgba(148,163,184,.25)" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} domain={[0, 100]} />
              <Tooltip />
              <Line type="monotone" dataKey="precisionPct" stroke="#14b8a6" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </article>
    </section>
  );
}

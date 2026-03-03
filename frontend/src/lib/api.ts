export type RunRequest = {
  text: string;
  preferred_tool?: string;
  tool_args?: Record<string, unknown>;
};

export type RunResponse = {
  request_id: string;
  status: "success" | "safe_fallback";
  route: string;
  intent: string;
  risk: "low" | "medium" | "high" | "critical";
  message: string;
  fallback_used: boolean;
  tool_results: Record<string, unknown>;
  policy: {
    allowed: boolean;
    reason: string;
    blocked_rules: string[];
    allowed_tools: string[];
  };
  errors: string[];
};

export type IncidentSummary = {
  total_incidents: number;
  by_type: Record<string, number>;
  recent_events: Array<{
    request_id: string;
    ts: string;
    step: string;
    event_type: string;
    success: boolean;
    details: Record<string, unknown>;
  }>;
};

export type IncidentTrendPoint = {
  day: string;
  event_type: string;
  count: number;
};

export type IncidentFeedItem = {
  request_id: string;
  incident_type: string;
  first_seen_ts: string;
  last_seen_ts: string;
  request_text: string;
  reason_summary: string;
  event_count: number;
  incident_events: Array<{
    ts: string;
    event_type: string;
    step: string;
    details: Record<string, unknown>;
  }>;
};

export type IncidentDetail = {
  request_id: string;
  found: boolean;
  request_text: string;
  incident_count: number;
  incident_types: string[];
  block_reasons: string[];
  timeline: Array<{
    id: number;
    ts: string;
    step: string;
    event_type: string;
    success: boolean;
    details: Record<string, unknown>;
  }>;
};

export type PerformancePoint = {
  hour: string;
  requests: number;
  successful: number;
  fallback_requests: number;
  policy_blocks: number;
  tool_failures: number;
  timeouts: number;
  invalid_outputs: number;
};

export type DashboardData = {
  metrics_summary: Record<string, unknown>;
  incident_summary: IncidentSummary;
  incident_trends: IncidentTrendPoint[];
  incident_feed: IncidentFeedItem[];
  performance_24h: PerformancePoint[];
};

export type ResetResponse = {
  status: string;
  telemetry_deleted_events: number;
  tasks_cleared: number;
  deleted_files: string[];
};

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {})
    }
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`API ${path} failed (${response.status}): ${text}`);
  }
  return (await response.json()) as T;
}

export function runAgent(payload: RunRequest): Promise<RunResponse> {
  return request<RunResponse>("/agent/run", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function fetchPolicies(): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>("/agent/policies");
}

export function fetchIncidents(): Promise<IncidentSummary> {
  return request<IncidentSummary>("/agent/incidents");
}

export function fetchDashboard(): Promise<DashboardData> {
  return request<DashboardData>("/agent/dashboard");
}

export function fetchIncidentFeed(limit = 50): Promise<{ items: IncidentFeedItem[] }> {
  return request<{ items: IncidentFeedItem[] }>(`/agent/incidents/feed?limit=${limit}`);
}

export function fetchIncidentDetail(requestId: string): Promise<IncidentDetail> {
  return request<IncidentDetail>(`/agent/incidents/${requestId}`);
}

export function resetApplicationState(): Promise<ResetResponse> {
  return request<ResetResponse>("/agent/reset", { method: "POST" });
}

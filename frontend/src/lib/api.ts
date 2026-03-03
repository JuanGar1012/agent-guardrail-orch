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

export type IncidentFeedItem = {
  request_id: string;
  incident_type: string;
  severity: "low" | "medium" | "high";
  status: "open" | "mitigated" | "closed";
  resolution_note: string;
  first_seen_ts: string;
  last_seen_ts: string;
  request_text: string;
  reason_summary: string;
  linked_rules: string[];
  tool_name: string;
  event_count: number;
  recurrence_count_24h: number;
};

export type IncidentDetail = {
  request_id: string;
  found: boolean;
  request_text: string;
  incident_count: number;
  incident_types: string[];
  severity: "low" | "medium" | "high";
  status: "open" | "mitigated" | "closed";
  resolution_note: string;
  root_cause_summary: string;
  linked_policy_rules: string[];
  tool_name: string;
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

export type ObservabilitySnapshot = {
  window_hours: number;
  latency_percentiles_ms: {
    p50: number;
    p95: number;
    p99: number;
  };
  tool_selection_distribution: Array<{ tool: string; count: number }>;
  risk_distribution_histogram: Array<{ risk: string; count: number }>;
  fallback_frequency_trend: Array<{ hour: string; fallback_requests: number }>;
  policy_precision_proxy_over_time: Array<{ hour: string; precision_proxy: number; policy_blocks: number }>;
  tool_error_heatmap: Array<{ tool: string; error_type: string; count: number }>;
};

export type DashboardData = {
  metrics_summary: Record<string, unknown>;
  incident_summary: IncidentSummary;
  incident_trends: Array<{ day: string; event_type: string; count: number }>;
  incident_feed: IncidentFeedItem[];
  performance_24h: PerformancePoint[];
  observability: ObservabilitySnapshot;
};

export type PolicyView = {
  summary: {
    allowed_tool_count: number;
    blocked_intent_count: number;
    blocked_keyword_count: number;
  };
  risk_caps: Array<{ intent: string; max_risk: string }>;
  tool_permissions: Array<{ intent: string; tools: string[] }>;
  keyword_rules: Array<{ keyword: string; category: string }>;
};

export type PolicySimulationResponse = {
  classification: {
    intent: string;
    risk: string;
    reason: string;
    route_hint: string;
  };
  route: string;
  suggested_tool: string | null;
  policy_decision: {
    allowed: boolean;
    reason: string;
    blocked_rules: string[];
    allowed_tools: string[];
  };
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

export function fetchDashboard(): Promise<DashboardData> {
  return request<DashboardData>("/agent/dashboard");
}

export function fetchPolicies(): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>("/agent/policies");
}

export function updatePolicies(policy: Record<string, unknown>): Promise<{ status: string; policy: Record<string, unknown> }> {
  return request<{ status: string; policy: Record<string, unknown> }>("/agent/policies", {
    method: "PUT",
    body: JSON.stringify({ policy })
  });
}

export function fetchPolicyView(): Promise<PolicyView> {
  return request<PolicyView>("/agent/policies/view");
}

export function simulatePolicy(text: string, preferredTool?: string): Promise<PolicySimulationResponse> {
  return request<PolicySimulationResponse>("/agent/policies/simulate", {
    method: "POST",
    body: JSON.stringify({ text, preferred_tool: preferredTool || undefined })
  });
}

export function fetchIncidentFeed(limit = 50): Promise<{ items: IncidentFeedItem[] }> {
  return request<{ items: IncidentFeedItem[] }>(`/agent/incidents/feed?limit=${limit}`);
}

export function fetchIncidentDetail(requestId: string): Promise<IncidentDetail> {
  return request<IncidentDetail>(`/agent/incidents/${requestId}`);
}

export function updateIncidentStatus(
  requestId: string,
  status: "open" | "mitigated" | "closed",
  resolutionNote = ""
): Promise<{ request_id: string; status: string; resolution_note: string }> {
  return request<{ request_id: string; status: string; resolution_note: string }>(`/agent/incidents/${requestId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status, resolution_note: resolutionNote })
  });
}

export function fetchObservability(hours = 24): Promise<ObservabilitySnapshot> {
  return request<ObservabilitySnapshot>(`/agent/observability?hours=${hours}`);
}

export function resetApplicationState(): Promise<ResetResponse> {
  return request<ResetResponse>("/agent/reset", { method: "POST" });
}

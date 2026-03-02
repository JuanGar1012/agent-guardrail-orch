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

export type DashboardData = {
  metrics_summary: Record<string, unknown>;
  incident_summary: IncidentSummary;
  incident_trends: IncidentTrendPoint[];
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

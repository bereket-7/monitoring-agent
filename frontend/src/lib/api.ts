import type {
  AgentChatResponse,
  DashboardAnalysisReport,
  DashboardDetail,
  DashboardSummary,
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) {
        detail = body.detail;
      }
    } catch {
      // keep status text
    }
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

export function listDashboards(): Promise<DashboardSummary[]> {
  return request<DashboardSummary[]>("/api/v1/dashboards");
}

export function getDashboard(uid: string): Promise<DashboardDetail> {
  return request<DashboardDetail>(`/api/v1/dashboards/${encodeURIComponent(uid)}`);
}

export function analyzeDashboard(uid: string): Promise<DashboardAnalysisReport> {
  return request<DashboardAnalysisReport>(
    `/api/v1/analysis/dashboards/${encodeURIComponent(uid)}`,
  );
}

export function agentChat(payload: {
  message: string;
  dashboard_uid?: string;
  context?: {
    time_range?: { from?: string; to?: string };
    filters?: Record<string, string>;
  };
}): Promise<AgentChatResponse> {
  return request<AgentChatResponse>("/api/v1/agent/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

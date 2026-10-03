import type { DashboardDetail, DashboardSummary } from "./types";

function apiOrigin(): string {
  return process.env.API_ORIGIN ?? "http://127.0.0.1:8000";
}

export async function listDashboardsServer(): Promise<DashboardSummary[]> {
  try {
    const response = await fetch(`${apiOrigin()}/api/v1/dashboards`, {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) {
      return [];
    }
    return (await response.json()) as DashboardSummary[];
  } catch {
    return [];
  }
}

export async function getDashboardServer(uid: string): Promise<DashboardDetail | null> {
  try {
    const response = await fetch(
      `${apiOrigin()}/api/v1/dashboards/${encodeURIComponent(uid)}`,
      {
        cache: "no-store",
        headers: { Accept: "application/json" },
      },
    );
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as DashboardDetail;
  } catch {
    return null;
  }
}

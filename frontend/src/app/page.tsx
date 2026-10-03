import { AnalysisWorkspace } from "@/components/AnalysisWorkspace";
import { getDashboardServer, listDashboardsServer } from "@/lib/server-api";

export default async function HomePage() {
  const dashboards = await listDashboardsServer();
  const initialUid = dashboards[0]?.grafana_uid ?? "";
  const initialDetail = initialUid ? await getDashboardServer(initialUid) : null;
  return (
    <AnalysisWorkspace initialDashboards={dashboards} initialDetail={initialDetail} />
  );
}

"use client";

import { useMemo, useState, useTransition } from "react";

import { AgentChat } from "@/components/AgentChat";
import { EvidencePanel } from "@/components/EvidencePanel";
import { FindingsPanel } from "@/components/FindingsPanel";
import { analyzeDashboard, getDashboard, listDashboards } from "@/lib/api";
import type {
  AgentChatResponse,
  DashboardAnalysisReport,
  DashboardDetail,
  DashboardSummary,
} from "@/lib/types";

const TIME_RANGES = [
  { label: "Last 1 hour", from: "now-1h", to: "now" },
  { label: "Last 6 hours", from: "now-6h", to: "now" },
  { label: "Last 24 hours", from: "now-24h", to: "now" },
  { label: "Last 7 days", from: "now-7d", to: "now" },
];

export function AnalysisWorkspace({
  initialDashboards,
  initialDetail,
}: {
  initialDashboards: DashboardSummary[];
  initialDetail: DashboardDetail | null;
}) {
  const [dashboards, setDashboards] = useState(initialDashboards);
  const [selectedUid, setSelectedUid] = useState(
    initialDetail?.grafana_uid ?? initialDashboards[0]?.grafana_uid ?? "",
  );
  const [detail, setDetail] = useState<DashboardDetail | null>(initialDetail);
  const [report, setReport] = useState<DashboardAnalysisReport | null>(null);
  const [chat, setChat] = useState<AgentChatResponse | null>(null);
  const [timeRange, setTimeRange] = useState(TIME_RANGES[1]);
  const [environment, setEnvironment] = useState("production");
  const [service, setService] = useState(() =>
    initialDetail?.variables.some((item) => item.name === "service") ? "payment-api" : "",
  );
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, startRefresh] = useTransition();
  const [isLoadingDetail, startDetailLoad] = useTransition();

  const filters = useMemo(() => {
    const next: Record<string, string> = {};
    if (environment.trim()) {
      next.environment = environment.trim();
    }
    if (service.trim()) {
      next.service = service.trim();
    }
    return next;
  }, [environment, service]);

  function refreshDashboards() {
    startRefresh(async () => {
      setError(null);
      try {
        const items = await listDashboards();
        setDashboards(items);
        if (!selectedUid && items.length > 0) {
          await selectDashboard(items[0].grafana_uid, items);
        } else if (selectedUid && !items.some((item) => item.grafana_uid === selectedUid)) {
          setSelectedUid("");
          setDetail(null);
          setReport(null);
          setChat(null);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load dashboards");
      }
    });
  }

  async function selectDashboard(uid: string, knownDashboards = dashboards) {
    setSelectedUid(uid);
    setReport(null);
    setChat(null);
    if (!uid) {
      setDetail(null);
      return;
    }

    startDetailLoad(async () => {
      setError(null);
      try {
        const dashboard = await getDashboard(uid);
        setDetail(dashboard);
        setService((current) => {
          if (current) {
            return current;
          }
          const hasService = dashboard.variables.some((item) => item.name === "service");
          return hasService ? "payment-api" : current;
        });
        if (!knownDashboards.some((item) => item.grafana_uid === uid)) {
          setDashboards((prev) => [...prev, dashboard]);
        }
      } catch (err) {
        setDetail(null);
        setError(err instanceof Error ? err.message : "Failed to load dashboard");
      }
    });
  }

  async function runAnalysis() {
    if (!selectedUid) {
      return;
    }
    setAnalyzing(true);
    setError(null);
    try {
      if (!detail) {
        await selectDashboard(selectedUid);
      }
      const next = await analyzeDashboard(selectedUid);
      setReport(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setAnalyzing(false);
    }
  }

  const findings = report?.findings ?? [];
  const grafanaHref =
    detail?.url && detail.url.startsWith("http")
      ? detail.url
      : detail?.url
        ? detail.url
        : null;

  return (
    <div className="app-shell">
      <header className="brand-bar">
        <div>
          <h1>Monitoring Dashboard Agent</h1>
          <p>Validate Grafana dashboards with deterministic findings and grounded agent chat.</p>
        </div>
        <button className="secondary-btn" type="button" onClick={refreshDashboards}>
          {isRefreshing ? "Refreshing…" : "Refresh list"}
        </button>
      </header>

      <section className="toolbar" aria-label="Analysis controls">
        <div className="field">
          <label htmlFor="dashboard">Dashboard</label>
          <select
            id="dashboard"
            value={selectedUid}
            onChange={(event) => {
              void selectDashboard(event.target.value);
            }}
            disabled={isRefreshing || dashboards.length === 0}
          >
            {dashboards.length === 0 ? (
              <option value="">No synced dashboards</option>
            ) : (
              dashboards.map((item) => (
                <option key={item.grafana_uid} value={item.grafana_uid}>
                  {item.title} ({item.grafana_uid})
                </option>
              ))
            )}
          </select>
        </div>

        <div className="field">
          <label htmlFor="time-range">Time range</label>
          <select
            id="time-range"
            value={`${timeRange.from}|${timeRange.to}`}
            onChange={(event) => {
              const match = TIME_RANGES.find(
                (item) => `${item.from}|${item.to}` === event.target.value,
              );
              if (match) {
                setTimeRange(match);
              }
            }}
          >
            {TIME_RANGES.map((item) => (
              <option key={item.label} value={`${item.from}|${item.to}`}>
                {item.label}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label htmlFor="environment">Environment</label>
          <input
            id="environment"
            value={environment}
            onChange={(event) => setEnvironment(event.target.value)}
            placeholder="production"
            autoComplete="off"
          />
        </div>

        <div className="field">
          <label htmlFor="service">Service</label>
          <input
            id="service"
            value={service}
            onChange={(event) => setService(event.target.value)}
            placeholder="payment-api"
            autoComplete="off"
          />
        </div>

        <button
          className="primary-btn"
          type="button"
          onClick={() => void runAnalysis()}
          disabled={!selectedUid || analyzing}
        >
          {analyzing ? "Analyzing…" : "Run analysis"}
        </button>
      </section>

      {error ? (
        <p className="status-line" data-tone="error" role="alert">
          {error}
        </p>
      ) : (
        <p className="status-line">
          {isLoadingDetail
            ? "Loading dashboard detail…"
            : detail
              ? `Selected ${detail.title} · ${detail.panel_count} panels · ${detail.variable_count} variables`
              : selectedUid
                ? "Dashboard selected — run analysis or open a panel overview by re-selecting."
                : "Sync a dashboard via POST /api/v1/dashboards/{uid}/sync, then refresh."}
        </p>
      )}

      <div className="workspace">
        <section className="overview" aria-labelledby="overview-title">
          <h2 id="overview-title" className="panel-title">
            Dashboard overview
          </h2>
          {!detail ? (
            <p className="empty">
              {selectedUid
                ? "Choose the dashboard again or click Refresh to load panel overview."
                : "Select a synced dashboard to inspect panels and variables."}
            </p>
          ) : (
            <div className="overview-grid">
              <div>
                <div className="meta-row">
                  <span>
                    UID: <span className="mono">{detail.grafana_uid}</span>
                  </span>
                  <span>Folder: {detail.folder ?? "—"}</span>
                  <span>
                    Open in Grafana:{" "}
                    {grafanaHref ? (
                      <a href={grafanaHref} target="_blank" rel="noreferrer">
                        {grafanaHref}
                      </a>
                    ) : (
                      "unavailable (analysis UI does not embed Grafana)"
                    )}
                  </span>
                </div>
                <ul className="panel-list" aria-label="Panels">
                  {detail.panels.map((panel) => (
                    <li key={panel.id}>
                      <strong>
                        {panel.title}{" "}
                        <span className="empty">#{panel.grafana_panel_id}</span>
                      </strong>
                      <div className="empty">
                        {panel.panel_type}
                        {panel.datasource_uid ? ` · ${panel.datasource_uid}` : ""}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h3 className="panel-title">Variables / filters</h3>
                <ul className="panel-list" aria-label="Variables">
                  {detail.variables.map((variable) => (
                    <li key={variable.id}>
                      <strong>${variable.name}</strong>
                      <div className="empty">
                        {variable.variable_type}
                        {variable.multi ? " · multi" : ""}
                        {variable.include_all ? " · includeAll" : ""}
                      </div>
                    </li>
                  ))}
                </ul>
                {report?.filter_intelligence ? (
                  <p className="empty">
                    Filter intel: {report.filter_intelligence.dead_variables.length} dead,{" "}
                    {report.filter_intelligence.partially_propagated.length} partial
                  </p>
                ) : null}
              </div>
            </div>
          )}
        </section>

        <div className="split">
          <FindingsPanel findings={findings} />
          <AgentChat
            dashboardUid={selectedUid}
            timeFrom={timeRange.from}
            timeTo={timeRange.to}
            filters={filters}
            onResponse={setChat}
          />
        </div>

        <EvidencePanel report={report} chat={chat} />
      </div>
    </div>
  );
}

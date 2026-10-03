import type { AgentChatResponse, DashboardAnalysisReport } from "@/lib/types";

export function EvidencePanel({
  report,
  chat,
}: {
  report: DashboardAnalysisReport | null;
  chat: AgentChatResponse | null;
}) {
  const queries = report?.query_inventory.slice(0, 12) ?? [];
  const chatEvidence = chat?.evidence ?? [];
  const chatQueries = chat?.queries ?? [];

  const empty = queries.length === 0 && chatEvidence.length === 0 && chatQueries.length === 0;

  return (
    <section className="evidence-panel" aria-labelledby="evidence-title">
      <h2 id="evidence-title" className="panel-title">
        Evidence / Query / Calculation
      </h2>
      {empty ? (
        <p className="empty">
          Evidence appears here after analysis or agent tool execution. Claims without tool
          results are not shown as observed data.
        </p>
      ) : (
        <ul className="evidence-list">
          {queries.map((query) => (
            <li key={`${query.panel_id}-${query.query_hash}`}>
              <strong>
                Panel {query.panel_id} · {query.panel_title}
              </strong>
              <div className="mono">{query.raw_query}</div>
              {query.referenced_metrics.length > 0 ? (
                <div>Metrics: {query.referenced_metrics.join(", ")}</div>
              ) : null}
            </li>
          ))}
          {chatQueries.map((query, index) => (
            <li key={`chat-query-${index}`}>
              <strong>
                {query.datasource} query · {query.result_summary}
              </strong>
              <div className="mono">{query.query}</div>
            </li>
          ))}
          {chatEvidence.map((item, index) => (
            <li key={`chat-evidence-${index}`}>
              <strong>
                {item.observed ? "Observed" : "Not observed"} · {item.tool_name}
              </strong>
              <div>{item.summary}</div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

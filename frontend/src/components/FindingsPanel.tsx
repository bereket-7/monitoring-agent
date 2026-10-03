import type { StaticAnalysisFinding } from "@/lib/types";

function panelFromEvidence(evidence: Array<Record<string, unknown>>): string | null {
  for (const item of evidence) {
    if (typeof item.panel_id === "number") {
      const title = typeof item.title === "string" ? item.title : null;
      return title ? `Panel ${item.panel_id} · ${title}` : `Panel ${item.panel_id}`;
    }
    if (typeof item.panel_ids === "object" && Array.isArray(item.panel_ids)) {
      return `Panels ${item.panel_ids.join(", ")}`;
    }
  }
  return null;
}

function valueFromEvidence(
  evidence: Array<Record<string, unknown>>,
  key: "query" | "observed_value" | "expected_value",
): string | null {
  for (const item of evidence) {
    const value = item[key];
    if (value === undefined || value === null) {
      continue;
    }
    return typeof value === "string" ? value : JSON.stringify(value);
  }
  return null;
}

export function FindingsPanel({ findings }: { findings: StaticAnalysisFinding[] }) {
  if (findings.length === 0) {
    return (
      <section className="findings-panel" aria-labelledby="findings-title">
        <h2 id="findings-title" className="panel-title">
          Validation Findings
        </h2>
        <p className="empty">Run analysis to see deterministic findings for this dashboard.</p>
      </section>
    );
  }

  return (
    <section className="findings-panel" aria-labelledby="findings-title">
      <h2 id="findings-title" className="panel-title">
        Validation Findings
      </h2>
      <div className="finding-list">
        {findings.map((finding, index) => {
          const panel = panelFromEvidence(finding.evidence);
          const query = valueFromEvidence(finding.evidence, "query");
          return (
            <article key={`${finding.rule_id}-${index}`}>
              <div
                className="severity"
                data-level={finding.severity}
                aria-label={`Severity ${finding.severity}`}
              >
                {finding.severity}
                {finding.rule_id ? ` · ${finding.rule_id}` : ""}
              </div>
              <h3>{finding.title}</h3>
              {panel ? <p>{panel}</p> : null}
              <p>{finding.description}</p>
              {query ? (
                <p className="mono" title="Query from evidence">
                  {query}
                </p>
              ) : null}
              {finding.recommendation ? (
                <p>
                  <strong>Recommendation:</strong> {finding.recommendation}
                </p>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}

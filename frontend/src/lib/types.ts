export type FindingSeverity = "info" | "warning" | "error" | "critical";

export interface DashboardSummary {
  id: number;
  grafana_uid: string;
  title: string;
  folder: string | null;
  url: string | null;
  json_hash: string;
  updated_at: string;
  panel_count: number;
  variable_count: number;
}

export interface DashboardDetail extends DashboardSummary {
  panels: Array<{
    id: number;
    grafana_panel_id: number;
    title: string;
    panel_type: string;
    datasource_uid: string | null;
  }>;
  variables: Array<{
    id: number;
    name: string;
    label: string | null;
    variable_type: string;
    query: string | null;
    multi: boolean;
    include_all: boolean;
  }>;
}

export interface StaticAnalysisFinding {
  rule_id: string;
  severity: FindingSeverity;
  category: string;
  title: string;
  description: string;
  evidence: Array<Record<string, unknown>>;
  recommendation: string;
}

export interface AnalyzedQuery {
  panel_id: number;
  panel_title: string;
  ref_id: string | null;
  raw_query: string;
  normalized_query: string;
  query_hash: string;
  referenced_metrics: string[];
  referenced_variables: string[];
}

export interface FilterIntelligenceReport {
  dead_variables: string[];
  partially_propagated: string[];
  findings: Array<Record<string, unknown>>;
  contracts: Array<{
    variable_name: string;
    label: string | null;
    multi: boolean;
    include_all: boolean;
    affected_panels: number[];
    unaffected_panels: number[];
    cardinality_class: string;
  }>;
}

export interface DashboardAnalysisReport {
  dashboard_uid: string;
  title: string;
  panel_count: number;
  variable_count: number;
  query_inventory: AnalyzedQuery[];
  unused_variables: string[];
  duplicate_queries: Array<{
    query_hash: string;
    normalized_query: string;
    occurrences: Array<Record<string, unknown>>;
  }>;
  filter_intelligence: FilterIntelligenceReport | null;
  findings: StaticAnalysisFinding[];
}

export interface ToolCallRecord {
  name: string;
  arguments: Record<string, unknown>;
  status: "success" | "error" | "denied";
  result: Record<string, unknown> | null;
  error: string | null;
}

export interface AgentChatResponse {
  answer: string;
  findings: Array<{
    rule_id: string | null;
    severity: string;
    title: string;
    description: string;
    evidence: Array<Record<string, unknown>>;
    recommendation: string | null;
  }>;
  evidence: Array<{
    source: string;
    tool_name: string;
    summary: string;
    data: Record<string, unknown>;
    observed: boolean;
  }>;
  queries: Array<{
    tool_name: string;
    query: string;
    datasource: string;
    result_summary: string;
  }>;
  confidence: "high" | "medium" | "low";
  limitations: string[];
  recommendations: string[];
  tool_calls: ToolCallRecord[];
  sections: Record<string, string>;
}

"""PromQL/LogQL structural analysis (deterministic, no LLM)."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from app.schemas.analysis import AnalyzedQuery, StaticAnalysisFinding

_METRIC_RE = re.compile(
    r"(?<![A-Za-z0-9_:])([a-zA-Z_:][a-zA-Z0-9_:]*)\s*(?:\{|\(|\[|$)",
)
_LABEL_RE = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:=~|!~|=|!=)\s*([\'"].*?[\'"])')
_VAR_RE = re.compile(r"\$\{?([a-zA-Z_][a-zA-Z0-9_]*)\}?")
_FUNC_RE = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")
_RANGE_RE = re.compile(r"\[[^\]]+\]")
_KEYWORDS = {
    "by",
    "without",
    "on",
    "ignoring",
    "group_left",
    "group_right",
    "bool",
    "and",
    "or",
    "unless",
    "sum",
    "min",
    "max",
    "avg",
    "count",
    "stddev",
    "stdvar",
    "topk",
    "bottomk",
    "quantile",
    "rate",
    "increase",
    "irate",
    "histogram_quantile",
    "label_replace",
    "label_join",
    "abs",
    "clamp",
    "clamp_max",
    "clamp_min",
    "round",
    "floor",
    "ceil",
    "delta",
    "deriv",
    "predict_linear",
    "time",
    "vector",
    "scalar",
    "sort",
    "sort_desc",
    "count_values",
    "absent",
    "changes",
    "resets",
}


def normalize_query(raw_query: str) -> str:
    """Normalize formatting only; do not rewrite query semantics."""
    normalized = raw_query.strip()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"\s*,\s*", ", ", normalized)
    normalized = re.sub(r"\s*\{\s*", "{", normalized)
    normalized = re.sub(r"\s*\}\s*", "}", normalized)
    normalized = re.sub(r"\s*\[\s*", "[", normalized)
    normalized = re.sub(r"\s*\]\s*", "]", normalized)
    normalized = re.sub(r"\s*\(\s*", "(", normalized)
    normalized = re.sub(r"\s*\)\s*", ")", normalized)
    return normalized


def hash_query(normalized_query: str) -> str:
    return hashlib.sha256(normalized_query.encode("utf-8")).hexdigest()


def analyze_query(
    *,
    raw_query: str,
    panel_id: int,
    panel_title: str,
    ref_id: str | None = None,
    datasource_uid: str | None = None,
    query_language: str | None = None,
) -> AnalyzedQuery:
    normalized = normalize_query(raw_query)
    metrics = _extract_metrics(normalized)
    labels = sorted({match.group(1) for match in _LABEL_RE.finditer(normalized)})
    variables = sorted({match.group(1) for match in _VAR_RE.finditer(normalized)})
    functions = sorted(
        {
            match.group(1)
            for match in _FUNC_RE.finditer(normalized)
            if match.group(1) in _KEYWORDS or match.group(1).islower()
        }
    )
    ranges = sorted({match.group(0) for match in _RANGE_RE.finditer(normalized)})
    has_regex = bool(re.search(r"=~|!~", normalized))

    return AnalyzedQuery(
        panel_id=panel_id,
        panel_title=panel_title,
        ref_id=ref_id,
        datasource_uid=datasource_uid,
        query_language=query_language,
        raw_query=raw_query,
        normalized_query=normalized,
        query_hash=hash_query(normalized),
        referenced_metrics=metrics,
        referenced_labels=labels,
        referenced_variables=variables,
        functions=functions,
        range_vectors=ranges,
        has_regex_selector=has_regex,
    )


def static_query_findings(analyzed: AnalyzedQuery) -> list[StaticAnalysisFinding]:
    """Produce evidence-based static analysis recommendations."""
    findings: list[StaticAnalysisFinding] = []
    query = analyzed.normalized_query

    # Unnecessary regex: exact literal with =~ and no regex metacharacters.
    for match in re.finditer(
        r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=~\s*[\'"]([^\'"]+)[\'"]',
        query,
    ):
        label, value = match.group(1), match.group(2)
        if not re.search(r"[.\\+*?\[\](){|^$]", value) and ".*" not in value and ".+" not in value:
            findings.append(
                StaticAnalysisFinding(
                    rule_id="QUERY-002",
                    severity="info",
                    category="query_quality",
                    title="Regex selector may be unnecessary",
                    description=(
                        f"Label '{label}' uses =~ with a literal value '{value}'. "
                        "This is a static analysis recommendation, not a measured performance claim."
                    ),
                    evidence=[
                        {
                            "panel_id": analyzed.panel_id,
                            "query": analyzed.raw_query,
                            "label": label,
                            "value": value,
                        }
                    ],
                    recommendation=f'Prefer {label}="{value}" unless regex matching is required.',
                )
            )

    # Counter-like metric without rate/increase (heuristic).
    if (
        any(name.endswith("_total") or name.endswith("_count") for name in analyzed.referenced_metrics)
        and not any(fn in {"rate", "increase", "irate"} for fn in analyzed.functions)
        and analyzed.query_language in {None, "promql"}
    ):
        findings.append(
            StaticAnalysisFinding(
                rule_id="QUERY-003",
                severity="warning",
                category="query_quality",
                title="Possible counter without rate/increase",
                description=(
                    "Query references *_total/*_count metrics without rate()/increase()/irate()."
                ),
                evidence=[
                    {
                        "panel_id": analyzed.panel_id,
                        "metrics": analyzed.referenced_metrics,
                        "query": analyzed.raw_query,
                    }
                ],
                recommendation="Wrap counters with rate() or increase() over an appropriate window.",
            )
        )

    if re.search(r"avg\s*\(\s*(?:histogram_quantile|quantile)\s*\(", query, re.IGNORECASE):
        findings.append(
            StaticAnalysisFinding(
                rule_id="QUERY-004",
                severity="error",
                category="query_quality",
                title="Averaging quantiles is likely incorrect",
                description=(
                    "Query appears to average quantile results. "
                    "This is a static semantic recommendation."
                ),
                evidence=[{"panel_id": analyzed.panel_id, "query": analyzed.raw_query}],
                recommendation=(
                    "Aggregate histogram buckets first, then compute quantiles."
                ),
            )
        )

    return findings


def _extract_metrics(query: str) -> list[str]:
    metrics: set[str] = set()
    # Metric before selector: metric{...}
    for match in re.finditer(r"([a-zA-Z_:][a-zA-Z0-9_:]*)\s*\{", query):
        name = match.group(1)
        if name not in _KEYWORDS:
            metrics.add(name)
    # Bare metric tokens used with range vector: metric[5m]
    for match in re.finditer(r"([a-zA-Z_:][a-zA-Z0-9_:]*)\s*\[", query):
        name = match.group(1)
        if name not in _KEYWORDS:
            metrics.add(name)
    return sorted(metrics)


def analyzed_query_to_dict(analyzed: AnalyzedQuery) -> dict[str, Any]:
    return analyzed.model_dump()

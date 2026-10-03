"""Dashboard normalization from Grafana dashboard JSON."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.schemas.dashboard import (
    NormalizedDashboard,
    NormalizedPanel,
    NormalizedQuery,
    NormalizedVariable,
)


def hash_dashboard_json(raw_json: dict[str, Any]) -> str:
    """Return a stable SHA-256 hash of dashboard JSON."""
    encoded = json.dumps(raw_json, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def normalize_grafana_dashboard(
    payload: dict[str, Any],
    *,
    folder: str | None = None,
    url: str | None = None,
) -> NormalizedDashboard:
    """Normalize a Grafana `/api/dashboards/uid/{uid}` payload or bare dashboard JSON."""
    dashboard_obj = payload.get("dashboard")
    meta_obj = payload.get("meta")
    meta: dict[str, Any] = meta_obj if isinstance(meta_obj, dict) else {}

    if isinstance(dashboard_obj, dict):
        raw = dashboard_obj
    else:
        raw = payload
        meta = {}

    uid = str(raw.get("uid") or meta.get("uid") or "")
    if not uid:
        raise ValueError("Dashboard JSON is missing uid")

    title = str(raw.get("title") or uid)
    resolved_folder = folder
    if resolved_folder is None:
        folder_title = meta.get("folderTitle")
        resolved_folder = str(folder_title) if folder_title else None

    resolved_url = url
    if resolved_url is None:
        meta_url = meta.get("url")
        if meta_url:
            resolved_url = str(meta_url)

    panels = _extract_panels(raw.get("panels") or [])
    variables = _extract_variables(raw.get("templating") or {})
    links = [link for link in (raw.get("links") or []) if isinstance(link, dict)]

    return NormalizedDashboard(
        grafana_uid=uid,
        title=title,
        folder=resolved_folder,
        url=resolved_url,
        json_hash=hash_dashboard_json(raw),
        raw_json=raw,
        panels=panels,
        variables=variables,
        links=links,
    )


def _extract_panels(panels: list[Any], *, next_id: int = 1) -> list[NormalizedPanel]:
    extracted: list[NormalizedPanel] = []
    counter = next_id

    for panel in panels:
        if not isinstance(panel, dict):
            continue

        panel_type = str(panel.get("type") or "unknown")
        if panel_type == "row":
            nested = panel.get("panels") or []
            if nested:
                nested_panels, counter = _extract_panels_with_counter(nested, counter)
                extracted.extend(nested_panels)
            continue

        grafana_panel_id = panel.get("id")
        if not isinstance(grafana_panel_id, int):
            grafana_panel_id = counter
            counter += 1

        datasource_uid, _ = _parse_datasource(panel.get("datasource"))
        queries = _extract_queries(panel.get("targets") or [], default_ds=datasource_uid)
        transformations = [
            item for item in (panel.get("transformations") or []) if isinstance(item, dict)
        ]
        field_config_obj = panel.get("fieldConfig")
        field_config: dict[str, Any] = (
            field_config_obj if isinstance(field_config_obj, dict) else {}
        )

        extracted.append(
            NormalizedPanel(
                grafana_panel_id=grafana_panel_id,
                title=str(panel.get("title") or f"Panel {grafana_panel_id}"),
                panel_type=panel_type,
                datasource_uid=datasource_uid,
                queries=queries,
                transformations=transformations,
                field_config=field_config,
                raw_definition=panel,
            )
        )

        # Nested panels outside classic rows (some exporters nest panels).
        nested = panel.get("panels") or []
        if nested:
            nested_panels, counter = _extract_panels_with_counter(nested, counter)
            extracted.extend(nested_panels)

    return extracted


def _extract_panels_with_counter(
    panels: list[Any],
    counter: int,
) -> tuple[list[NormalizedPanel], int]:
    extracted = _extract_panels(panels, next_id=counter)
    used_ids = {panel.grafana_panel_id for panel in extracted}
    next_counter = max([counter, *used_ids], default=counter) + 1
    return extracted, next_counter


def _extract_queries(
    targets: list[Any],
    *,
    default_ds: str | None,
) -> list[NormalizedQuery]:
    queries: list[NormalizedQuery] = []
    for target in targets:
        if not isinstance(target, dict):
            continue
        raw_query = _target_query_text(target)
        if raw_query is None:
            continue
        ds_uid, ds_type = _parse_datasource(target.get("datasource"))
        query_language = _infer_query_language(ds_type, target)
        queries.append(
            NormalizedQuery(
                ref_id=str(target["refId"]) if target.get("refId") is not None else None,
                datasource_uid=ds_uid or default_ds,
                datasource_type=ds_type,
                query_language=query_language,
                raw_query=raw_query,
                expr=str(target["expr"]) if target.get("expr") is not None else None,
            )
        )
    return queries


def _target_query_text(target: dict[str, Any]) -> str | None:
    for key in ("expr", "expression", "query", "rawSql"):
        value = target.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _infer_query_language(ds_type: str | None, target: dict[str, Any]) -> str | None:
    if ds_type:
        lowered = ds_type.lower()
        if "prometheus" in lowered:
            return "promql"
        if "loki" in lowered:
            return "logql"
    if "expr" in target:
        return "promql"
    if "rawSql" in target:
        return "sql"
    return None


def _parse_datasource(value: Any) -> tuple[str | None, str | None]:
    if isinstance(value, str) and value:
        return value, None
    if isinstance(value, dict):
        uid = value.get("uid")
        ds_type = value.get("type")
        return (
            str(uid) if uid is not None else None,
            str(ds_type) if ds_type is not None else None,
        )
    return None, None


def _extract_variables(templating: Any) -> list[NormalizedVariable]:
    if not isinstance(templating, dict):
        return []
    items = templating.get("list") or []
    variables: list[NormalizedVariable] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not name:
            continue
        query = item.get("query")
        query_text: str | None
        if isinstance(query, dict):
            query_text = str(query.get("query") or query.get("expr") or "") or None
        elif query is None:
            query_text = None
        else:
            query_text = str(query)

        current = item.get("current")
        current_value: Any = None
        if isinstance(current, dict):
            current_value = current.get("value", current.get("text"))
        else:
            current_value = current

        variables.append(
            NormalizedVariable(
                name=str(name),
                label=str(item["label"]) if item.get("label") is not None else None,
                variable_type=str(item.get("type") or "unknown"),
                query=query_text,
                current_value=current_value,
                multi=bool(item.get("multi", False)),
                include_all=bool(item.get("includeAll", False)),
                raw_definition=item,
            )
        )
    return variables

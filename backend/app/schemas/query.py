"""Typed query request/response models for Prometheus and Loki."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class InstantQueryRequest(BaseModel):
    query: str = Field(min_length=1)
    time: str | float | None = None


class RangeQueryRequest(BaseModel):
    query: str = Field(min_length=1)
    start: str | float
    end: str | float
    step: str | float | None = None
    limit: int | None = Field(default=None, ge=1)


class PrometheusSample(BaseModel):
    metric: dict[str, str] = Field(default_factory=dict)
    value: tuple[float, str] | None = None
    values: list[tuple[float, str]] = Field(default_factory=list)


class PrometheusQueryResult(BaseModel):
    result_type: Literal["vector", "matrix", "scalar", "string"]
    result: list[PrometheusSample] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class MetricMetadata(BaseModel):
    metric: str
    type: str | None = None
    help: str | None = None
    unit: str | None = None


class SeriesSelector(BaseModel):
    labels: dict[str, str] = Field(default_factory=dict)


class LokiStream(BaseModel):
    stream: dict[str, str] = Field(default_factory=dict)
    values: list[tuple[str, str]] = Field(default_factory=list)


class LokiQueryResult(BaseModel):
    result_type: Literal["streams", "matrix", "vector"] | str
    result: list[LokiStream] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)

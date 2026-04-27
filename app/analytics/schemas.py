from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class FieldType(StrEnum):
    string = "string"
    number = "number"
    date = "date"


class Aggregation(StrEnum):
    count = "count"
    avg = "avg"
    sum = "sum"
    min = "min"
    max = "max"


class FilterOperator(StrEnum):
    eq = "eq"
    in_ = "in"
    gte = "gte"
    lte = "lte"
    contains = "contains"


class SortDirection(StrEnum):
    asc = "asc"
    desc = "desc"


class AnalyticsFieldResponse(BaseModel):
    id: str
    label: str
    type: FieldType
    groupable: bool
    filterable: bool
    aggregations: list[Aggregation] = Field(default_factory=list)


class MetricRequest(BaseModel):
    field: str
    aggregation: Aggregation


class FilterRequest(BaseModel):
    field: str
    operator: FilterOperator
    value: Any


class SortRequest(BaseModel):
    field: str
    direction: SortDirection = SortDirection.asc


class AnalyticsQueryRequest(BaseModel):
    metrics: list[MetricRequest] = Field(default_factory=list, max_length=2)
    dimensions: list[str] = Field(default_factory=list, max_length=2)
    filters: list[FilterRequest] = Field(default_factory=list)
    sort: list[SortRequest] = Field(default_factory=list, max_length=3)
    limit: int = Field(default=100, ge=1, le=500)


class AnalyticsColumnResponse(BaseModel):
    key: str
    label: str
    type: FieldType


class AnalyticsQueryResponse(BaseModel):
    columns: list[AnalyticsColumnResponse]
    rows: list[dict[str, Any]]


class RatingRequest(BaseModel):
    status: str | None = None
    military_specialty: str | None = None
    study_group: str | None = None
    fitness_category: str | None = None
    psycho_category: str | None = None
    limit: int = Field(default=100, ge=1, le=500)


class RatingRow(BaseModel):
    full_name: str | None = None
    study_group: str | None = None
    military_specialty: str | None = None
    status: str | None = None
    fitness_category: str | None = None
    psycho_category: str | None = None
    grade100: float | None = None
    total_points: int | None = None
    final_result: int | None = None


class RatingResponse(BaseModel):
    rows: list[RatingRow]

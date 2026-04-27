from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session

from app.analytics.catalog import AnalyticsField, get_field
from app.analytics.schemas import (
    Aggregation,
    AnalyticsColumnResponse,
    AnalyticsQueryRequest,
    AnalyticsQueryResponse,
    FieldType,
    FilterOperator,
    SortDirection,
)
from app.auth.schemas import UserRoleName
from app.models import (
    MilitaryAccountingSpecialty,
    MilitaryCommissariat,
    Platoon,
    Specialty,
    Student,
    StudyGroup,
)


def execute_analytics_query(
    session: Session,
    request: AnalyticsQueryRequest,
    role: UserRoleName,
) -> AnalyticsQueryResponse:
    if not request.metrics and not request.dimensions:
        raise _bad_request("At least one metric or dimension is required")

    dimensions = [_resolve_dimension(field_id, role) for field_id in request.dimensions]
    metrics = [_build_metric(metric.field, metric.aggregation, role) for metric in request.metrics]

    select_items: list[ColumnElement[Any]] = []
    columns: list[AnalyticsColumnResponse] = []
    output_expressions: dict[str, ColumnElement[Any]] = {}

    for field_item in dimensions:
        expression = field_item.expression().label(field_item.id)
        select_items.append(expression)
        output_expressions[field_item.id] = expression
        columns.append(
            AnalyticsColumnResponse(
                key=field_item.id,
                label=field_item.label,
                type=field_item.type,
            )
        )

    for key, label, field_type, expression in metrics:
        labeled_expression = expression.label(key)
        select_items.append(labeled_expression)
        output_expressions[key] = labeled_expression
        columns.append(
            AnalyticsColumnResponse(key=key, label=label, type=field_type)
        )

    statement = select(*select_items).select_from(Student)
    statement = _apply_joins(statement, _collect_joins(request, role))
    statement = _apply_filters(statement, request, role)

    if dimensions:
        statement = statement.group_by(*(field_item.expression() for field_item in dimensions))

    statement = _apply_sort(statement, request, output_expressions)
    statement = statement.limit(request.limit)

    rows = [dict(row) for row in session.execute(statement).mappings().all()]
    return AnalyticsQueryResponse(columns=columns, rows=rows)


def _resolve_dimension(field_id: str, role: UserRoleName) -> AnalyticsField:
    field_item = get_field(field_id, role)
    if field_item is None:
        raise _bad_request(f"Unknown or inaccessible field: {field_id}")
    if not field_item.groupable:
        raise _bad_request(f"Field cannot be used as a dimension: {field_id}")
    return field_item


def _build_metric(
    field_id: str,
    aggregation: Aggregation,
    role: UserRoleName,
) -> tuple[str, str, FieldType, ColumnElement[Any]]:
    field_item = get_field(field_id, role)
    if field_item is None:
        raise _bad_request(f"Unknown or inaccessible field: {field_id}")
    if aggregation not in field_item.aggregations:
        raise _bad_request(f"Aggregation {aggregation} is not allowed for {field_id}")

    expression = field_item.expression()
    if aggregation == Aggregation.count:
        metric_expression = func.count(expression)
    elif aggregation == Aggregation.avg:
        metric_expression = func.avg(expression)
    elif aggregation == Aggregation.sum:
        metric_expression = func.sum(expression)
    elif aggregation == Aggregation.min:
        metric_expression = func.min(expression)
    elif aggregation == Aggregation.max:
        metric_expression = func.max(expression)
    else:
        raise _bad_request(f"Unsupported aggregation: {aggregation}")

    key = field_id if aggregation == Aggregation.count else f"{aggregation.value}_{field_id}"
    label = field_item.label if aggregation == Aggregation.count else (
        f"{_aggregation_label(aggregation)}: {field_item.label}"
    )
    return key, label, FieldType.number, metric_expression


def _collect_joins(request: AnalyticsQueryRequest, role: UserRoleName) -> set[str]:
    joins: set[str] = set()
    requested_fields = [
        *request.dimensions,
        *(metric.field for metric in request.metrics),
        *(filter_item.field for filter_item in request.filters),
    ]
    for field_id in requested_fields:
        field_item = get_field(field_id, role)
        if field_item is not None:
            joins.update(field_item.joins)
    return joins


def _apply_joins(statement: Select[Any], joins: set[str]) -> Select[Any]:
    if "study_group" in joins or "specialty" in joins:
        statement = statement.outerjoin(
            StudyGroup,
            Student.study_group_id == StudyGroup.id_group,
        )
    if "specialty" in joins:
        statement = statement.outerjoin(
            Specialty,
            StudyGroup.specialty_id == Specialty.id_specialty,
        )
    if "military_specialty" in joins:
        statement = statement.outerjoin(
            MilitaryAccountingSpecialty,
            Student.military_accounting_specialty_id
            == MilitaryAccountingSpecialty.id_military_accounting_specialty,
        )
    if "military_commissariat" in joins:
        statement = statement.outerjoin(
            MilitaryCommissariat,
            Student.military_commissariat_id
            == MilitaryCommissariat.id_military_commissariat,
        )
    if "platoon" in joins:
        statement = statement.outerjoin(Platoon, Student.platoon_id == Platoon.id)
    return statement


def _apply_filters(
    statement: Select[Any],
    request: AnalyticsQueryRequest,
    role: UserRoleName,
) -> Select[Any]:
    for filter_item in request.filters:
        field_item = get_field(filter_item.field, role)
        if field_item is None:
            raise _bad_request(f"Unknown or inaccessible filter field: {filter_item.field}")
        if not field_item.filterable:
            raise _bad_request(f"Field cannot be filtered: {filter_item.field}")

        expression = field_item.expression()
        operator = filter_item.operator
        value = filter_item.value

        if operator == FilterOperator.eq:
            statement = statement.where(expression == value)
        elif operator == FilterOperator.in_:
            if not isinstance(value, list):
                raise _bad_request("Operator 'in' expects a list value")
            statement = statement.where(expression.in_(value))
        elif operator == FilterOperator.gte:
            statement = statement.where(expression >= value)
        elif operator == FilterOperator.lte:
            statement = statement.where(expression <= value)
        elif operator == FilterOperator.contains:
            statement = statement.where(expression.ilike(f"%{value}%"))
        else:
            raise _bad_request(f"Unsupported filter operator: {operator}")

    return statement


def _apply_sort(
    statement: Select[Any],
    request: AnalyticsQueryRequest,
    output_expressions: dict[str, ColumnElement[Any]],
) -> Select[Any]:
    for sort_item in request.sort:
        expression = output_expressions.get(sort_item.field)
        if expression is None:
            raise _bad_request(f"Sort field must be selected: {sort_item.field}")
        statement = statement.order_by(
            expression.desc()
            if sort_item.direction == SortDirection.desc
            else expression.asc()
        )
    return statement


def _aggregation_label(aggregation: Aggregation) -> str:
    labels = {
        Aggregation.avg: "Среднее",
        Aggregation.sum: "Сумма",
        Aggregation.min: "Минимум",
        Aggregation.max: "Максимум",
        Aggregation.count: "Количество",
    }
    return labels[aggregation]


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

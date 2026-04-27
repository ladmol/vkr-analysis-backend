from decimal import Decimal
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
    DetailQueryRequest,
    FieldType,
    FilterRequest,
    FilterOperator,
    SortDirection,
    SortRequest,
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
    _validate_request_shape(request)

    dimensions = [_resolve_dimension(field_id, role) for field_id in request.dimensions]
    metrics = [_build_metric(metric.field, metric.aggregation, role) for metric in request.metrics]

    select_items: list[ColumnElement[Any]] = []
    columns: list[AnalyticsColumnResponse] = []
    output_expressions: dict[str, ColumnElement[Any]] = {}

    dimension_group_expressions: list[ColumnElement[Any]] = []

    for field_item in dimensions:
        group_expression = field_item.expression()
        labeled_expression = group_expression.label(field_item.id)
        dimension_group_expressions.append(group_expression)
        select_items.append(labeled_expression)
        output_expressions[field_item.id] = labeled_expression
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
        statement = statement.group_by(*dimension_group_expressions)

    statement = _apply_sort(statement, request, output_expressions)
    statement = statement.limit(request.limit)

    rows = [_normalize_row(dict(row)) for row in session.execute(statement).mappings().all()]
    return AnalyticsQueryResponse(columns=columns, rows=rows)


def execute_summary_query(
    session: Session,
    request: AnalyticsQueryRequest,
    role: UserRoleName,
) -> AnalyticsQueryResponse:
    return execute_analytics_query(session, request, role)


def execute_detail_query(
    session: Session,
    request: DetailQueryRequest,
    role: UserRoleName,
) -> AnalyticsQueryResponse:
    _validate_detail_request_shape(request)

    columns: list[AnalyticsColumnResponse] = []
    select_items: list[ColumnElement[Any]] = []
    output_expressions: dict[str, ColumnElement[Any]] = {}

    for field_id in request.columns:
        field_item = _resolve_detail_column(field_id, role)
        labeled_expression = field_item.expression().label(field_item.id)
        select_items.append(labeled_expression)
        output_expressions[field_item.id] = labeled_expression
        columns.append(
            AnalyticsColumnResponse(
                key=field_item.id,
                label=field_item.label,
                type=field_item.type,
            )
        )

    statement = select(*select_items).select_from(Student)
    statement = _apply_joins(statement, _collect_detail_joins(request, role))
    statement = _apply_filter_items(statement, request.filters, role)
    statement = _apply_detail_sort(statement, request.sort, output_expressions, role)
    statement = statement.limit(request.limit)

    rows = [_normalize_row(dict(row)) for row in session.execute(statement).mappings().all()]
    return AnalyticsQueryResponse(columns=columns, rows=rows)


def get_field_values(
    session: Session,
    field_id: str,
    role: UserRoleName,
    limit: int = 100,
) -> list[Any]:
    field_item = get_field(field_id, role)
    if field_item is None:
        raise _bad_request(f"Unknown or inaccessible field: {field_id}")
    if not field_item.filterable:
        raise _bad_request(f"Field cannot be filtered: {field_id}")

    expression = field_item.expression().label("value")
    statement = (
        select(expression)
        .select_from(Student)
        .distinct()
        .where(expression.is_not(None))
        .order_by(expression.asc())
        .limit(limit)
    )
    statement = _apply_joins(statement, set(field_item.joins))

    return [
        _normalize_value(row["value"])
        for row in session.execute(statement).mappings().all()
    ]


def _resolve_dimension(field_id: str, role: UserRoleName) -> AnalyticsField:
    field_item = get_field(field_id, role)
    if field_item is None:
        raise _bad_request(f"Unknown or inaccessible field: {field_id}")
    if not field_item.groupable:
        raise _bad_request(f"Field cannot be used as a dimension: {field_id}")
    return field_item


def _resolve_detail_column(field_id: str, role: UserRoleName) -> AnalyticsField:
    field_item = get_field(field_id, role)
    if field_item is None:
        raise _bad_request(f"Unknown or inaccessible field: {field_id}")
    if not field_item.displayable:
        raise _bad_request(f"Field cannot be displayed: {field_id}")
    return field_item


def _validate_request_shape(request: AnalyticsQueryRequest) -> None:
    if not request.metrics and not request.dimensions:
        raise _bad_request("At least one metric or dimension is required")

    if len(request.dimensions) != len(set(request.dimensions)):
        raise _bad_request("Dimensions must be unique")

    metric_keys = [
        metric.field if metric.aggregation == Aggregation.count else (
            f"{metric.aggregation.value}_{metric.field}"
        )
        for metric in request.metrics
    ]
    if len(metric_keys) != len(set(metric_keys)):
        raise _bad_request("Metrics must be unique")

    selected_keys = {*request.dimensions, *metric_keys}
    if len(selected_keys) != len(request.dimensions) + len(metric_keys):
        raise _bad_request("Selected dimensions and metrics must have unique keys")


def _validate_detail_request_shape(request: DetailQueryRequest) -> None:
    if len(request.columns) != len(set(request.columns)):
        raise _bad_request("Columns must be unique")


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


def _collect_detail_joins(request: DetailQueryRequest, role: UserRoleName) -> set[str]:
    joins: set[str] = set()
    requested_fields = [
        *request.columns,
        *(filter_item.field for filter_item in request.filters),
        *(sort_item.field for sort_item in request.sort),
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
    return _apply_filter_items(statement, request.filters, role)


def _apply_filter_items(
    statement: Select[Any],
    filters: list[FilterRequest],
    role: UserRoleName,
) -> Select[Any]:
    for filter_item in filters:
        field_item = get_field(filter_item.field, role)
        if field_item is None:
            raise _bad_request(f"Unknown or inaccessible filter field: {filter_item.field}")
        if not field_item.filterable:
            raise _bad_request(f"Field cannot be filtered: {filter_item.field}")
        _validate_filter_operator(field_item, filter_item.operator)

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


def _validate_filter_operator(
    field_item: AnalyticsField,
    operator: FilterOperator,
) -> None:
    if operator == FilterOperator.contains and field_item.type != FieldType.string:
        raise _bad_request("Operator 'contains' is allowed only for string fields")

    if operator in {FilterOperator.gte, FilterOperator.lte} and field_item.type == FieldType.string:
        raise _bad_request("Range operators are not allowed for string fields")


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


def _apply_detail_sort(
    statement: Select[Any],
    sort_items: list[SortRequest],
    output_expressions: dict[str, ColumnElement[Any]],
    role: UserRoleName,
) -> Select[Any]:
    for sort_item in sort_items:
        expression = output_expressions.get(sort_item.field)
        if expression is None:
            field_item = get_field(sort_item.field, role)
            if field_item is None:
                raise _bad_request(f"Unknown or inaccessible sort field: {sort_item.field}")
            if not field_item.displayable:
                raise _bad_request(f"Field cannot be sorted in detail mode: {sort_item.field}")
            expression = field_item.expression()

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


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _normalize_value(value)
        for key, value in row.items()
    }


def _normalize_value(value: Any) -> Any:
    return float(value) if isinstance(value, Decimal) else value


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

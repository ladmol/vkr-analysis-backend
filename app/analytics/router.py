from fastapi import APIRouter, Depends, Response
from sqlmodel import Session

from app.analytics.catalog import get_accessible_fields
from app.analytics.export import analytics_response_to_xlsx, rating_response_to_xlsx
from app.analytics.query_builder import execute_analytics_query
from app.analytics.rating import get_rating
from app.analytics.schemas import (
    AnalyticsFieldResponse,
    AnalyticsQueryRequest,
    AnalyticsQueryResponse,
    RatingRequest,
    RatingResponse,
)
from app.auth.dependencies import get_current_user
from app.auth.schemas import CurrentUser
from app.db.session import get_session


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/fields", response_model=list[AnalyticsFieldResponse])
def list_fields(
    current_user: CurrentUser = Depends(get_current_user),
) -> list[AnalyticsFieldResponse]:
    fields = get_accessible_fields(current_user.role)
    return [field_item.to_response() for field_item in fields.values()]


@router.post("/query", response_model=AnalyticsQueryResponse)
def query_analytics(
    payload: AnalyticsQueryRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> AnalyticsQueryResponse:
    return execute_analytics_query(session, payload, current_user.role)


@router.post("/query/export/xlsx")
def export_query_xlsx(
    payload: AnalyticsQueryRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    result = execute_analytics_query(session, payload, current_user.role)
    content = analytics_response_to_xlsx(result)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="analytics-report.xlsx"'},
    )


@router.post("/rating", response_model=RatingResponse)
def rating(
    payload: RatingRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> RatingResponse:
    return get_rating(session, payload, current_user.role)


@router.post("/rating/export/xlsx")
def export_rating_xlsx(
    payload: RatingRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    result = get_rating(session, payload, current_user.role)
    content = rating_response_to_xlsx(result)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="rating.xlsx"'},
    )

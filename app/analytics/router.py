from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.analytics.catalog import get_accessible_fields
from app.analytics.query_builder import execute_analytics_query
from app.analytics.schemas import (
    AnalyticsFieldResponse,
    AnalyticsQueryRequest,
    AnalyticsQueryResponse,
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

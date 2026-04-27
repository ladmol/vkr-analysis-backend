import pytest
from fastapi import HTTPException

from app.analytics.catalog import get_accessible_fields
from app.analytics.query_builder import execute_analytics_query
from app.analytics.schemas import AnalyticsQueryRequest
from app.auth.schemas import UserRoleName


def test_observer_cannot_access_full_name():
    fields = get_accessible_fields(UserRoleName.observer)

    assert "full_name" not in fields
    assert "student_count" in fields


def test_empty_analytics_query_is_rejected_before_db_access():
    with pytest.raises(HTTPException) as exc_info:
        execute_analytics_query(
            session=None,
            request=AnalyticsQueryRequest(),
            role=UserRoleName.admin,
        )

    assert exc_info.value.status_code == 400

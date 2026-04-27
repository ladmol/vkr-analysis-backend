from collections.abc import Generator

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.db.session import engine
from app.main import app


TEST_PASSWORD = "admin"


@pytest.fixture(scope="module")
def db_session() -> Generator[Session, None, None]:
    try:
        with Session(engine) as session:
            session.exec(text("SELECT 1"))
            yield session
    except SQLAlchemyError as exc:
        pytest.skip(f"PostgreSQL test database is not available: {exc}")


@pytest.fixture()
def seeded_db(db_session: Session) -> Generator[None, None, None]:
    cleanup_test_data(db_session)
    seed_test_data(db_session)
    db_session.commit()

    yield

    cleanup_test_data(db_session)
    db_session.commit()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_login_and_me_against_real_database(
    seeded_db: None,
    client: TestClient,
):
    login_response = client.post(
        "/auth/login",
        json={"login": "pytest_admin", "password": TEST_PASSWORD},
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["login"] == "pytest_admin"
    assert me_response.json()["role"] == "admin"


def test_analytics_query_against_real_database(
    seeded_db: None,
    client: TestClient,
):
    token = login(client)

    fields_response = client.get(
        "/analytics/fields",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fields_response.status_code == 200
    field_ids = {field["id"] for field in fields_response.json()}
    assert {"student_count", "military_specialty", "status"} <= field_ids

    query_response = client.post(
        "/analytics/query",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "metrics": [{"field": "student_count", "aggregation": "count"}],
            "dimensions": ["military_specialty"],
            "filters": [
                {"field": "status", "operator": "eq", "value": "PYTEST"}
            ],
            "sort": [{"field": "student_count", "direction": "desc"}],
            "limit": 10,
        },
    )

    assert query_response.status_code == 200
    payload = query_response.json()
    assert payload["columns"] == [
        {"key": "military_specialty", "label": "ВУС", "type": "string"},
        {"key": "student_count", "label": "Количество", "type": "number"},
    ]
    assert payload["rows"] == [
        {"military_specialty": "Pytest ВУС", "student_count": 2}
    ]


def test_full_name_dimension_query_against_real_database(
    seeded_db: None,
    client: TestClient,
):
    token = login(client)

    query_response = client.post(
        "/analytics/query",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "metrics": [{"field": "student_count", "aggregation": "count"}],
            "dimensions": ["full_name"],
            "filters": [
                {"field": "status", "operator": "eq", "value": "PYTEST"}
            ],
            "sort": [{"field": "student_count", "direction": "desc"}],
            "limit": 10,
        },
    )

    assert query_response.status_code == 200
    payload = query_response.json()
    assert payload["columns"] == [
        {"key": "full_name", "label": "ФИО", "type": "string"},
        {"key": "student_count", "label": "Количество", "type": "number"},
    ]
    assert {row["full_name"] for row in payload["rows"]} == {
        "Первый Тест Тестович",
        "Второй Тест Тестович",
    }


def test_rating_endpoint_returns_sorted_rows(
    seeded_db: None,
    client: TestClient,
):
    token = login(client)

    response = client.post(
        "/analytics/rating",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "PYTEST", "limit": 10},
    )

    assert response.status_code == 200
    rows = response.json()["rows"]
    assert [row["final_result"] for row in rows] == [180, 170]
    assert rows[0]["full_name"] == "Второй Тест Тестович"


def test_analytics_query_xlsx_export(
    seeded_db: None,
    client: TestClient,
):
    token = login(client)

    response = client.post(
        "/analytics/query/export/xlsx",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "metrics": [{"field": "student_count", "aggregation": "count"}],
            "dimensions": ["military_specialty"],
            "filters": [
                {"field": "status", "operator": "eq", "value": "PYTEST"}
            ],
            "sort": [{"field": "student_count", "direction": "desc"}],
            "limit": 10,
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert response.content.startswith(b"PK")


def test_rating_xlsx_export(
    seeded_db: None,
    client: TestClient,
):
    token = login(client)

    response = client.post(
        "/analytics/rating/export/xlsx",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "PYTEST", "limit": 10},
    )

    assert response.status_code == 200
    assert response.content.startswith(b"PK")


def login(client: TestClient) -> str:
    response = client.post(
        "/auth/login",
        json={"login": "pytest_admin", "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def seed_test_data(session: Session) -> None:
    password_hash = bcrypt.hashpw(
        TEST_PASSWORD.encode("utf-8"),
        bcrypt.gensalt(rounds=4),
    ).decode("utf-8")

    session.exec(
        text(
            """
            INSERT INTO users (login, password)
            VALUES ('pytest_admin', :password_hash)
            ON CONFLICT (login) DO UPDATE
            SET password = EXCLUDED.password
            """
        ),
        params={"password_hash": password_hash},
    )
    session.exec(
        text(
            """
            DELETE FROM user_roles
            WHERE user_id = (SELECT id_user FROM users WHERE login = 'pytest_admin')
            """
        )
    )
    session.exec(
        text(
            """
            INSERT INTO user_roles (user_authority, user_id)
            SELECT 0, id_user
            FROM users
            WHERE login = 'pytest_admin'
            """
        )
    )
    session.exec(
        text(
            """
            INSERT INTO military_accounting_specialty (code, title)
            VALUES ('PYTEST', 'Pytest ВУС')
            ON CONFLICT (code) DO UPDATE
            SET title = EXCLUDED.title
            """
        )
    )
    session.exec(
        text(
            """
            INSERT INTO specialty (code_specialty, title_specialty, institute)
            VALUES ('00.00.01', 'Pytest направление', 'TEST')
            ON CONFLICT (code_specialty) DO UPDATE
            SET title_specialty = EXCLUDED.title_specialty,
                institute = EXCLUDED.institute
            """
        )
    )
    session.exec(
        text(
            """
            INSERT INTO study_group (name_group, course, specialty_id)
            SELECT 'PYTEST-1', 1, id_specialty
            FROM specialty
            WHERE code_specialty = '00.00.01'
            ON CONFLICT (name_group) DO UPDATE
            SET course = EXCLUDED.course,
                specialty_id = EXCLUDED.specialty_id
            """
        )
    )
    session.exec(
        text(
            """
            INSERT INTO military_commissariat (name_military_commissariat)
            VALUES ('Pytest военкомат')
            ON CONFLICT (name_military_commissariat) DO NOTHING
            """
        )
    )
    session.exec(
        text(
            """
            INSERT INTO student (
                first_name,
                last_name,
                patronymic,
                course,
                study_group_id,
                military_commissariat_id,
                military_accounting_specialty_id,
                note_student,
                status,
                total_points,
                final_result,
                medical_result,
                fitness_category,
                psycho_category,
                grade5,
                grade100
            )
            SELECT
                data.first_name,
                data.last_name,
                'Тестович',
                1,
                study_group.id_group,
                military_commissariat.id_military_commissariat,
                military_accounting_specialty.id_military_accounting_specialty,
                'pytest-seed',
                'PYTEST',
                data.total_points,
                data.final_result,
                'годен',
                'А',
                'I',
                data.grade5,
                data.grade100
            FROM (
                VALUES
                    ('Тест', 'Первый', 120, 170, 4.20::numeric, 60.00::numeric),
                    ('Тест', 'Второй', 130, 180, 4.60::numeric, 80.00::numeric)
            ) AS data(
                first_name,
                last_name,
                total_points,
                final_result,
                grade5,
                grade100
            )
            JOIN study_group ON study_group.name_group = 'PYTEST-1'
            JOIN military_commissariat
                ON military_commissariat.name_military_commissariat = 'Pytest военкомат'
            JOIN military_accounting_specialty
                ON military_accounting_specialty.code = 'PYTEST'
            """
        )
    )


def cleanup_test_data(session: Session) -> None:
    session.exec(text("DELETE FROM student WHERE note_student = 'pytest-seed'"))
    session.exec(
        text(
            """
            DELETE FROM user_roles
            WHERE user_id IN (SELECT id_user FROM users WHERE login = 'pytest_admin')
            """
        )
    )
    session.exec(text("DELETE FROM users WHERE login = 'pytest_admin'"))

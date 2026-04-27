from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlmodel import Session

from app.analytics.schemas import RatingRequest, RatingResponse, RatingRow
from app.auth.schemas import UserRoleName
from app.models import MilitaryAccountingSpecialty, Student, StudyGroup


def get_rating(
    session: Session,
    request: RatingRequest,
    role: UserRoleName,
) -> RatingResponse:
    full_name = func.concat_ws(
        " ",
        Student.last_name,
        Student.first_name,
        Student.patronymic,
    ).label("full_name")

    statement = (
        select(
            full_name,
            StudyGroup.name_group.label("study_group"),
            MilitaryAccountingSpecialty.title.label("military_specialty"),
            Student.status,
            Student.fitness_category,
            Student.psycho_category,
            Student.grade100,
            Student.total_points,
            Student.final_result,
        )
        .select_from(Student)
        .outerjoin(StudyGroup, Student.study_group_id == StudyGroup.id_group)
        .outerjoin(
            MilitaryAccountingSpecialty,
            Student.military_accounting_specialty_id
            == MilitaryAccountingSpecialty.id_military_accounting_specialty,
        )
        .order_by(Student.final_result.desc().nullslast())
        .limit(request.limit)
    )
    statement = _apply_rating_filters(statement, request)

    rows = []
    for row in session.execute(statement).mappings().all():
        row_dict = dict(row)
        if role == UserRoleName.observer:
            row_dict["full_name"] = None
        if isinstance(row_dict.get("grade100"), Decimal):
            row_dict["grade100"] = float(row_dict["grade100"])
        rows.append(RatingRow(**row_dict))
    return RatingResponse(rows=rows)


def _apply_rating_filters(
    statement: Select,
    request: RatingRequest,
) -> Select:
    if request.status:
        statement = statement.where(Student.status == request.status)
    if request.military_specialty:
        statement = statement.where(MilitaryAccountingSpecialty.title == request.military_specialty)
    if request.study_group:
        statement = statement.where(StudyGroup.name_group == request.study_group)
    if request.fitness_category:
        statement = statement.where(Student.fitness_category == request.fitness_category)
    if request.psycho_category:
        statement = statement.where(Student.psycho_category == request.psycho_category)
    return statement

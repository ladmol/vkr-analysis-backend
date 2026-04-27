from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import ColumnElement, func, literal_column

from app.analytics.schemas import Aggregation, AnalyticsFieldResponse, FieldType
from app.auth.schemas import UserRoleName
from app.models import (
    MilitaryAccountingSpecialty,
    MilitaryCommissariat,
    Platoon,
    Specialty,
    Student,
    StudyGroup,
)


ExpressionFactory = Callable[[], ColumnElement[Any]]


@dataclass(frozen=True)
class AnalyticsField:
    id: str
    label: str
    type: FieldType
    expression: ExpressionFactory
    joins: tuple[str, ...] = ()
    displayable: bool = False
    groupable: bool = False
    filterable: bool = False
    aggregations: tuple[Aggregation, ...] = ()
    roles: set[UserRoleName] = field(
        default_factory=lambda: {
            UserRoleName.admin,
            UserRoleName.operator,
            UserRoleName.observer,
        }
    )

    def to_response(self) -> AnalyticsFieldResponse:
        return AnalyticsFieldResponse(
            id=self.id,
            label=self.label,
            type=self.type,
            displayable=self.displayable,
            groupable=self.groupable,
            filterable=self.filterable,
            aggregations=list(self.aggregations),
        )


def full_name_expression() -> ColumnElement[Any]:
    return func.concat_ws(
        literal_column("' '"),
        Student.last_name,
        Student.first_name,
        Student.patronymic,
    )


CATALOG: dict[str, AnalyticsField] = {
    "student_count": AnalyticsField(
        id="student_count",
        label="Количество",
        type=FieldType.number,
        expression=lambda: Student.id_student,
        aggregations=(Aggregation.count,),
    ),
    "full_name": AnalyticsField(
        id="full_name",
        label="ФИО",
        type=FieldType.string,
        expression=full_name_expression,
        displayable=True,
        filterable=True,
        roles={UserRoleName.admin, UserRoleName.operator},
    ),
    "status": AnalyticsField(
        id="status",
        label="Статус",
        type=FieldType.string,
        expression=lambda: Student.status,
        displayable=True,
        groupable=True,
        filterable=True,
    ),
    "course": AnalyticsField(
        id="course",
        label="Курс",
        type=FieldType.number,
        expression=lambda: StudyGroup.course,
        joins=("study_group",),
        displayable=True,
        groupable=True,
        filterable=True,
    ),
    "student_course": AnalyticsField(
        id="student_course",
        label="Курс студента",
        type=FieldType.number,
        expression=lambda: Student.course,
        displayable=True,
        groupable=True,
        filterable=True,
    ),
    "study_group": AnalyticsField(
        id="study_group",
        label="Учебная группа",
        type=FieldType.string,
        expression=lambda: StudyGroup.name_group,
        joins=("study_group",),
        displayable=True,
        groupable=True,
        filterable=True,
    ),
    "institute": AnalyticsField(
        id="institute",
        label="Институт",
        type=FieldType.string,
        expression=lambda: Specialty.institute,
        joins=("study_group", "specialty"),
        displayable=True,
        groupable=True,
        filterable=True,
    ),
    "specialty": AnalyticsField(
        id="specialty",
        label="Направление подготовки",
        type=FieldType.string,
        expression=lambda: Specialty.title_specialty,
        joins=("study_group", "specialty"),
        displayable=True,
        groupable=True,
        filterable=True,
    ),
    "military_specialty": AnalyticsField(
        id="military_specialty",
        label="ВУС",
        type=FieldType.string,
        expression=lambda: MilitaryAccountingSpecialty.title,
        joins=("military_specialty",),
        displayable=True,
        groupable=True,
        filterable=True,
    ),
    "military_commissariat": AnalyticsField(
        id="military_commissariat",
        label="Военный комиссариат",
        type=FieldType.string,
        expression=lambda: MilitaryCommissariat.name_military_commissariat,
        joins=("military_commissariat",),
        displayable=True,
        groupable=True,
        filterable=True,
    ),
    "platoon": AnalyticsField(
        id="platoon",
        label="Взвод",
        type=FieldType.string,
        expression=lambda: Platoon.name_platoon,
        joins=("platoon",),
        displayable=True,
        groupable=True,
        filterable=True,
    ),
    "medical_result": AnalyticsField(
        id="medical_result",
        label="Результат медосвидетельствования",
        type=FieldType.string,
        expression=lambda: Student.medical_result,
        displayable=True,
        groupable=True,
        filterable=True,
    ),
    "fitness_category": AnalyticsField(
        id="fitness_category",
        label="Категория годности",
        type=FieldType.string,
        expression=lambda: Student.fitness_category,
        displayable=True,
        groupable=True,
        filterable=True,
    ),
    "psycho_category": AnalyticsField(
        id="psycho_category",
        label="Категория профпригодности",
        type=FieldType.string,
        expression=lambda: Student.psycho_category,
        displayable=True,
        groupable=True,
        filterable=True,
    ),
    "grade100": AnalyticsField(
        id="grade100",
        label="Балл успеваемости",
        type=FieldType.number,
        expression=lambda: Student.grade100,
        displayable=True,
        filterable=True,
        aggregations=(Aggregation.avg, Aggregation.min, Aggregation.max),
    ),
    "final_result": AnalyticsField(
        id="final_result",
        label="Итоговый балл",
        type=FieldType.number,
        expression=lambda: Student.final_result,
        displayable=True,
        filterable=True,
        aggregations=(Aggregation.avg, Aggregation.sum, Aggregation.min, Aggregation.max),
    ),
    "total_points": AnalyticsField(
        id="total_points",
        label="Сумма баллов физподготовки",
        type=FieldType.number,
        expression=lambda: Student.total_points,
        displayable=True,
        filterable=True,
        aggregations=(Aggregation.avg, Aggregation.sum, Aggregation.min, Aggregation.max),
    ),
    "strength_points": AnalyticsField(
        id="strength_points",
        label="Баллы за силу",
        type=FieldType.number,
        expression=lambda: Student.strength_points,
        displayable=True,
        filterable=True,
        aggregations=(Aggregation.avg, Aggregation.sum, Aggregation.min, Aggregation.max),
    ),
    "speed_points": AnalyticsField(
        id="speed_points",
        label="Баллы за быстроту",
        type=FieldType.number,
        expression=lambda: Student.speed_points,
        displayable=True,
        filterable=True,
        aggregations=(Aggregation.avg, Aggregation.sum, Aggregation.min, Aggregation.max),
    ),
    "endurance_points": AnalyticsField(
        id="endurance_points",
        label="Баллы за выносливость",
        type=FieldType.number,
        expression=lambda: Student.endurance_points,
        displayable=True,
        filterable=True,
        aggregations=(Aggregation.avg, Aggregation.sum, Aggregation.min, Aggregation.max),
    ),
}


def get_accessible_fields(role: UserRoleName) -> dict[str, AnalyticsField]:
    return {field_id: item for field_id, item in CATALOG.items() if role in item.roles}


def get_field(field_id: str, role: UserRoleName) -> AnalyticsField | None:
    field_item = CATALOG.get(field_id)
    if field_item is None or role not in field_item.roles:
        return None
    return field_item

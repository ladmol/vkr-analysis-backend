from datetime import date
from decimal import Decimal

from sqlmodel import Field, SQLModel


class MilitaryAccountingSpecialty(SQLModel, table=True):
    __tablename__ = "military_accounting_specialty"

    id_military_accounting_specialty: int | None = Field(default=None, primary_key=True)
    code: str
    title: str


class MilitaryCommissariat(SQLModel, table=True):
    __tablename__ = "military_commissariat"

    id_military_commissariat: int | None = Field(default=None, primary_key=True)
    name_military_commissariat: str


class Platoon(SQLModel, table=True):
    __tablename__ = "platoon"

    id: int | None = Field(default=None, primary_key=True)
    name_platoon: str


class Specialty(SQLModel, table=True):
    __tablename__ = "specialty"

    id_specialty: int | None = Field(default=None, primary_key=True)
    code_specialty: str
    title_specialty: str
    institute: str


class StudyGroup(SQLModel, table=True):
    __tablename__ = "study_group"

    id_group: int | None = Field(default=None, primary_key=True)
    name_group: str
    course: int
    specialty_id: int = Field(foreign_key="specialty.id_specialty")


class User(SQLModel, table=True):
    __tablename__ = "users"

    id_user: int | None = Field(default=None, primary_key=True)
    login: str
    password: str


class UserRole(SQLModel, table=True):
    __tablename__ = "user_roles"

    id_user_role: int | None = Field(default=None, primary_key=True)
    user_authority: int | None = None
    user_id: int | None = Field(default=None, foreign_key="users.id_user")


class Student(SQLModel, table=True):
    __tablename__ = "student"

    id_student: int | None = Field(default=None, primary_key=True)
    first_name: str | None = None
    last_name: str | None = None
    patronymic: str | None = None
    birthday: date | None = None
    course: int | None = None
    study_group_id: int | None = Field(default=None, foreign_key="study_group.id_group")
    military_commissariat_id: int | None = Field(
        default=None,
        foreign_key="military_commissariat.id_military_commissariat",
    )
    military_accounting_specialty_id: int | None = Field(
        default=None,
        foreign_key="military_accounting_specialty.id_military_accounting_specialty",
    )
    student_id_card: str | None = None
    phone_number: str | None = None
    note_student: str | None = None
    status: str | None = None
    platoon_id: int | None = Field(default=None, foreign_key="platoon.id")
    strength_result: int | None = None
    strength_points: int | None = None
    speed_result: float | None = None
    speed_points: int | None = None
    endurance_result: float | None = None
    endurance_points: int | None = None
    total_points: int | None = None
    final_result: int | None = None
    strength_exercise_number: int | None = None
    speed_exercise_number: int | None = None
    endurance_exercise_number: int | None = None
    medical_result: str | None = None
    fitness_category: str | None = None
    psycho_category: str | None = None
    grade5: Decimal | None = None
    grade100: Decimal | None = None

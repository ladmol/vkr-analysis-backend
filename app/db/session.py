from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlmodel import Session

from app.core.config import get_settings


engine: Engine = create_engine(
    get_settings().sqlalchemy_database_url,
    pool_pre_ping=True,
)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.auth.schemas import TokenPayload, UserRoleName
from app.core.config import get_settings


ROLE_BY_AUTHORITY = {
    0: UserRoleName.admin,
    1: UserRoleName.operator,
    2: UserRoleName.observer,
}


def map_authority_to_role(authority: int | None) -> UserRoleName:
    return ROLE_BY_AUTHORITY.get(authority, UserRoleName.observer)


def verify_password(plain_password: str, stored_password: str) -> bool:
    password_bytes = plain_password.encode("utf-8")
    stored_bytes = stored_password.encode("utf-8")
    try:
        return bcrypt.checkpw(password_bytes, stored_bytes)
    except ValueError:
        # Existing external DB may contain plain demo passwords during MVP.
        return plain_password == stored_password


def create_access_token(user_id: int, role: UserRoleName) -> str:
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> TokenPayload | None:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return TokenPayload(sub=str(payload["sub"]), role=payload["role"])
    except (JWTError, KeyError, ValueError):
        return None

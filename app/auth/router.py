from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.auth.dependencies import get_current_user
from app.auth.schemas import CurrentUser, LoginRequest, TokenResponse
from app.auth.security import create_access_token, map_authority_to_role, verify_password
from app.db.session import get_session
from app.models import User, UserRole


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    user = session.exec(select(User).where(User.login == payload.login)).first()
    if user is None or not verify_password(payload.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login or password",
        )

    role_record = session.exec(
        select(UserRole).where(UserRole.user_id == user.id_user)
    ).first()
    role = map_authority_to_role(
        role_record.user_authority if role_record is not None else None
    )
    return TokenResponse(access_token=create_access_token(user.id_user, role))


@router.get("/me", response_model=CurrentUser)
def me(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return current_user

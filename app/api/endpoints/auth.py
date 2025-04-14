from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from api import deps
from core import security
from schemas.token import Token
from crud import crud_user
from schemas.user import UserCreate, User as UserSchema

router = APIRouter()


@router.post("/register", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
def register_user(
        *,
        db: Annotated[Session, Depends(deps.get_db)],
        user_in: UserCreate,
):
    user = crud_user.get_user_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Такой пользователь уже существует.",
        )

    user = crud_user.create_user(db=db, user=user_in)
    return user


@router.post("/login", response_model=Token)
def login_for_access_token(

        db: Annotated[Session, Depends(deps.get_db)],
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    user = crud_user.get_user_by_email(db, email=form_data.username)

    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверная почта или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    elif not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неактивный пользователь")

    access_token = security.create_access_token(
        subject=user.email
    )

    return {"access_token": access_token, "token_type": "bearer"}

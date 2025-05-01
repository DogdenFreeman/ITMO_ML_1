from typing import Generator, Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError
import logging

from db.models.user import User
from db.base import get_db
from schemas.token import TokenData
from core.config import settings
from core import security
from crud import crud_user


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

logger = logging.getLogger(__name__)


async def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    logger.debug("Попытка получить текущего пользователя по токену.")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось подтвердить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = security.decode_access_token(token)
        logger.debug(f"Payload токена: {payload}")
        if payload is None:
            logger.warning("Payload токена пустой или некорректный.")
            raise credentials_exception
        email: str | None = payload.get("sub")
        if email is None:
            logger.warning("В Payload токена отсутствует email ('sub').")
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        logger.exception("JWTError при декодировании токена")
        raise credentials_exception
    except Exception as e:
        logger.exception(f"Непредвиденная ошибка при обработке токена: {e}")
        raise credentials_exception

    user = crud_user.get_user_by_email(db, email=token_data.email)
    if user is None:
        logger.warning(f"Пользователь с email '{token_data.email}' из токена не найден в БД.")
        raise credentials_exception
    if not user.is_active:
        logger.warning(f"Пользователь {user.email} из токена неактивен.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    logger.debug(f"Пользователь {user.email} успешно аутентифицирован.")
    return user


async def get_current_active_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_superuser:
        logger.warning(f"Пользователь {current_user.email} попытался получить доступ к ресурсам суперпользователя.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )
    logger.debug(f"Суперпользователь {current_user.email} успешно аутентифицирован.")
    return current_user
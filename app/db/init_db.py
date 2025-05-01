from sqlalchemy.orm import Session
from db import base
from db.models.user import User
from core.config import settings
from core.security import get_password_hash
import logging


logger = logging.getLogger(__name__)


def init_db(db: Session) -> None:
    logger.info("Попытка создания таблиц базы данных...")
    try:
        base.Base.metadata.create_all(bind=base.engine)
        logger.info("Таблицы успешно созданы или уже существуют.")
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц базы данных: {e}", exc_info=True)
        raise e


def seed_db(db: Session) -> None:
    logger.info("Проверка и создание начальных данных (суперпользователь)...")
    try:
        superuser = db.query(User).filter(User.email == settings.FIRST_SUPERUSER_EMAIL).first()
        if not superuser:
            hashed_password = get_password_hash(settings.FIRST_SUPERUSER_PASSWORD)
            superuser_in = User(
                email=settings.FIRST_SUPERUSER_EMAIL,
                hashed_password=hashed_password,
                is_superuser=True,
                balance=1000.0
            )
            db.add(superuser_in)
            db.commit()
            db.refresh(superuser_in)
            logger.info("Суперпользователь успешно создан.")
        else:
            logger.info("Суперпользователь уже существует.")

        demo_user = db.query(User).filter(User.email == settings.DEMO_USER_EMAIL).first()
        if not demo_user:
            hashed_password = get_password_hash(settings.DEMO_USER_PASSWORD)
            demo_user_in = User(
                email=settings.DEMO_USER_EMAIL,
                hashed_password=hashed_password,
                is_superuser=False,
                balance=0.0
            )
            db.add(demo_user_in)
            db.commit()
            db.refresh(demo_user_in)
            logger.info("Демо-пользователь успешно создан.")
        else:
            logger.info("Демо-пользователь уже существует.")


    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при сидинге базы данных: {e}", exc_info=True)
        raise e
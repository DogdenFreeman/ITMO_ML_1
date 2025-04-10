from sqlalchemy.orm import Session
from sqlalchemy import update as sqlalchemy_update
from typing import List, Optional

from app.db.models.user import User
from app.db.models.transaction import Transaction
from app.schemas.user import UserCreate
from app.core.security import get_password_hash, verify_password
import datetime
import logging

logger = logging.getLogger(__name__)


def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).order_by(User.id).offset(skip).limit(limit).all()


def create_user(db: Session, user: UserCreate) -> User:
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        hashed_password=hashed_password,
        balance=0.0,
        role="student",
        is_active=True,
        is_superuser=False
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logger.info(f"Создан пользователь: {db_user.email} (ID: {db_user.id})")
    return db_user


def update_balance(db: Session, user: User, amount: float, transaction_type: str,
                   prediction_request_id: int | None = None) -> User | None:
    new_balance = user.balance + amount

    if amount < 0 and new_balance < 0:
        logger.warning(
            f"Попытка списания {abs(amount)} у пользователя {user.id} ({user.email}). Баланс: {user.balance}. Недостаточно средств.")
        return None

    try:

        stmt = (
            sqlalchemy_update(User)
            .where(User.id == user.id)
            .values(balance=new_balance)
            .execution_options(synchronize_session="fetch")
        )
        result = db.execute(stmt)

        if result.rowcount == 0:
            logger.error(f"Не удалось обновить баланс для пользователя {user.id}. Пользователь не найден?")
            db.rollback()
            return None

        transaction = Transaction(
            user_id=user.id,
            amount=amount,
            transaction_type=transaction_type,
            prediction_request_id=prediction_request_id,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        db.add(transaction)

        db.commit()
        db.refresh(user)
        logger.info(
            f"Баланс пользователя {user.id} ({user.email}) обновлен: {user.balance:.2f}. Операция: {transaction_type} ({amount:.2f}).")
        return user

    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при обновлении баланса для пользователя {user.id}: {e}", exc_info=True)
        return None

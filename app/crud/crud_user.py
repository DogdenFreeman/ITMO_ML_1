from sqlalchemy.orm import Session
from typing import List, Optional
import datetime
import logging

from db.models.user import User
from db.models.transaction import Transaction
from schemas.user import UserCreate
from core.security import get_password_hash


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
        is_active=True,
        is_superuser=False
    )
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"Создан пользователь: {db_user.email} (ID: {db_user.id})")
        return db_user
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при создании пользователя {user.email}: {e}", exc_info=True)
        raise e


def update_balance(db: Session, user: User, amount: float, transaction_type: str,
                   prediction_request_id: int | None = None) -> User | None:
    new_balance = user.balance + amount

    if amount < 0 and new_balance < 0:
        logger.warning(
            f"Попытка списания {abs(amount):.2f} у пользователя {user.id} ({user.email}). "
            f"Текущий баланс: {user.balance:.2f}. Недостаточно средств. Операция '{transaction_type}' отменена."
        )
        return None

    try:
        transaction = Transaction(
            user_id=user.id,
            amount=amount,
            transaction_type=transaction_type,
            prediction_request_id=prediction_request_id,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        db.add(transaction)

        user.balance = new_balance

        db.commit()

        db.refresh(user)

        logger.info(
            f"Баланс пользователя {user.id} ({user.email}) успешно обновлен. Новое значение: {user.balance:.2f}. "
            f"Операция: '{transaction_type}' ({amount:+.2f}). Создана транзакция ID: {transaction.id}."
        )
        return user

    except Exception as e:
        db.rollback()
        logger.error(
            f"Ошибка при обновлении баланса для пользователя {user.id} ({user.email}) "
            f"для операции '{transaction_type}' ({amount:+.2f}): {e}", exc_info=True
        )
        return None
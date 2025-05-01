from sqlalchemy.orm import Session
from typing import List, Optional
import datetime

from db.models.transaction import Transaction
from db.models.user import User


def get_transaction_by_id(db: Session, transaction_id: int) -> Optional[Transaction]:
    return db.query(Transaction).filter(Transaction.id == transaction_id).first()


def get_transactions_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Transaction]:
    return (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.timestamp.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_all_transactions(db: Session, skip: int = 0, limit: int = 100) -> List[Transaction]:
    return (
        db.query(Transaction)
        .order_by(Transaction.timestamp.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_transaction(db: Session, *, user_id: int, amount: float, transaction_type: str,
                       prediction_request_id: Optional[int] = None) -> Transaction:
    db_transaction = Transaction(
        user_id=user_id,
        amount=amount,
        transaction_type=transaction_type,
        prediction_request_id=prediction_request_id,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    # Note: This function does not commit. The caller is responsible for committing.
    # In crud_user.update_balance, Transaction objects are created and committed there.
    return db_transaction
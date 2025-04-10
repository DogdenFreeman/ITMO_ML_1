from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.models.transaction import Transaction
from app.db.models.user import User


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
        prediction_request_id=prediction_request_id
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

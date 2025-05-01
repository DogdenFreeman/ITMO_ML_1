from typing import List, Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from api import deps
from db.models.user import User
from schemas.user import User, BalanceUpdate
from schemas.transaction import Transaction
from schemas.prediction import PredictionRequest

from crud import crud_user, crud_transaction, crud_prediction

logger = logging.getLogger(__name__)


router = APIRouter()


@router.get("/me", response_model=User)
def read_users_me(
    current_user: Annotated[User, Depends(deps.get_current_user)]
):
    return current_user


@router.post("/me/balance/topup", response_model=User)
def topup_user_balance(
    *,
    db: Annotated[Session, Depends(deps.get_db)],
    balance_in: BalanceUpdate,
    current_user: Annotated[User, Depends(deps.get_current_user)],
):
    if balance_in.amount <= 0:
        logger.warning(
            f"Пользователь {current_user.id} ({current_user.email}) попытался пополнить баланс на отрицательную/нулевую сумму: {balance_in.amount}."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сумма пополнения должна быть положительной."
        )

    updated_user = crud_user.update_balance(
        db=db,
        user=current_user,
        amount=balance_in.amount,
        transaction_type="topup"
    )

    if not updated_user:
        logger.error(
            f"Не удалось обновить баланс пользователя {current_user.id} ({current_user.email}) "
            f"при пополнении на {balance_in.amount}.", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось обновить баланс."
        )

    return updated_user


@router.get("/me/history/transactions", response_model=List[Transaction])
def read_transaction_history(
    *,
    db: Annotated[Session, Depends(deps.get_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    skip: int = 0,
    limit: int = 100
):
    transactions = crud_transaction.get_transactions_by_user(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    return transactions


@router.get("/me/history/predictions", response_model=List[PredictionRequest])
def read_prediction_history(
    *,
    db: Annotated[Session, Depends(deps.get_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    skip: int = 0,
    limit: int = 100
):
    predictions = crud_prediction.get_prediction_history_by_user(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    return predictions


@router.get("/", response_model=List[User], dependencies=[Depends(deps.get_current_active_superuser)])
def read_users(
    db: Annotated[Session, Depends(deps.get_db)],
    skip: int = 0,
    limit: int = 100,
):
    users = crud_user.get_users(db, skip=skip, limit=limit)
    return users


@router.post("/{user_id}/admin/credit", response_model=User,
             dependencies=[Depends(deps.get_current_active_superuser)])
def admin_credit_user_balance(
    *,
    db: Annotated[Session, Depends(deps.get_db)],
    user_id: int,
    balance_in: BalanceUpdate,
):
    user_to_credit = crud_user.get_user(db, user_id=user_id)
    if not user_to_credit:
        logger.warning(f"Администратор попытался пополнить баланс несуществующего пользователя с ID {user_id}.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден.")

    if balance_in.amount <= 0:
        logger.warning(
            f"Администратор попытался пополнить баланс пользователя {user_id} на отрицательную/нулевую сумму: {balance_in.amount}."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сумма для пополнения должна быть положительной."
        )

    updated_user = crud_user.update_balance(
        db=db,
        user=user_to_credit,
        amount=balance_in.amount,
        transaction_type="admin_credit"
    )

    if not updated_user:
        logger.error(
            f"Не удалось обновить баланс пользователя {user_id} при адminском пополнении на {balance_in.amount}.", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось обновить баланс пользователя."
        )

    return updated_user
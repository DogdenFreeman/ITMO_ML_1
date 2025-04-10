from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.db.models.user import User as UserModel
from app.schemas import user as user_schema
from app.schemas import transaction as transaction_schema
from app.schemas import prediction as prediction_schema
from app.crud import crud_user, crud_transaction, crud_prediction

router = APIRouter()


@router.get("/me", response_model=user_schema.User)
def read_users_me(

        current_user: Annotated[UserModel, Depends(deps.get_current_user)]
):
    return current_user


@router.post("/me/balance/topup", response_model=user_schema.User)
def topup_user_balance(
        *,
        db: Annotated[Session, Depends(deps.get_db)],
        balance_in: user_schema.BalanceUpdate,
        current_user: Annotated[UserModel, Depends(deps.get_current_user)],
):
    if balance_in.amount <= 0:
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось обновить баланс."
        )

    return updated_user


@router.get("/me/history/transactions", response_model=List[transaction_schema.Transaction])
def read_transaction_history(
        *,
        db: Annotated[Session, Depends(deps.get_db)],
        current_user: Annotated[UserModel, Depends(deps.get_current_user)],
        skip: int = 0,
        limit: int = 100
):
    transactions = crud_transaction.get_transactions_by_user(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    return transactions


@router.get("/me/history/predictions", response_model=List[prediction_schema.PredictionRequest])
def read_prediction_history(
        *,
        db: Annotated[Session, Depends(deps.get_db)],
        current_user: Annotated[UserModel, Depends(deps.get_current_user)],
        skip: int = 0,
        limit: int = 100
):
    predictions = crud_prediction.get_prediction_history_by_user(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    return predictions


@router.get("/", response_model=List[user_schema.User], dependencies=[Depends(deps.get_current_active_superuser)])
def read_users(
        db: Annotated[Session, Depends(deps.get_db)],
        skip: int = 0,
        limit: int = 100,

):
    users = crud_user.get_users(db, skip=skip, limit=limit)
    return users


@router.post("/{user_id}/admin/credit", response_model=user_schema.User,
             dependencies=[Depends(deps.get_current_active_superuser)])
def admin_credit_user_balance(
        *,
        db: Annotated[Session, Depends(deps.get_db)],
        user_id: int,
        balance_in: user_schema.BalanceUpdate,

):
    user_to_credit = crud_user.get_user(db, user_id=user_id)
    if not user_to_credit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден.")

    if balance_in.amount <= 0:
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось обновить баланс пользователя."
        )
    return updated_user

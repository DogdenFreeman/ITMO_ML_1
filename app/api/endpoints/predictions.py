from typing import Annotated, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.db.models.user import User as UserModel

from app.schemas import prediction as prediction_schema
from app.crud import crud_user, crud_prediction, crud_transaction
from app.core.config import settings

router = APIRouter()


@router.post(
    "/",
    response_model=prediction_schema.PredictionRequest,
    status_code=status.HTTP_202_ACCEPTED
)
def create_prediction_request_endpoint(
        *,
        db: Annotated[Session, Depends(deps.get_db)],
        prediction_in: prediction_schema.PredictionCreate,
        current_user: Annotated[UserModel, Depends(deps.get_current_user)],
):
    prediction_cost = settings.PREDICTION_COST

    if current_user.balance < prediction_cost:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Недостаточно средств. Требуется {prediction_cost:.2f} суммы, доступно {current_user.balance:.2f}."
        )

    try:

        db_prediction_request = crud_prediction.create_prediction_request(
            db=db,
            user_id=current_user.id,
            prediction_in=prediction_in,
            cost=prediction_cost
        )

        db.add(db_prediction_request)
        db.flush()

        updated_user = crud_user.update_balance(
            db=db,
            user=current_user,
            amount=-prediction_cost,
            transaction_type="prediction_fee",
            prediction_request_id=db_prediction_request.id
        )

        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при списании средств или записи транзакции."
            )

        db.refresh(db_prediction_request)

        return db_prediction_request

    except Exception as e:

        db.rollback()

        print(f"Ошибка при создании запроса на предсказание: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось создать запрос на предсказание."
        )


@router.get("/{prediction_id}", response_model=prediction_schema.PredictionRequest)
def read_prediction_request(
        *,
        db: Annotated[Session, Depends(deps.get_db)],
        prediction_id: int,
        current_user: Annotated[UserModel, Depends(deps.get_current_user)],
):
    db_prediction = crud_prediction.get_prediction_by_id(db, prediction_id=prediction_id)

    if not db_prediction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запрос на предсказание не найден."
        )

    if db_prediction.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для просмотра этого запроса."
        )

    return db_prediction


@router.get("/", response_model=List[prediction_schema.PredictionRequest])
def read_prediction_requests(
        db: Annotated[Session, Depends(deps.get_db)],
        current_user: Annotated[UserModel, Depends(deps.get_current_user)],
        skip: int = 0,
        limit: int = 100
):
    if current_user.is_superuser:

        predictions = crud_prediction.get_all_predictions(db, skip=skip, limit=limit)
    else:

        predictions = crud_prediction.get_prediction_history_by_user(
            db, user_id=current_user.id, skip=skip, limit=limit
        )
    return predictions

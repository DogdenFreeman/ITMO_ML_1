from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import datetime
import logging

from db.models.prediction_request import PredictionRequest
from schemas.prediction import PredictionCreate

logger = logging.getLogger(__name__)


def get_prediction_by_id(db: Session, prediction_id: int) -> Optional[PredictionRequest]:
    return db.query(PredictionRequest).filter(PredictionRequest.id == prediction_id).first()


def get_prediction_history_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[
    PredictionRequest]:
    return (
        db.query(PredictionRequest)
        .filter(PredictionRequest.user_id == user_id)
        .order_by(PredictionRequest.timestamp_created.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_all_predictions(db: Session, skip: int = 0, limit: int = 100) -> List[PredictionRequest]:
    return (
        db.query(PredictionRequest)
        .order_by(PredictionRequest.timestamp_created.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_prediction_request(db: Session, *, user_id: int, prediction_in: PredictionCreate,
                              cost: float | None = None) -> PredictionRequest | None:
    input_data_dict = prediction_in.input_data.model_dump() if prediction_in.input_data else None

    db_obj = PredictionRequest(
        user_id=user_id,
        input_data=input_data_dict,
        status="pending",
        cost=cost,
        timestamp_created=datetime.datetime.now(datetime.timezone.utc)
    )

    try:
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        logger.info(f"Создан запрос на предсказание (ID: {db_obj.id}) для пользователя {user_id}.")

        return db_obj
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при создании запроса на предсказание для пользователя {user_id}: {e}", exc_info=True)
        return None


def update_prediction_status(
    db: Session,
    prediction_id: int,
    status: str,
    result: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
) -> Optional[PredictionRequest]:
    db_prediction = db.query(PredictionRequest).filter(PredictionRequest.id == prediction_id).first()

    if db_prediction:
        logger.info(f"Попытка обновления статуса запроса {prediction_id} на '{status}'.")
        db_prediction.status = status
        db_prediction.result = result
        db_prediction.error_message = error_message

        if status in ["completed", "failed"]:
             db_prediction.timestamp_completed = datetime.datetime.now(datetime.timezone.utc)
             logger.info(f"Установлено время завершения для запроса {prediction_id}.")

        try:
            db.commit()
            db.refresh(db_prediction)

            logger.info(f"Статус запроса {prediction_id} успешно обновлен на '{status}'.")
            return db_prediction
        except Exception as e:
            db.rollback()
            logger.error(f"Ошибка при коммите обновления статуса запроса {prediction_id}: {e}", exc_info=True)
            return None
    else:
        logger.warning(f"Попытка обновить статус несуществующего запроса {prediction_id}. Запрошенный статус: '{status}'.")
        return None
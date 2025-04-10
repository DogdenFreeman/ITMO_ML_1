from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import datetime

from app.db.models.prediction_request import PredictionRequest
from app.schemas.prediction import PredictionCreate


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
                              cost: float | None = None) -> PredictionRequest:
    input_data_dict = prediction_in.input_data.model_dump() if prediction_in.input_data else None

    db_obj = PredictionRequest(
        user_id=user_id,
        input_data=input_data_dict,
        status="pending",
        cost=cost,
        timestamp_created=datetime.datetime.now(datetime.timezone.utc)

    )

    return db_obj


def update_prediction_status(
        db: Session,
        prediction_id: int,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
) -> Optional[PredictionRequest]:
    db_prediction = db.query(PredictionRequest).filter(PredictionRequest.id == prediction_id).first()
    if db_prediction:
        db_prediction.status = status
        db_prediction.result = result
        db_prediction.error_message = error_message
        db_prediction.timestamp_completed = datetime.datetime.now(datetime.timezone.utc)
        try:
            db.commit()
            db.refresh(db_prediction)

            print(f"Статус запроса {prediction_id} обновлен на '{status}'.")
            return db_prediction
        except Exception as e:
            db.rollback()

            print(f"Ошибка при обновлении статуса запроса {prediction_id}: {e}")
            return None
    else:

        print(f"Попытка обновить статус несуществующего запроса {prediction_id}.")
        return None

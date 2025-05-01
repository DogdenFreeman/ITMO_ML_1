from typing import Annotated, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import pika
import json
import logging

from api import deps
from db.models.user import User
from db.models.lesson import Lesson

from schemas.prediction import PredictionCreate, PredictionRequest
from crud import crud_user, crud_prediction, crud_lesson
from core.config import settings

logger = logging.getLogger(__name__)


router = APIRouter()


@router.post(
    "/",
    response_model=PredictionRequest,
    status_code=status.HTTP_202_ACCEPTED
)
def create_prediction_request_endpoint(
    *,
    db: Annotated[Session, Depends(deps.get_db)],
    prediction_in: PredictionCreate,
    current_user: Annotated[User, Depends(deps.get_current_user)],
):
    prediction_cost = settings.PREDICTION_COST

    if current_user.balance < prediction_cost:
        logger.warning(
            f"Пользователь {current_user.id} ({current_user.email}) попытался создать предсказание без достаточных средств. "
            f"Требуется {prediction_cost:.2f}, доступно {current_user.balance:.2f}."
        )
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Недостаточно средств. Требуется {prediction_cost:.2f} кредитов, доступно {current_user.balance:.2f}.",
        )


    if not prediction_in.input_data or 'lesson_id' not in prediction_in.input_data.model_dump():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо указать 'lesson_id' во входных данных."
        )

    lesson_id = prediction_in.input_data.lesson_id
    # lesson = crud_lesson.get_lesson(db, lesson_id=lesson_id) // проверка на существование урока
    # if not lesson:
    #      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Урок с ID {lesson_id} не найден.")


    db.begin_nested()

    try:
        db_prediction_request = crud_prediction.create_prediction_request(
            db=db,
            user_id=current_user.id,
            prediction_in=prediction_in, # prediction_in теперь включает lesson_id
            cost=prediction_cost
        )

        updated_user = crud_user.update_balance(
            db=db,
            user=current_user,
            amount=-prediction_cost,
            transaction_type="prediction_fee",
            prediction_request_id=db_prediction_request.id
        )

        if not updated_user:
            db.rollback()
            logger.error(
                f"Не удалось обновить баланс пользователя {current_user.id} или записать транзакцию "
                f"после создания запроса {db_prediction_request.id}. Откат операции."
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при списании средств или записи транзакции.",
            )

        db.commit()

        db.refresh(db_prediction_request)

        # В задачу RabbitMQ теперь отправляем lesson_id вместе с prediction_id и user_id
        send_task_to_rabbitmq(db_prediction_request.id, current_user.id, lesson_id)

        logger.info(
            f"Запрос на предсказание (ID: {db_prediction_request.id}, Lesson ID: {lesson_id}) создан для пользователя {current_user.id}. "
            f"Списано: {prediction_cost:.2f}. Задача отправлена в RabbitMQ."
        )

        return db_prediction_request

    except HTTPException as e:
        db.rollback()
        logger.warning(f"HTTPException при создании предсказания: {e.detail}. Откат.")
        raise e

    except Exception as e:
        db.rollback()
        logger.error(f"Непредвиденная ошибка при создании запроса на предсказание: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось создать запрос на предсказание.",
        )


def send_task_to_rabbitmq(prediction_id: int, user_id: int, lesson_id: int): # Добавлен lesson_id
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
        channel = connection.channel()
        channel.queue_declare(queue='ml_tasks', durable=True)

        task = {'prediction_id': prediction_id, 'user_id': user_id, 'lesson_id': lesson_id} # Добавлен lesson_id в task
        channel.basic_publish(
            exchange='',
            routing_key='ml_tasks',
            body=json.dumps(task),
            properties=pika.BasicProperties(
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
            )
        )
        connection.close()
        logger.info(f"Задача для предсказания {prediction_id} отправлена в RabbitMQ.")
    except Exception as e:
        logger.error(f"Ошибка при отправке задачи в RabbitMQ для prediction_id={prediction_id}: {e}")


@router.get("/{prediction_id}", response_model=PredictionRequest)
def read_prediction_request(
    *,
    db: Annotated[Session, Depends(deps.get_db)],
    prediction_id: int,
    current_user: Annotated[User, Depends(deps.get_current_user)],
):
    db_prediction = crud_prediction.get_prediction_by_id(db, prediction_id=prediction_id)

    if not db_prediction:
        logger.warning(f"Пользователь {current_user.id} запросил несуществующее предсказание с ID {prediction_id}.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запрос на предсказание не найден."
        )

    if db_prediction.user_id != current_user.id and not current_user.is_superuser:
        logger.warning(
            f"Пользователь {current_user.id} попытался просмотреть предсказание {prediction_id}, "
            f"принадлежащее пользователю {db_prediction.user_id}. Доступ запрещен."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для просмотра этого запроса."
        )

    return db_prediction


@router.get("/", response_model=List[PredictionRequest])
def read_prediction_requests(
    db: Annotated[Session, Depends(deps.get_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
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
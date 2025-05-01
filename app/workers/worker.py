import os
import pika
import json
import logging
import datetime

from ml_model import predict

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.orm import joinedload


from db.models.prediction_request import PredictionRequest
from db.models.attendance import Attendance
from db.models.lesson import Lesson
from db.models.subject import Subject
from crud import crud_prediction
from crud import crud_attendance
from core.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

rabbitmq_host = 'rabbitmq'
rabbitmq_queue = 'ml_tasks'

DATABASE_URL = settings.DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session() -> Session:
    return SessionLocal()


def process_message(ch, method, properties, body):
    db: Session | None = None
    prediction_id = None
    user_id = None
    lesson_id = None

    try:
        logger.info(f"Получено сообщение из RabbitMQ: {body.decode()}")
        task = json.loads(body)
        prediction_id = task.get('prediction_id')
        user_id = task.get('user_id')
        lesson_id = task.get('lesson_id')

        if not prediction_id or not user_id or lesson_id is None:
            logger.error(f"Неверный формат сообщения из RabbitMQ: {body}. Отклонение сообщения.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        logger.info(f"Начата обработка задачи на предсказание (ID: {prediction_id}, User ID: {user_id}, Lesson ID: {lesson_id})")

        db = get_db_session()

        history_records = crud_attendance.get_attendance_history(db, user_id=user_id)

        logger.debug(f"Получено {len(history_records)} записей истории посещений для пользователя {user_id}.")

        attendance_history_for_model = []
        for attendance in history_records:
             if attendance.lesson and attendance.lesson.subject:
                 attendance_history_for_model.append({
                    'subject_name': attendance.lesson.subject.name,
                    'date_time': attendance.lesson.date_time.isoformat() if attendance.lesson.date_time else None,
                    'attended': attendance.attended
                })
             else:
                 logger.warning(f"Запись посещения {attendance.id} для пользователя {user_id} не содержит данных Lesson или Subject. Пропускаем.")

        logger.info(f"История посещений для модели предсказания ({len(attendance_history_for_model)} записей): {attendance_history_for_model}")

        # Выполняем предсказание, передавая историю и lesson_id
        result = predict(attendance_history_for_model, lesson_id) # Передаем lesson_id

        logger.info(f"Результат предсказания для запроса {prediction_id}: {result}")

        updated_prediction = crud_prediction.update_prediction_status(
            db,
            prediction_id,
            "completed",
            result=result
        )

        if updated_prediction:
             logger.info(f"Статус предсказания (ID: {prediction_id}) успешно обновлен на 'completed'")
        else:
             logger.error(f"Не удалось обновить статус предсказания (ID: {prediction_id}) на 'completed' после успешного предсказания.")


    except Exception as e:
        logger.error(f"Ошибка обработки сообщения для prediction_id={prediction_id}: {e}", exc_info=True)

        if db:
            try:
                 logger.info(f"Попытка обновить статус предсказания {prediction_id} на 'failed' после ошибки.")
                 crud_prediction.update_prediction_status(
                    db,
                    prediction_id,
                    "failed",
                    error_message=str(e)
                 )
                 logger.info(f"Статус предсказания (ID: {prediction_id}) обновлен на 'failed'.")
            except Exception as update_error:
                 logger.error(f"Критическая ошибка: не удалось обновить статус предсказания {prediction_id} на 'failed' после основной ошибки: {update_error}", exc_info=True)
        else:
            logger.error(f"Ошибка обработки сообщения prediction_id={prediction_id}, сессия БД не была открыта для обновления статуса 'failed'.")

    finally:
        if db:
            try:
                db.close()
                logger.debug(f"Сессия БД для запроса {prediction_id} закрыта.")
            except Exception as close_error:
                 logger.error(f"Ошибка при закрытии сессии БД для запроса {prediction_id}: {close_error}", exc_info=True)

        logger.info(f"Сообщение RabbitMQ для prediction_id={prediction_id} подтверждено (ACK).")
        ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    logger.info("ML Worker запущен. Попытка подключения к RabbitMQ и ожидание задач...")

    connection = None
    retries = 10
    delay = 10
    for i in range(retries):
        try:
            logger.info(f"Попытка подключения к RabbitMQ ({i+1}/{retries})...")
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host, heartbeat=600, blocked_connection_timeout=300))
            logger.info("Успешное подключение к RabbitMQ.")
            break
        except pika.exceptions.AMQPConnectionError as e:
            logger.warning(f"Попытка подключения к RabbitMQ не удалась: {e}")
            if i < retries - 1:
                import time
                logger.info(f"Повторная попытка через {delay} секунд.")
                time.sleep(delay)
            else:
                logger.critical("Не удалось подключиться к RabbitMQ после нескольких попыток. Выход из приложения.")
                exit(1)
        except Exception as e:
             logger.error(f"Непредвиденная ошибка при подключении к RabbitMQ: {e}", exc_info=True)
             if i < retries - 1:
                import time
                logger.info(f"Повторная попытка через {delay} секунд.")
                time.sleep(delay)
             else:
                logger.critical("Не удалось подключиться к RabbitMQ после нескольких попыток. Выход из приложения.")
                exit(1)

    if connection is None:
        logger.critical("Не удалось установить соединение с RabbitMQ. Выход.")
        exit(1)

    try:
        channel = connection.channel()
        channel.queue_declare(queue=rabbitmq_queue, durable=True)
        logger.info(f"Очередь '{rabbitmq_queue}' объявлена.")

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=rabbitmq_queue, on_message_callback=process_message, auto_ack=False)

        logger.info('Начато потребление сообщений из очереди. Ожидание задач...')
        channel.start_consuming()

    except KeyboardInterrupt:
        logger.info("Получен сигнал KeyboardInterrupt. Остановка потребления.")
        if channel:
            channel.stop_consuming()
    except Exception as e:
        logger.error(f"Непредвиденная ошибка воркера: {e}", exc_info=True)
    finally:
        if connection and connection.is_open:
            logger.info("Закрытие соединения с RabbitMQ.")
            connection.close()


if __name__ == '__main__':
    main()
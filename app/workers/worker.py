import pika
import json
import logging
from ml_model import predict
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models.prediction_request import PredictionRequest
from db.models.attendance import Attendance


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


rabbitmq_host = 'rabbitmq'
rabbitmq_queue = 'ml_tasks'


DATABASE_URL = "postgresql+psycopg2://user_test:changeme_db_password@database/db_test"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def process_message(ch, method, properties, body):
    try:
        task = json.loads(body)
        prediction_id = task.get('prediction_id')
        user_id = task.get('user_id')

        if not prediction_id or not user_id:
            logging.error(f"Неверный формат сообщения: {body}")
            return

        logging.info(f"Получена задача на предсказание (ID: {prediction_id})")

        # Получаем историю посещений из базы данных
        history = get_attendance_history(user_id)

        result = predict(history)
        logging.info(f"Результат предсказания: {result}")
        update_prediction_status(prediction_id, "completed", result=result)

    except Exception as e:
        logging.error(f"Ошибка обработки сообщения: {e}")
        update_prediction_status(prediction_id, "failed", error_message=str(e))

    ch.basic_ack(delivery_tag=method.delivery_tag)

def get_attendance_history(user_id):
    db = SessionLocal()
    try:
        history = db.query(Attendance).filter(Attendance.user_id == user_id).all()
        # история посещения для модели
        attendance_history = []
        for attendance in history:
            attendance_history.append({
                'subject_name': attendance.lesson.subject.name,
                'date_time': attendance.lesson.date_time,
                'attended': attendance.attended
            })
        return attendance_history
    except Exception as e:
        logging.error(f"Ошибка получения истории посещений: {e}")
        return []
    finally:
        db.close()

def update_prediction_status(prediction_id, status, result=None, error_message=None):
    db = SessionLocal()
    try:
        prediction = db.query(PredictionRequest).filter(PredictionRequest.id == prediction_id).first()
        if prediction:
            prediction.status = status
            prediction.result = result
            prediction.error_message = error_message
            db.commit()
            logging.info(f"Статус предсказания (ID: {prediction_id}) обновлен на '{status}'")
        else:
            logging.error(f"Предсказание с ID {prediction_id} не найдено")
    except Exception as e:
        logging.error(f"Ошибка обновления статуса предсказания: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host))
    channel = connection.channel()
    channel.queue_declare(queue=rabbitmq_queue)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=rabbitmq_queue, on_message_callback=process_message)

    logging.info('Ожидание задач...')
    channel.start_consuming()

if __name__ == '__main__':
    main()
FROM python:3.12.3-slim

WORKDIR /app

COPY app/workers/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/workers/worker.py .
COPY app/workers/ml_model.py .
COPY app/db/base.py app/db/
COPY app/db/models/prediction_request.py app/db/models/
COPY app/db/models/attendance.py app/db/models/


CMD ["python", "worker.py"]
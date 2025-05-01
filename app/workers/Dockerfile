FROM python:3.12.3-slim as base

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PIP_NO_CACHE_DIR=off
ENV PIP_DISABLE_PIP_VERSION_CHECK=on
ENV PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

FROM base as builder

COPY app/workers/requirements.txt /app/requirements.txt

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

FROM base

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

COPY app/workers/worker.py /app/
COPY app/workers/ml_model.py /app/
COPY app/db/base.py /app/db/
COPY app/db/models/prediction_request.py /app/db/models/
COPY app/db/models/attendance.py /app/db/models/
COPY app/db/models/lesson.py /app/db/models/
COPY app/db/models/subject.py /app/db/models/
COPY app/crud/crud_prediction.py /app/crud/
COPY app/crud/crud_attendance.py /app/crud/
COPY app/core/config.py /app/core/

CMD ["python", "worker.py"]
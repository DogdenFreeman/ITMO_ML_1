FROM python:3.12.3-slim

WORKDIR /app

COPY app/workers/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app .


CMD ["python", "worker.py"]
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.api.endpoints import auth, users, predictions
from app.db.base import SessionLocal
from app.db import init_db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Запуск приложения...")
    logger.info("Попытка инициализации базы данных...")
    db: Session | None = None
    try:

        db = SessionLocal()
        init_db.init_db(db)
        init_db.seed_db(db)
        logger.info("Инициализация базы данных завершена.")
    except Exception as e:
        logger.error(f"Критическая ошибка при инициализации БД: {e}")


    finally:
        if db:
            db.close()
    yield

    logger.info("Остановка приложения...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="API для сервиса регистрации посещаемости студентов.",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["Users"])
app.include_router(predictions.router, prefix=f"{settings.API_V1_STR}/predictions", tags=["Predictions"])


@app.get("/")
async def read_root():
    logger.info("Запрос к корневому эндпоинту /")
    return {"message": f"Добро пожаловать в {settings.PROJECT_NAME}"}


@app.get("/health")
async def health_check():
    logger.info("Проверка работоспособности сервиса /health")

    db: Session | None = None
    try:
        db = SessionLocal()

        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Ошибка проверки соединения с БД: {e}")
        db_status = "unhealthy"
    finally:
        if db:
            db.close()
    return {"status": "healthy", "database": db_status}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTPException: {exc.status_code} {exc.detail} для {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Необработ. исключение: {exc} для следующего запроса {request.url}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренная ошибка сервера"},
    )

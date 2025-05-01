import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))) # для тестирования непосредственно, без докера



import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Annotated, Any, List


from core.config import settings
from api.endpoints import auth, users, predictions, attendances, lessons, subjects
from api import deps
from db.base import SessionLocal
from db import init_db
from schemas.user import UserCreate, BalanceUpdate, User
from schemas.prediction import PredictionCreate, PredictionRequest, PredictionInputData
from schemas.lesson import LessonBase

from db.models.user import User as UserModel
from crud import crud_lesson


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


templates = Jinja2Templates(directory="templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Запуск приложения '{settings.PROJECT_NAME}' (версия {app.version})...")
    logger.info("Попытка инициализации базы данных...")
    db: Session | None = None
    try:
        db = SessionLocal()
        init_db.init_db(db)
        init_db.seed_db(db)
        db.close()
        logger.info("Инициализация базы данных завершена успешно.")
    except Exception as e:
        logger.critical(f"Критическая ошибка при инициализации БД: {e}", exc_info=True)

    yield

    logger.info("Остановка приложения...")
    pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description=settings.PROJECT_NAME,
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["Users"])
app.include_router(predictions.router, prefix=f"{settings.API_V1_STR}/predictions", tags=["Predictions"])
app.include_router(attendances.router, prefix=f"{settings.API_V1_STR}/attendances", tags=["Attendances"])
app.include_router(lessons.router, prefix=f"{settings.API_V1_STR}/lessons", tags=["Lessons"])
app.include_router(subjects.router, prefix=f"{settings.API_V1_STR}/subjects", tags=["Subjects"])


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    logger.info(f"Запрос главной страницы от {request.client.host}")
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    logger.info(f"Запрос страницы регистрации от {request.client.host}")
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register", response_class=HTMLResponse)
async def register_user_web(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    logger.info(f"POST запрос на регистрацию для email: {email} от {request.client.host}")
    try:
        user_in = UserCreate(email=email, password=password)
        created_user = auth.register_user(db=db, user_in=user_in)
        logger.info(f"Пользователь {created_user.email} успешно зарегистрирован. Перенаправление на /login.")
        response = RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
        return response
    except HTTPException as e:
        logger.warning(f"Ошибка регистрации для email '{email}': {e.detail}. Отображение ошибки на странице регистрации.")
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": e.detail},
            status_code=e.status_code
        )
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при регистрации для email '{email}': {e}", exc_info=True)
        return templates.TemplateResponse(
             "register.html",
             {"request": request, "error": "Произошла внутренняя ошибка сервера."},
             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
         )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    logger.info(f"Запрос страницы входа от {request.client.host}")
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login", response_class=HTMLResponse)
async def login_user_web(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(deps.get_db)
):
    logger.info(f"POST запрос на вход для пользователя: {username} от {request.client.host}")
    try:
        form_data = OAuth2PasswordRequestForm(username=username, password=password)
        token = auth.login_for_access_token(db=db, form_data=form_data)

        response = RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="access_token", value=token["access_token"], httponly=True)
        logger.info(f"Пользователь {username} успешно вошел. Перенаправление на /dashboard.")
        return response
    except HTTPException as e:
        logger.warning(f"Ошибка входа для пользователя '{username}': {e.detail}. Отображение ошибки на странице входа.")
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": e.detail},
            status_code=e.status_code
        )
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при входе для пользователя '{username}': {e}", exc_info=True)
        return templates.TemplateResponse(
             "login.html",
             {"request": request, "error": "Произошла внутренняя ошибка сервера."},
             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
         )


async def get_current_user_from_cookie(request: Request, db: Session = Depends(deps.get_db)):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return await deps.get_current_user(db, token)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    current_user: Annotated[UserModel, Depends(get_current_user_from_cookie)],
    db: Session = Depends(deps.get_db)
):
    logger.info(f"Запрос страницы личного кабинета от пользователя {current_user.email} ({request.client.host})")
    try:
        predictions_data = predictions.read_prediction_requests(db=db, current_user=current_user, skip=0, limit=100)
        transactions_data = users.read_transaction_history(db=db, current_user=current_user, skip=0, limit=100)
        upcoming_lessons = crud_lesson.get_upcoming_lessons(db=db, skip=0, limit=50)

        predictions_list = predictions_data if isinstance(predictions_data, list) else []
        transactions_list = transactions_data if isinstance(transactions_data, list) else []


        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": current_user,
            "predictions": predictions_list,
            "transactions": transactions_list,
            "upcoming_lessons": upcoming_lessons,
            "prediction_cost": settings.PREDICTION_COST
        })
    except HTTPException as e:
        logger.warning(f"Ошибка при загрузке дашборда для пользователя {current_user.email}: {e.detail}")
        if e.status_code == status.HTTP_401_UNAUTHORIZED:
             response = RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
             response.delete_cookie(key="access_token")
             return response
        return templates.TemplateResponse(
             "dashboard.html",
             {"request": request, "user": current_user, "error": e.detail, "predictions": [], "transactions": [], "upcoming_lessons": [], "prediction_cost": settings.PREDICTION_COST},
             status_code=e.status_code
         )
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при загрузке дашборда для пользователя {current_user.email}: {e}", exc_info=True)
        return templates.TemplateResponse(
             "dashboard.html",
             {"request": request, "user": current_user, "error": "Произошла внутренняя ошибка при загрузке данных.", "predictions": [], "transactions": [], "upcoming_lessons": [], "prediction_cost": settings.PREDICTION_COST},
             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
         )


@app.post("/topup", response_class=HTMLResponse)
async def topup_balance_web(
    request: Request,
    current_user: Annotated[UserModel, Depends(get_current_user_from_cookie)],
    db: Session = Depends(deps.get_db),
    amount: float = Form(...)
):
    logger.info(f"POST запрос на пополнение баланса ({amount}) от пользователя {current_user.email} ({request.client.host})")
    try:
        balance_in = BalanceUpdate(amount=amount)
        updated_user = users.topup_user_balance(db=db, balance_in=balance_in, current_user=current_user)
        logger.info(f"Баланс пользователя {current_user.email} успешно пополнен на {amount}. Новый баланс: {updated_user.balance}.")
        return RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    except HTTPException as e:
        logger.warning(f"Ошибка пополнения баланса для пользователя {current_user.email}: {e.detail}")
        predictions_data = predictions.read_prediction_requests(db=db, current_user=current_user, skip=0, limit=100)
        transactions_data = users.read_transaction_history(db=db, current_user=current_user, skip=0, limit=100)
        upcoming_lessons = crud_lesson.get_upcoming_lessons(db=db, skip=0, limit=50)
        predictions_list = predictions_data if isinstance(predictions_data, list) else []
        transactions_list = transactions_data if isinstance(transactions_data, list) else []
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "user": current_user,
                "predictions": predictions_list,
                "transactions": transactions_list,
                "upcoming_lessons": upcoming_lessons,
                "error": e.detail,
                "prediction_cost": settings.PREDICTION_COST
            },
            status_code=e.status_code
        )
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при пополнении баланса для пользователя {current_user.email}: {e}", exc_info=True)
        predictions_data = predictions.read_prediction_requests(db=db, current_user=current_user, skip=0, limit=100)
        transactions_data = users.read_transaction_history(db=db, current_user=current_user, skip=0, limit=100)
        upcoming_lessons = crud_lesson.get_upcoming_lessons(db=db, skip=0, limit=50)
        predictions_list = predictions_data if isinstance(predictions_data, list) else []
        transactions_list = transactions_data if isinstance(transactions_data, list) else []
        return templates.TemplateResponse(
             "dashboard.html",
             {"request": request, "user": current_user, "error": "Произошла внутренняя ошибка при пополнении баланса.", "predictions": predictions_list, "transactions": transactions_list, "upcoming_lessons": upcoming_lessons, "prediction_cost": settings.PREDICTION_COST},
             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
         )


@app.post("/predict", response_class=HTMLResponse)
async def create_prediction_web(
    request: Request,
    current_user: Annotated[UserModel, Depends(get_current_user_from_cookie)],
    lesson_id: int = Form(...),
    db: Session = Depends(deps.get_db)
):
    logger.info(f"POST запрос на создание предсказания для урока {lesson_id} от пользователя {current_user.email} ({request.client.host})")
    try:
        prediction_in = PredictionCreate(input_data=PredictionInputData(lesson_id=lesson_id))
        prediction_request = predictions.create_prediction_request_endpoint(db=db, prediction_in=prediction_in, current_user=current_user)
        logger.info(f"Запрос на предсказание (ID: {prediction_request.id}) для урока {lesson_id} успешно создан для пользователя {current_user.email}.")
        return RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    except HTTPException as e:
        logger.warning(f"Ошибка при создании предсказания для урока {lesson_id} пользователя {current_user.email}: {e.detail}")
        predictions_data = predictions.read_prediction_requests(db=db, current_user=current_user, skip=0, limit=100)
        transactions_data = users.read_transaction_history(db=db, current_user=current_user, skip=0, limit=100)
        upcoming_lessons = crud_lesson.get_upcoming_lessons(db=db, skip=0, limit=50)
        predictions_list = predictions_data if isinstance(predictions_data, list) else []
        transactions_list = transactions_data if isinstance(transactions_data, list) else []
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "user": current_user,
                "predictions": predictions_list,
                "transactions": transactions_list,
                "upcoming_lessons": upcoming_lessons,
                "error": e.detail,
                "prediction_cost": settings.PREDICTION_COST
            },
            status_code=e.status_code
        )
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при создании предсказания для урока {lesson_id} пользователя {current_user.email}: {e}", exc_info=True)
        predictions_data = predictions.read_prediction_requests(db=db, current_user=current_user, skip=0, limit=100)
        transactions_data = users.read_transaction_history(db=db, current_user=current_user, skip=0, limit=100)
        upcoming_lessons = crud_lesson.get_upcoming_lessons(db=db, skip=0, limit=50)
        predictions_list = predictions_data if isinstance(predictions_data, list) else []
        transactions_list = transactions_data if isinstance(transactions_data, list) else []
        return templates.TemplateResponse(
             "dashboard.html",
             {"request": request, "user": current_user, "error": "Произошла внутренняя ошибка при создании предсказания.", "predictions": predictions_list, "transactions": transactions_list, "upcoming_lessons": upcoming_lessons, "prediction_cost": settings.PREDICTION_COST},
             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
         )


@app.get("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    logger.info(f"Запрос выхода от {request.client.host}")
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="access_token")
    return response


@app.get("/health")
async def health_check():
    logger.info("Проверка работоспособности сервиса /health")
    db: Session | None = None
    db_status = "unhealthy"
    try:
        db = SessionLocal()
        db.execute(text('SELECT 1'))
        db_status = "healthy"
        logger.debug("Проверка соединения с БД успешна.")
    except Exception as e:
        logger.error(f"Ошибка проверки соединения с БД: {e}", exc_info=True)
        db_status = "unhealthy"
    finally:
        if db:
            try:
                db.close()
                logger.debug("Сессия БД в health check закрыта.")
            except Exception as close_error:
                logger.error(f"Ошибка при закрытии сессии БД в health check: {close_error}", exc_info=True)

    app_status = "healthy"

    status_code = status.HTTP_200_OK if db_status == "healthy" else status.HTTP_500_INTERNAL_SERVER_ERROR

    return JSONResponse(content={"status": app_status, "database": db_status}, status_code=status_code)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTPException: {exc.status_code} {exc.detail} для {request.method} {request.url}")
    if request.url.path.startswith(settings.API_V1_STR):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers
        )
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
         response = RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
         response.delete_cookie(key="access_token")
         return response

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Необработанное исключение для запроса {request.method} {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Внутренняя ошибка сервера"},
    )
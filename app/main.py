import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Annotated

from core.config import settings
from api.endpoints import auth, users, predictions, attendances, lessons, subjects
from api import deps
from db.base import SessionLocal
from db import init_db
from schemas.user import UserCreate, BalanceUpdate
from schemas.prediction import PredictionCreate

from db.models.user import User as UserModel

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="templates")

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
app.include_router(attendances.router, prefix=f"{settings.API_V1_STR}/attendances", tags=["Attendances"])
app.include_router(lessons.router, prefix=f"{settings.API_V1_STR}/lessons", tags=["Lessons"])
app.include_router(subjects.router, prefix=f"{settings.API_V1_STR}/subjects", tags=["Subjects"])

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register", response_class=HTMLResponse)
async def register_user(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(deps.get_db)):
    try:
        user_in = UserCreate(email=email, password=password)
        user = auth.register_user(db=db, user_in=user_in)
        return RedirectResponse("/login", status_code=303)
    except HTTPException as e:
        return templates.TemplateResponse("register.html", {"request": request, "error": e.detail})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login", response_class=HTMLResponse)
async def login_user(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(deps.get_db)):
    try:
        token = auth.login_for_access_token(db=db, form_data=OAuth2PasswordRequestForm(username=username, password=password))
        response = RedirectResponse("/dashboard", status_code=303)
        response.set_cookie(key="access_token", value=token["access_token"], httponly=True)
        return response
    except HTTPException as e:
        return templates.TemplateResponse("login.html", {"request": request, "error": e.detail})

async def get_current_user_from_cookie(request: Request, db: Session = Depends(deps.get_db)):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await deps.get_current_user(db, token)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, current_user: Annotated[UserModel, Depends(deps.get_current_user_from_cookie)], db: Session = Depends(deps.get_db)):
    predictions_data = predictions.read_prediction_requests(db=db, current_user=current_user)
    transactions_data = users.read_transaction_history(db=db, current_user=current_user)
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": current_user,
        "predictions": predictions_data,
        "transactions": transactions_data,
        "prediction_cost": settings.PREDICTION_COST
    })

@app.post("/topup", response_class=HTMLResponse)
async def topup_balance(request: Request, current_user: Annotated[UserModel, Depends(deps.get_current_user_from_cookie)], db: Session = Depends(deps.get_db), amount: float = Form(...)):
    try:
        balance_in = BalanceUpdate(amount=amount)
        updated_user = users.topup_user_balance(db=db, balance_in=balance_in, current_user=current_user)
        return RedirectResponse("/dashboard", status_code=303)
    except HTTPException as e:
        predictions_data = predictions.read_prediction_requests(db=db, current_user=current_user)
        transactions_data = users.read_transaction_history(db=db, current_user=current_user)
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": current_user,
            "predictions": predictions_data,
            "transactions": transactions_data,
            "error": e.detail,
            "prediction_cost": settings.PREDICTION_COST
        })

@app.post("/predict", response_class=HTMLResponse)
async def create_prediction(request: Request, current_user: Annotated[UserModel, Depends(deps.get_current_user_from_cookie)], feature1: float = Form(...), feature2: str = Form(...), db: Session = Depends(deps.get_db)):
    try:
        prediction_in = PredictionCreate(input_data={"feature1": feature1, "feature2": feature2})
        prediction_request = predictions.create_prediction_request_endpoint(db=db, prediction_in=prediction_in, current_user=current_user)
        return RedirectResponse("/dashboard", status_code=303)
    except HTTPException as e:
        predictions_data = predictions.read_prediction_requests(db=db, current_user=current_user)
        transactions_data = users.read_transaction_history(db=db, current_user=current_user)
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": current_user,
            "predictions": predictions_data,
            "transactions": transactions_data,
            "error": e.detail,
            "prediction_cost": settings.PREDICTION_COST
        })

@app.get("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(key="access_token")
    return response

@app.get("/health")
async def health_check():
    logger.info("Проверка работоспособности сервиса /health")
    db: Session | None = None
    try:
        db = SessionLocal()
        db.execute(text('SELECT 1'))
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
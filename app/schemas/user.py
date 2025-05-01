from pydantic import BaseModel, EmailStr, ConfigDict


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class User(BaseModel):
    id: int
    email: EmailStr
    balance: float
    is_active: bool
    is_superuser: bool

    model_config = ConfigDict(from_attributes=True)


class BalanceUpdate(BaseModel):
    amount: float

    model_config = ConfigDict(from_attributes=True)
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class User(BaseModel):
    id: int
    email: EmailStr
    balance: float
    is_active: bool
    is_superuser: bool

    class Config:
        from_attributes = True


class BalanceUpdate(BaseModel):
    amount: float

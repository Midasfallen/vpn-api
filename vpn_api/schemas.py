from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: str
    status: str
    is_admin: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TariffOut(BaseModel):
    id: int
    name: str
    price: int

    model_config = {"from_attributes": True}

class AssignTariff(BaseModel):
    tariff_id: int

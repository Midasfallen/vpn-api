from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from decimal import Decimal
from enum import Enum


class UserStatus(str, Enum):
    pending = "pending"
    active = "active"
    blocked = "blocked"


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    status: UserStatus
    is_admin: bool = False
    google_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TariffCreate(BaseModel):
    name: str
    description: Optional[str] = None
    duration_days: Optional[int] = 30
    price: Decimal


class TariffOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    duration_days: int
    price: Decimal
    model_config = {"from_attributes": True}


class AssignTariff(BaseModel):
    tariff_id: int


class VpnPeerCreate(BaseModel):
    user_id: int
    wg_public_key: str
    wg_ip: str
    allowed_ips: Optional[str] = None


class VpnPeerOut(BaseModel):
    id: int
    user_id: int
    wg_public_key: str
    wg_ip: str
    allowed_ips: Optional[str]
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentCreate(BaseModel):
    user_id: Optional[int]
    amount: Decimal
    currency: Optional[str] = "USD"
    provider: Optional[str]


class PaymentOut(BaseModel):
    id: int
    user_id: Optional[int]
    amount: Decimal
    currency: str
    status: str
    provider: Optional[str]
    provider_payment_id: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}

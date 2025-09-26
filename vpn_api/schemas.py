from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserStatus(str, Enum):
    pending = "pending"
    active = "active"
    blocked = "blocked"


class UserCreate(BaseModel):
    email: EmailStr
    password: str | None = None


class RegisterIn(BaseModel):
    email: EmailStr


class VerifyIn(BaseModel):
    email: EmailStr
    code: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


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
    # If not provided, server will use the authenticated user id.
    user_id: Optional[int] = None
    # Keys and IPs can be omitted; server will generate them according to
    # WG_KEY_POLICY (db/host/wg-easy) or return an error if generation is
    # not available.
    wg_public_key: Optional[str] = None
    wg_ip: Optional[str] = None
    allowed_ips: Optional[str] = None
    # Optional client-visible device name or platform string (not required)
    device_name: Optional[str] = None


class VpnPeerOut(BaseModel):
    id: int
    user_id: int
    wg_public_key: str
    # Private key is returned on create so the client can configure its
    # local WireGuard interface. It may be None for remote-managed clients
    # (e.g. when WG_KEY_POLICY creates the key remotely and it is not
    # available to the API).
    wg_private_key: Optional[str]
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

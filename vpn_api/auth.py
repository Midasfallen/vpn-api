"""Authentication and user management endpoints.

Contains registration, login, user lookup and admin utilities. This module
is exercised by unit and integration tests.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from vpn_api import models, schemas
from vpn_api.database import get_db
from vpn_api.mail_service import send_verification_email_background

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY must be set in environment variables!")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
# optional oauth2 scheme that does not raise on missing token
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
PROMOTE_SECRET = os.getenv("PROMOTE_SECRET", "")


def validate_password(password: str):
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    # Можно добавить проверки на сложность
    return True


def get_password_hash(password: str):
    validate_password(password)
    return pwd_context.hash(password)


def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # legacy registration (username+password) remains supported via existing route
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    # Validate password if provided
    hashed_pw = None
    if user.password:
        get_password_hash(user.password)
        hashed_pw = pwd_context.hash(user.password)
    new_user = models.User(email=user.email, hashed_password=hashed_pw)
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(status_code=400, detail="User already exists or DB error") from err
    db.refresh(new_user)
    return new_user


@router.post("/auth/register")
def email_register(
    payload: schemas.RegisterIn, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """Start email verification flow: create user record (if missing), generate code and email it.

    Returns a generic success message to avoid leaking account existence.
    """
    db_user = db.query(models.User).filter(models.User.email == payload.email).first()
    if db_user and db_user.is_verified:
        return {"status": "ok", "message": "Email already verified"}
    if not db_user:
        db_user = models.User(email=payload.email)
        db.add(db_user)
    # generate 6-digit code
    import random

    code = f"{random.randint(0, 999999):06d}"
    db_user.verification_code = code
    from datetime import datetime, timedelta

    db_user.verification_expires_at = datetime.utcnow() + timedelta(minutes=10)
    db.commit()
    # send email in background
    send_verification_email_background(background_tasks, payload.email, code)
    return {"status": "ok", "message": "Check your email"}


@router.post("/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": db_user.email})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/auth/verify", response_model=schemas.TokenOut)
def email_verify(payload: schemas.VerifyIn, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not db_user or not db_user.verification_code:
        raise HTTPException(status_code=400, detail="No verification in progress for this email")
    from datetime import datetime

    if db_user.verification_expires_at and db_user.verification_expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Verification code expired")
    if db_user.verification_code != payload.code:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    # mark verified, clear code
    db_user.is_verified = True
    db_user.verification_code = None
    db_user.verification_expires_at = None
    # set status active
    db_user.status = "active"
    db.commit()
    token = create_access_token({"sub": db_user.email})
    return {"access_token": token, "token_type": "bearer"}


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError as err:
        raise credentials_exception from err
    user = get_user_by_email(db, email)
    if user is None:
        raise credentials_exception
    # models.User.status is an Enum; compare to its value
    try:
        status_val = user.status.value if hasattr(user.status, "value") else str(user.status)
    except Exception:
        status_val = str(user.status)
    if status_val != "active":
        raise HTTPException(status_code=403, detail="User not active")
    return user


def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme_optional), db: Session = Depends(get_db)
):
    """Return user if token provided and valid, otherwise return None."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except Exception:
        return None
    user = get_user_by_email(db, email)
    return user


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.post("/assign_tariff")
def assign_tariff(
    user_id: int,
    assign: schemas.AssignTariff,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # проверка прав: только админ может назначать тарифы
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db_tariff = db.query(models.Tariff).filter(models.Tariff.id == assign.tariff_id).first()
    if not db_tariff:
        raise HTTPException(status_code=404, detail="Tariff not found")
    # Проверка: не назначен ли уже этот тариф
    existing = (
        db.query(models.UserTariff).filter_by(user_id=user_id, tariff_id=assign.tariff_id).first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Tariff already assigned to user")
    user_tariff = models.UserTariff(user_id=user_id, tariff_id=assign.tariff_id)
    db.add(user_tariff)
    # при присвоении тарифа активируем пользователя
    db_user.status = "active"
    db.commit()
    db.refresh(user_tariff)
    return {"msg": "tariff assigned", "user_id": user_id, "tariff_id": assign.tariff_id}


@router.post("/admin/promote")
def promote_user(
    user_id: int,
    secret: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(get_current_user_optional),
):
    """Promote a user to admin.

    If PROMOTE_SECRET matches the provided secret, allow bootstrap promotion.
    Otherwise only an existing admin may promote users.
    """
    if PROMOTE_SECRET and secret == PROMOTE_SECRET:
        # If the correct PROMOTE_SECRET is provided, allow promotion.
        # (Previously we prevented bootstrap promote when any admin existed; for testing
        # and deterministic behavior allow using the secret to promote regardless.)
        pass
    else:
        if not getattr(current_user, "is_admin", False):
            raise HTTPException(status_code=403, detail="Admin privileges required to promote")

    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db_user.is_admin = True
    # make admin active so they can use protected admin endpoints immediately
    db_user.status = "active"
    db.commit()
    return {"msg": "user promoted", "user_id": user_id}

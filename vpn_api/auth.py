from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta

import models, schemas
from database import get_db

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

import os

SECRET_KEY = os.getenv("SECRET_KEY", "supersecret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
PROMOTE_SECRET = os.getenv("PROMOTE_SECRET", "")


def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_pw = get_password_hash(user.password)
    new_user = models.User(email=user.email, hashed_password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login")
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
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
    except JWTError:
        raise credentials_exception
    user = get_user_by_email(db, email)
    if user is None:
        raise credentials_exception
    if user.status != "active":
        raise HTTPException(status_code=403, detail="User not active")
    return user


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.post("/assign_tariff")
def assign_tariff(user_id: int, assign: schemas.AssignTariff, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # проверка прав: только админ может назначать тарифы
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db_tariff = db.query(models.Tariff).filter(models.Tariff.id == assign.tariff_id).first()
    if not db_tariff:
        raise HTTPException(status_code=404, detail="Tariff not found")
    user_tariff = models.UserTariff(user_id=user_id, tariff_id=assign.tariff_id)
    db.add(user_tariff)
    # при присвоении тарифа активируем пользователя
    db_user.status = "active"
    db.commit()
    db.refresh(user_tariff)
    return {"msg": "tariff assigned", "user_id": user_id, "tariff_id": assign.tariff_id}


@router.post("/admin/promote")
def promote_user(user_id: int, secret: str = None, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Promote a user to admin.

    If PROMOTE_SECRET is set in env and matches provided secret, anyone with a valid token can promote (bootstrap).
    Otherwise only existing admins can promote new admins.
    """
    # allow bootstrap via secret
    if PROMOTE_SECRET and secret == PROMOTE_SECRET:
        pass
    else:
        if not getattr(current_user, "is_admin", False):
            raise HTTPException(status_code=403, detail="Admin privileges required to promote")

    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db_user.is_admin = True
    db.commit()
    return {"msg": "user promoted", "user_id": user_id}

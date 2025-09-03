from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from vpn_api import models, schemas
from vpn_api.auth import get_current_user
from vpn_api.database import get_db

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/", response_model=schemas.PaymentOut)
def create_payment(
    payload: schemas.PaymentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Only admin or owner can create payment
    if (
        payload.user_id
        and not getattr(current_user, "is_admin", False)
        and current_user.id != payload.user_id
    ):
        raise HTTPException(status_code=403, detail="Not allowed")
    payment = models.Payment(
        user_id=payload.user_id,
        amount=payload.amount,
        currency=payload.currency,
        provider=payload.provider,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


@router.get("/", response_model=List[schemas.PaymentOut])
def list_payments(
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.Payment)
    if user_id:
        if not getattr(current_user, "is_admin", False) and current_user.id != user_id:
            raise HTTPException(status_code=403, detail="Not allowed")
        q = q.filter(models.Payment.user_id == user_id)
    elif not getattr(current_user, "is_admin", False):
        q = q.filter(models.Payment.user_id == current_user.id)
    return q.offset(skip).limit(limit).all()


@router.get("/{payment_id}", response_model=schemas.PaymentOut)
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    payment = db.query(models.Payment).filter(models.Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if not getattr(current_user, "is_admin", False) and payment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    return payment


@router.put("/{payment_id}", response_model=schemas.PaymentOut)
def update_payment(
    payment_id: int,
    payload: schemas.PaymentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    payment = db.query(models.Payment).filter(models.Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if not getattr(current_user, "is_admin", False) and payment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    payment.amount = payload.amount
    payment.currency = payload.currency
    payment.provider = payload.provider
    db.commit()
    db.refresh(payment)
    return payment


@router.delete("/{payment_id}")
def delete_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    payment = db.query(models.Payment).filter(models.Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if not getattr(current_user, "is_admin", False) and payment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    db.delete(payment)
    db.commit()
    return {"msg": "deleted"}

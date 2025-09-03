from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from vpn_api import models, schemas
from vpn_api.database import get_db

router = APIRouter()


@router.post("/", response_model=schemas.TariffOut)
def create_tariff(t: schemas.TariffCreate, db: Session = Depends(get_db)):
    db_t = db.query(models.Tariff).filter(models.Tariff.name == t.name).first()
    if db_t:
        raise HTTPException(status_code=400, detail="Tariff already exists")
    new = models.Tariff(name=t.name, price=t.price)
    db.add(new)
    try:
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(status_code=400, detail="Tariff already exists or DB error") from err
    db.refresh(new)
    return new


@router.get("/")
def list_tariffs(
    db: Session = Depends(get_db), skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)
):
    return db.query(models.Tariff).offset(skip).limit(limit).all()


# Удаление тарифа (если не назначен ни одному пользователю)
@router.delete("/{tariff_id}")
def delete_tariff(tariff_id: int, db: Session = Depends(get_db)):
    tariff = db.query(models.Tariff).filter(models.Tariff.id == tariff_id).first()
    if not tariff:
        raise HTTPException(status_code=404, detail="Tariff not found")
    assigned = db.query(models.UserTariff).filter(models.UserTariff.tariff_id == tariff_id).first()
    if assigned:
        raise HTTPException(
            status_code=400, detail="Tariff is assigned to users and cannot be deleted"
        )
    db.delete(tariff)
    db.commit()
    return {"msg": "tariff deleted", "tariff_id": tariff_id}

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models, schemas
from database import get_db

router = APIRouter()

@router.post("/", response_model=schemas.TariffOut)
def create_tariff(t: schemas.TariffOut, db: Session = Depends(get_db)):
    db_t = db.query(models.Tariff).filter(models.Tariff.name == t.name).first()
    if db_t:
        raise HTTPException(status_code=400, detail="Tariff already exists")
    new = models.Tariff(name=t.name, price=t.price)
    db.add(new)
    db.commit()
    db.refresh(new)
    return new

@router.get("/")
def list_tariffs(db: Session = Depends(get_db)):
    return db.query(models.Tariff).all()

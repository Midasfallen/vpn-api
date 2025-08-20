from fastapi import FastAPI
import models
from database import engine
from auth import router as auth_router
from tariffs import router as tariffs_router

app = FastAPI(title="VPN Backend")

# Создание таблиц
models.Base.metadata.create_all(bind=engine)

# Подключение роутов
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(tariffs_router, prefix="/tariffs", tags=["tariffs"])

@app.get("/")
def root():
    return {"msg": "VPN API is running"}

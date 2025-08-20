from fastapi import FastAPI
from vpn_api import models
from vpn_api.database import engine
from vpn_api.auth import router as auth_router
from vpn_api.tariffs import router as tariffs_router

app = FastAPI(title="VPN Backend")

# Создание таблиц
models.Base.metadata.create_all(bind=engine)

# Подключение роутов
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(tariffs_router, prefix="/tariffs", tags=["tariffs"])

@app.get("/")
def root():
    return {"msg": "VPN API is running"}

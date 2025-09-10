import os

from fastapi import FastAPI

from vpn_api import models
from vpn_api.auth import router as auth_router
from vpn_api.database import engine
from vpn_api.payments import router as payments_router
from vpn_api.peers import router as peers_router
from vpn_api.tariffs import router as tariffs_router

app = FastAPI(title="VPN Backend")

# Примечание: не вызываем автоматически models.Base.metadata.create_all при запуске
# в продакшене — таблицы создаются через Alembic-миграции. Если нужно локально
# инициализировать sqlite/тестовую БД, установите переменную окружения
# DEV_INIT_DB=1 перед запуском.
if os.getenv("DEV_INIT_DB") == "1":
    models.Base.metadata.create_all(bind=engine)

# Подключение роутов
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(tariffs_router, prefix="/tariffs", tags=["tariffs"])
app.include_router(peers_router)
app.include_router(payments_router)


@app.get("/")
def root():
    return {"msg": "VPN API is running"}

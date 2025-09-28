import os

from fastapi import FastAPI

from vpn_api import models
from vpn_api.auth import router as auth_router
from vpn_api.database import engine
from vpn_api.payments import router as payments_router
from vpn_api.peers import router as peers_router
from vpn_api.tariffs import router as tariffs_router

app = FastAPI(
    title="VPN Backend",
    version=os.getenv("APP_VERSION", "0.1.0"),
    description=(
        "VPN Backend API — управление пользователями, тарифами и WireGuard-пирами.\n"
        "Эндпоинты:\n"
        "- /auth — регистрация, логин и управление пользователями\n"
        "- /vpn_peers — CRUD для WireGuard пиров (создание, получение, удаление)\n"
        "- /tariffs — тарифы и назначение тарифов пользователям\n"
        "- /payments — заглушки для платёжных провайдеров\n"
        "Используйте токен Bearer (JWT) из /auth/login для доступа к защищённым маршрутам."
    ),
)

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

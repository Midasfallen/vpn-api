# VPN API

## Описание
REST API для управления пользователями и тарифами VPN-сервиса на FastAPI + SQLAlchemy.

## Быстрый старт

1. Клонируйте репозиторий и создайте виртуальное окружение:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r vpn_api/requirements.txt
```

2. Запустите приложение:

```powershell
uvicorn vpn_api.main:app --reload
```

3. Откройте документацию по адресу http://127.0.0.1:8000/docs

## Переменные окружения
- `SECRET_KEY` — секретный ключ для JWT (обязательно задать в продакшене)
- `ALGORITHM` — алгоритм шифрования JWT (по умолчанию HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES` — время жизни токена (по умолчанию 60)
- `PROMOTE_SECRET` — секрет для назначения первого админа

## Используемые технологии
- FastAPI
- SQLAlchemy
- Pydantic
- Passlib (bcrypt)
- python-jose

## TODO
- Миграции Alembic
- Подтверждение email
- Пагинация
- История тарифов
- Unit-тесты

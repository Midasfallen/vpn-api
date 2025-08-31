# VPN API

## Описание
REST API для управления пользователями и тарифами VPN‑сервиса на FastAPI + SQLAlchemy.

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
- `DATABASE_URL` — URL базы данных для Alembic/приложения (например, postgresql://user:pass@host:5432/dbname)

## Используемые технологии
- FastAPI
- SQLAlchemy
- Pydantic
- Alembic (миграции)
- Passlib (bcrypt)
- python-jose (JWT)
- wireguard (внешняя интеграция — модуль заготовлен)

---

## Техническое описание

Ниже — подробное описание модулей проекта, моделей, API‑эндпоинтов и вспомогательных скриптов. Описание ориентировано на текущую структуру репозитория и реализованный функционал.

### Структура проекта (ключевые файлы)
- vpn_api/
  - main.py — создание FastAPI приложения, подключение роутеров и middlewares.
  - database.py — SQLAlchemy Engine, SessionLocal, Base, и константа DB_URL.
  - models.py — все ORM‑модели (User, Tariff, UserTariff, VpnPeer, Payment).
  - schemas.py — Pydantic‑схемы для запросов/ответов (UserCreate, UserOut, TariffCreate, TariffOut, VpnPeerOut, PaymentOut и т.д.).
  - auth.py — логика регистрации, входа (JWT), получение текущего пользователя, promote admin, валидация пароля.
  - tariffs.py — CRUD для тарифов, список (с пагинацией), назначение тарифа пользователю.
  - vpn.py (или peers.py) — создание/удаление VPN‑пира, генерация конфигурации WireGuard, выдача .conf, проверка статуса подключения.
  - payments.py — создание платежа, webhook обработки уведомлений от Telegram‑бота/провайдера, проверка статуса платежа.
  - peers.py — маршруты CRUD для vpn_peers (если отдельный модуль).
  - alembic/ — конфигурация миграций и папка versions с ревизиями.
  - scripts/check_schema.py — утилита для проверки структуры SQLite тестовой БД.
  - tests/ или vpn_api/*.py (test_*.py) — набор pytest тестов (TestClient), conftest.py обеспечивает тестовую настройку окружения/БД.

### models.py — описание моделей
- User
  - id: Integer, PK
  - email: String, unique, not null
  - hashed_password: String
  - google_id: String, nullable (для Google SignIn)
  - status: Enum(UserStatus) — pending/active/blocked
  - is_admin: Boolean
  - created_at: DateTime(timezone=True)
  - relationships: tariffs (UserTariff), vpn_peers (VpnPeer), payments (Payment)

- Tariff
  - id: Integer, PK
  - name: String, unique, not null
  - description: String, nullable
  - duration_days: Integer, default 30
  - price: Numeric(10,2)
  - created_at: DateTime(timezone=True)
  - relationship: user_tariffs

- UserTariff (история тарифов)
  - id: Integer, PK
  - user_id: FK -> users.id (ON DELETE CASCADE)
  - tariff_id: FK -> tariffs.id (ON DELETE RESTRICT)
  - started_at: DateTime
  - ended_at: DateTime, nullable
  - status: String (active/expired/cancelled)
  - UniqueConstraint на (user_id, tariff_id, started_at) — опционально

- VpnPeer
  - id: Integer, PK
  - user_id: FK -> users.id (ON DELETE CASCADE)
  - wg_private_key: String (секретно — хранение в открытом виде нежелательно для продакшна)
  - wg_public_key: String, unique
  - wg_ip: String, unique (e.g. "10.0.0.5/32")
  - allowed_ips: String, nullable
  - active: Boolean
  - created_at: DateTime

- Payment
  - id: Integer, PK
  - user_id: FK -> users.id (ON DELETE SET NULL или CASCADE в зависимости от политики)
  - amount: Numeric(10,2)
  - currency: String
  - status: Enum(PaymentStatus) — pending/completed/failed/refunded
  - provider: String (telegram_stars, crypto, stripe...)
  - provider_payment_id: String (внешний id для идемпотентности)
  - created_at: DateTime

### database.py
- Экспортирует:
  - DB_URL — строка подключения (используется alembic/env.py при отсутствии sqlalchemy.url в alembic.ini)
  - engine — SQLAlchemy Engine
  - SessionLocal — фабрика сессий
  - Base — declarative_base()
- Предусмотрено поведение: если используется SQLite для тестов, DB_URL указывает на vpn_api/test.db

### alembic/env.py
- Подключает project root в sys.path, затем делает пакетные импорты vpn_api.database и vpn_api.models
- target_metadata = Base.metadata используется для autogenerate
- Если alembic.ini не содержит sqlalchemy.url, берёт DB_URL из vpn_api.database

Примечание: в рабочем коде env.py поправлен импорт, чтобы Pylance разрешал package imports.

### auth.py — ключевые функции/эндпоинты
(основная логика авторизации и управления пользователями)
- register (POST /auth/register)
  - Валидирует email и пароль (минимальная длина, опционально сложность)
  - Хеширует пароль (bcrypt via passlib)
  - Создаёт запись User со статусом pending
  - Возвращает UserOut без поля hashed_password
  - Обрабатывает IntegrityError при дублировании email

- login (POST /auth/login)
  - Принимает email и пароль
  - Проверяет хеш пароля
  - Выдаёт JWT access token (и опционально refresh token)
  - Токен содержит user_id и is_admin флаги

- get_current_user (dependency)
  - Разворачивает токен из Authorization заголовка (Bearer)
  - Декодирует JWT, подаёт user из БД
  - Бросает 401 при ошибке/отсутствии

- promote_user (POST /auth/admin/promote)
  - Позволяет повысить пользователя до admin
  - Поддерживает PROMOTE_SECRET (bootstrap) и админ‑права от текущего пользователя
  - Помечает user.is_admin = True и устанавливает status = active (опционально)

- /auth/me (GET)
  - Возвращает данные текущего пользователя (UserOut)

- Замечания безопасности
  - SECRET_KEY обязателен
  - PROMOTE_SECRET должен храниться безопасно
  - В продакшне рекомендуется отключать bootstrap promote либо ограничить его по IP/времени/ACL

### tariffs.py — управление тарифами
- list_tariffs (GET /tariffs/list)
  - Поддерживает пагинацию: skip, limit
  - Возвращает TariffOut[]

- create_tariff (POST /tariffs)
  - Принимает TariffCreate (name, duration_days, price, description)
  - Проверяет уникальность name
  - Обрабатывает IntegrityError

- assign_tariff (POST /tariffs/assign)
  - Назначает тариф пользователю (создаёт UserTariff запись)
  - При необходимости завершает предыдущий активный тариф (ended_at = now, status = expired)
  - Сделает user.status = active после успешной оплаты/назначения

- delete_tariff (DELETE /tariffs/{id})
  - Запрещает удаление тарифа, если он назначен пользователям либо делает soft‑delete

### vpn.py / peers.py — работа с WireGuard‑пирами
- create_peer (POST /vpn/create_peer)
  - Генерирует пару ключей (wg genkey / wg pubkey или библиотека)
  - Выделяет свободный IP из пула (пулы конфигурируются в настройках)
  - Создаёт запись VpnPeer в БД с wg_private_key (шифрование в продакшне)
  - Добавляет peer в конфигурацию WireGuard на сервере (выполняется внешним скриптом или через subprocess с sudo)
  - Возвращает конфигурацию клиента (.conf) или ссылку на скачивание

- get_config (GET /vpn/config)
  - Возвращает .conf для текущего пользователя (если у пользователя активный тариф)
  - Проверяет срок действия тарифа и статус пользователя

- vpn_status (GET /vpn/status)
  - Возвращает разрешено ли подключение (active/expired), активен ли peer

- delete_peer / deactivate_peer (DELETE/POST)
  - Удаляет или деактивирует peer и удаляет из wg конфигурации

### payments.py — платежи и webhook
- create_payment (POST /payments/create)
  - Регистрирует ожидаемый платёж в БД (status = pending)
  - Возвращает инструкцию/интеракцию для Telegram‑бота или провайдера

- payments_webhook (POST /payments/webhook)
  - Принимает уведомление от бота/провайдера
  - Валидирует подпись/идемпотентность (provider_payment_id)
  - Обновляет запись Payment: status = completed / failed
  - Назначает/активирует тариф (создаёт UserTariff) и генерирует vpn_peer при успешной оплате
  - Ответ 200 для подтверждения приёма webhook

- get_payment_status (GET /payments/status/{payment_id})
  - Возвращает текущий статус платежа

### schemas.py — Pydantic-схемы
- Схемы входных данных:
  - UserCreate (email, password)
  - TariffCreate (name, duration_days, price, description)
  - AssignTariff (user_id, tariff_id)
  - VpnPeerCreate (user_id, optional params)
  - PaymentCreate (user_id, amount, provider, provider_payment_id)

- Схемы вывода:
  - UserOut (id, email, status, is_admin, created_at)
  - TariffOut (id, name, duration_days, price, description)
  - VpnPeerOut (id, wg_public_key, wg_ip, active)
  - PaymentOut (id, amount, status, provider, created_at)

- Денежные поля используют Decimal/DecimalStr (Pydantic) и сопоставляются с Numeric в SQLAlchemy.

### Тесты (pytest)
- Тесты используют fastapi.testclient.TestClient и временную SQLite БД.
- conftest.py:
  - Устанавливает переменные окружения теста (SECRET_KEY, PROMOTE_SECRET)
  - Перенаправляет DATABASE_URL на временную sqlite (vpn_api/test.db или tmp файл)
  - Создаёт/удаляет тестовую БД между тестами/сессиями
- Основные тесты покрывают:
  - Регистрацию / вход / promote admin
  - CRUD тарифа, назначение тарифа
  - CRUD vpn_peers
  - CRUD payments и webhook flow
- Рекомендация: расширить тесты на edge cases, повторные webhooks, race conditions.

### Alembic (миграции)
- Alembic настроен использовать metadata из vpn_api.database.Base
- alembic/env.py добавляет project_root в sys.path и использует vpn_api.database.DB_URL если sqlalchemy.url не задан
- В репозитории есть ревизия, создающая/расширяющая таблицы users, tariffs, user_tariffs, vpn_peers, payments
- На продакшн: если таблицы уже созданы вручную — использовать `alembic stamp head` или выполнить `alembic upgrade head` после резерва БД.

### Скрипты и утилиты
- scripts/check_schema.py — выводит структуру тестовой SQLite БД (PRAGMA table_info)
- alembic/create_db.py — вспомогательный скрипт для создания sqlite DB для тестов (если присутствует)

---

## Безопасность и замечания для продакшн
- SECRET_KEY и PROMOTE_SECRET должны храниться в безопасном хранилище (env vars/secret manager).
- Хранение wg_private_key в базе небезопасно в открытом виде — рекомендуется шифровать или управлять ключами только на сервере (не сохранять приватный ключ в БД в открытом виде).
- Webhook'и необходимо защищать: подпись/токен/корректная валидация provider_payment_id.
- Email подтверждение и сброс пароля нужно реализовать до публичного запуска.
- Настроить HTTPS (nginx + certbot) и систему запуска (systemd, gunicorn/uvicorn).

---

## Дальнейшие шаги (рекомендуется)
1. Проверить миграции на staging Postgres (резервная копия, pg_dump).
2. Реализовать надёжное управление WireGuard (скрипты/служба + audit).
3. Добавить email подтверждение и reset password.
4. Настроить CI (GitHub Actions): тесты + миграции + lint.
5. Улучшить покрытие тестами: webhook, concurrency, security tests.
6. Интегрировать с Flutter клиентом и bot‑платформой (Telegram).

---

Файлы и места, которые следует проверить в первую очередь при деплое:
- vpn_api/database.py — DATABASE_URL
- alembic/env.py и alembic.ini — корректный sqlalchemy.url
- SECRET_KEY и PROMOTE_SECRET в окружении сервера
- Скрипты для приёма webhook и добавления peer в WireGuard

Продолжение следует
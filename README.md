# VPN API

## Описание
REST API для управления пользователями и тарифами VPN‑сервиса на FastAPI + SQLAlchemy.

## Быстрый старт

1. Клонируйте репозиторий и создайте виртуальное окружение:

```powershell
# VPN API — краткая и актуальная инструкция

REST API для управления пользователями, тарифами и WireGuard‑peer'ами на базе FastAPI + SQLAlchemy.

Цель этого README — быстро ввести разработчика в проект, описать как запускать, тестировать и деплоить,
и зафиксировать важные наблюдения из последней отладки CI/Deploy.

## Быстрый старт (локально)

1) Клонировать и создать виртуальное окружение:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r vpn_api/requirements.txt
```

2) Запустить сервис локально:

```powershell
python -m uvicorn vpn_api.main:app --reload
# API docs: http://127.0.0.1:8000/docs
```

3) Запустить тесты:

```powershell
python -m pytest -q
```

Если тесты запускаются в CI, используйте `python -m pytest` (гарантирует корректную загрузку `conftest.py`).

## Важные файлы и примерные локации
- `vpn_api/main.py` — приложение FastAPI и точка входа. Обратите внимание: создание таблиц `create_all` защищено через `DEV_INIT_DB`.
- `vpn_api/database.py` — экспортирует `DB_URL`, `engine`, `SessionLocal`, `Base`.
- `vpn_api/conftest.py` — тестовая настройка: временная SQLite, установка `DATABASE_URL` и `DEV_INIT_DB` для тестов.
- `alembic/env.py` и `alembic.ini` — конфигурация миграций; env.py использует `vpn_api.database.DB_URL`, если `sqlalchemy.url` не задан.
- `.github/workflows/ci.yml` и `.github/workflows/deploy.yml` — CI и деплой: смотрите шаги `build-and-test` и `deploy`.

## Миграции

Примеры команд (локально):
```powershell
alembic revision --autogenerate -m "msg"
alembic upgrade head
alembic downgrade -1
```

Важно: `alembic/env.py` больше не делает «мягкий» fallback к SQLite — нужно обеспечить `DATABASE_URL` для рабочих запусков.

## CI / Deploy — практические нюансы
- Workflow `deploy.yml` выполняет `build-and-test` и затем `deploy` (на `main`).
- Перед деплоем workflow делает `pg_dump` и загружает артефакт `pre-deploy-backup`.
- В CI были проблемы: иногда `pytest` отсутствовал в PATH (решение: всегда устанавливать dev deps и запускать `python -m pytest`).
- Полезные диагностические команды (локально/CI):
  - `python -V` / `python -m pip show pytest`
  - `echo $DEV_INIT_DB, $DATABASE_URL` (PowerShell) или `echo $ENV_VAR` в bash

Особенности GitHub CLI на Windows PowerShell: не используйте `||`/`&&` в PowerShell 5.1 — в скриптах CI-отладке используйте `$LASTEXITCODE` или запускайте PowerShell 7 (`pwsh`).

## Переменные окружения, обязательные для работы
- `DATABASE_URL` — обязателен для рабочих запусков
- `SECRET_KEY`, `PROMOTE_SECRET` — безопасность, требуется в проде
- SSH‑ключ / `DEPLOY_SSH_PRIVATE_KEY`, `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_PATH` — для `deploy.yml`

## Как получить пред‑деплой бэкап (коротко)
- Workflow пытается загрузить артефакт `pre-deploy-backup` (имя в `deploy.yml`).
- Локально/в терминале можно скачать артефакт через `gh`:
  ```powershell
  gh api repos/<owner>/<repo>/actions/artifacts --jq '.artifacts[] | {id:.id,name:.name,created_at:.created_at}'
  gh api repos/<owner>/<repo>/actions/artifacts/<artifact_id>/zip --silent > ./backup.zip
  Expand-Archive -LiteralPath ./backup.zip -DestinationPath ./backup
  ```

Если `gh` возвращает `Bad credentials`, выполните `gh auth login --web` и повторите.

## Частые проблемы и как их исправлять
- "pytest: command not found" в CI — убедитесь, что `requirements-dev.txt` устанавливается и используйте `python -m pytest`.
- Alembic выполняет миграции не туда — проверьте `DATABASE_URL` и `alembic.ini`.
- Не сохраняйте приватные WG‑ключи в БД в открытом виде — шифруйте или храните только публичное.

## Короткий план дальнейших действий (приоритеты)
1. Убедиться, что `deploy` workflow надёжно устанавливает dev‑deps и запускает `python -m pytest` — наблюдать за ближайшим run.
2. Поднять CI‑проверку pre‑deploy backup: убедиться, что `pg_dump` выполняется и артефакт `pre-deploy-backup` доступен.
3. Проверить и зафиксировать процесс удалённого выполнения `alembic upgrade head` в `deploy.yml` (логирование, ошибки).
4. Настроить секреты на сервере/CI: `DATABASE_URL`, `SECRET_KEY`, `PROMOTE_SECRET`, `DEPLOY_SSH_PRIVATE_KEY`.
5. Добавить/уточнить инструкции по локальной разработке и восстановлению БД в `scripts/` и обновить `conftest.py` при необходимости.

## Куда смотреть в первую очередь
- `vpn_api/main.py`, `vpn_api/database.py`, `vpn_api/conftest.py`
- `alembic/env.py`, `alembic/versions/`
- `.github/workflows/deploy.yml` — шаги бэкапа/загрузки артефакта/ssh
- `vpn_api/payments.py` и `vpn_api/peers.py` — бизнес‑логика, которая влияет на создание ресурсов


---
Последнее обновление: 2025-09-10 — содержит наблюдения по CI/Deploy из последних прогонов.


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
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
# VPN API — Полная инструкция

Это подробный и практический README для проекта VPN API — REST‑сервис на FastAPI + SQLAlchemy, управляющий пользователями, тарифами, платежами и WireGuard‑peers.

Документ покрывает: быструю установку, локальную разработку на Windows (включая Python 3.12 и PostgreSQL dev tools для `psycopg2`), тестирование, CI, миграции, интеграцию с `wg-easy` (adapter), деплой и отладочные приёмы.

## Содержание

- О проекте
- Быстрый старт (локально)
- Подробная установка (Windows)
  - Python и venv (рекомендуется 3.12)
  - PostgreSQL (pg_config) — почему важно
  - Установка зависимостей
- Запуск приложения
- Тестирование
  - pytest, pytest-asyncio
  - рекомендации
- Миграции (Alembic)
- CI (GitHub Actions)
- Интеграция wg-easy
- Переменные окружения
- Troubleshooting — частые ошибки и их решения
- Рекомендации по безопасности и продакшн
- Полный список полезных команд


## О проекте

Проект — backend API для управления VPN‑сервисом: регистрация пользователей, управление тарифами, обработка платежей, создание WireGuard peers, генерация конфигураций клиентов. Основные технологии:

- Python 3.12 (рекомендовано для локальной разработки и CI)
- FastAPI
- SQLAlchemy 2.x
- Alembic для миграций
- pytest + pytest-asyncio для тестирования
- wg-easy API wrapper (опционально) для управления WireGuard через сторонний сервис


## Быстрый старт (локально)

Минимальный рабочий набор команд (если у вас уже есть Python 3.12 и PostgreSQL dev tools):

```powershell
# Активировать PowerShell и выполнить из корня репозитория
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r vpn_api/requirements.txt
python -m pip install -r vpn_api/requirements-dev.txt  # dev deps (pytest, pytest-asyncio и т.д.)

# Запуск сервиса
python -m uvicorn vpn_api.main:app --reload
# Документация: http://127.0.0.1:8000/docs

# Запуск тестов
python -m pytest -q
```

Если у вас Windows и отсутствует `pg_config` (см. ниже), установка зависимостей может падать при сборке `psycopg2-binary`. Следуйте разделу "Windows: PostgreSQL/pg_config".


## Подробная установка — Windows (рекомендации)

Этот раздел даёт пошаговый рецепт для разработчика на Windows, чтобы избежать ошибок при установке `psycopg2` и обеспечить полную локальную среду тестирования.

### 1) Установка Python 3.12

- Установите Python 3.12 (рекомендуется стабильная минорная версия) через официальный установщик или winget.
- Проверьте версию:

```powershell
py -3.12 -V
# или
python --version
```

- Создайте виртуальное окружение и активируйте:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
```

> Почему 3.12: пакет `wg-easy-api>=0.1.2` и некоторые колеса в проекте таргетят Python >=3.12. CI в этом репозитории также настроен на Python 3.12.


### 2) Установка PostgreSQL dev tools (pg_config)

`pg_config` требуется при сборке некоторых Python расширений (например, `psycopg2-binary`) из исходников. На Windows проще всего установить официальную сборку PostgreSQL (включает `pg_config.exe`).

Рекомендуемый способ (winget):

```powershell
# выполнить в PowerShell (если winget доступен)
winget install --id PostgreSQL.PostgreSQL.17 -e --accept-package-agreements --accept-source-agreements
```

После установки найдите `pg_config.exe` (обычно: `C:\Program Files\PostgreSQL\<версия>\bin\pg_config.exe`).

Добавьте этот bin каталог в PATH (в сессии PowerShell для текущего окна):

```powershell
$env:Path = 'C:\Program Files\PostgreSQL\17\bin;' + $env:Path
# или актуализируйте путь под вашу версию
```

Проверьте доступность:

```powershell
where.exe pg_config
pg_config --version
```

Если вы не хотите ставить PostgreSQL целиком, можно установить только клиентские инструменты/SDK от Postgres или использовать WSL/контейнер с Linux, где `pg_config` обычно доступен.


### 3) Установка зависимостей

С активированным `.venv` и с `pg_config` в PATH выполните:

```powershell
python -m pip install -r vpn_api/requirements.txt
python -m pip install -r vpn_api/requirements-dev.txt
```

Замечания:
- Если установка падает на `psycopg2-binary` — убедитесь, что `pg_config` в PATH и вы используете ту же архитектуру (x64).
- На некоторых Windows-системах pip может скачать уже готовый wheel и сборка не потребуется; но гарантированно работоспособный подход — наличие `pg_config`.


## Запуск приложения

Запустите локально:

```powershell
python -m uvicorn vpn_api.main:app --reload
```

- API документы: http://127.0.0.1:8000/docs
- Основной модуль приложения — `vpn_api/main.py`


## Тестирование

Тесты написаны с использованием `pytest` и `FastAPI TestClient` + временной SQLite DB (на уровне `conftest.py`). Некоторые тесты используют `pytest-asyncio`.

Команды:

```powershell
# В активированном venv
python -m pip install -r vpn_api/requirements-dev.txt
python -m pytest -q
```

Рекомендации:
- Всегда запускать тесты как `python -m pytest` в CI, чтобы избежать проблем с путями и `conftest.py`.
- Если вы добавляете async‑тесты, убедитесь, что `pytest-asyncio` установлен и совместим с версией `pytest`.


## Alembic — миграции

Работа с миграциями:

```powershell
# Создать миграцию с автогенерацией
alembic revision --autogenerate -m "описание"
# Применить миграции
alembic upgrade head
# Откат на одну ревизию
alembic downgrade -1
```

Замечания:
- `alembic/env.py` использует `vpn_api.database.DB_URL` как fallback, но в рабочих запусках рекомендуется задавать `sqlalchemy.url` в `alembic.ini` или экспортировать `DATABASE_URL`.
- В продакшн перед миграцией делайте резервную копию БД (pg_dump).


## CI (GitHub Actions)

В репозитории есть workflow `ci.yml`, настроенный на Python 3.12 (матрица), устанавливающий dev зависимости и прогоняющий тесты. Важные моменты:

- В CI используйте `python -m pip install -r vpn_api/requirements.txt` и `python -m pip install -r vpn_api/requirements-dev.txt`.
- Запускайте `python -m pytest` (не `pytest` напрямую) для корректного разрешения `conftest.py`.
- CI runner (Ubuntu) обычно имеет готовые колеса для psycopg2, поэтому проблемы, которые встречаются на Windows, там редки.


## Интеграция wg-easy

Проект содержит адаптер для `wg-easy-api` и код в `vpn_api/peers.py`, который при `WG_KEY_POLICY == 'wg-easy'` вызывает `wg-easy` API для создания/удаления клиентов и использует `wg_client_id` в модели `VpnPeer`.

Ключевые замечания:
- Переменные окружения для wg-easy:
  - `WG_EASY_URL` — URL API (например, http://146.103.99.95:51821)
  - `WG_EASY_PASSWORD` — пароль, используемый адаптером для аутентификации
- Адаптер реализован асинхронно; для синхронных участков используется временная обёртка `asyncio.run` — рекомендуется в будущем конвертировать соответствующие обработчики в async.
- В коде реализована компенсация: если удаление/создание клиента на wg-easy прошло, но запись в БД не удалась, код пытается удалить созданный клиент чтобы не оставить «висящие» записи.


## Переменные окружения (обязательные/рекомендуемые)

Общее:
- `DATABASE_URL` — обязательна для рабочих запусков (Postgres). Формат: `postgresql://user:pass@host:5432/dbname`
- `SECRET_KEY` — JWT/секрет приложения
- `PROMOTE_SECRET` — bootstrap секрет для initial promote

Опционально (wg-easy):
- `WG_KEY_POLICY` — установите в `wg-easy` для использования адаптера
- `WG_EASY_URL` — URL wg-easy API
- `WG_EASY_PASSWORD` — пароль wg-easy

Тестовые/локальные переменные:
- `DEV_INIT_DB=true` — позволяет приложению автоматически создавать таблицы локально (при разработке)


## Troubleshooting — частые ошибки и решения

1) Ошибка при установке `psycopg2-binary` (pg_config not found)
- Причина: отсутствует `pg_config` в PATH на Windows.
- Решение: установить PostgreSQL (или client SDK) и добавить `C:\Program Files\PostgreSQL\<версия>\bin` в PATH, либо использовать WSL/контейнер.

2) Тесты падают с ModuleNotFoundError: No module named 'fastapi'
- Причина: зависимость не установлена в активном venv.
- Решение: активировать `.venv` и выполнить `python -m pip install -r vpn_api/requirements.txt`.

3) CI: pytest not found или некорректный `conftest.py`
- Используйте `python -m pip install -r vpn_api/requirements-dev.txt` и `python -m pytest`.

4) Alembic миграции применяются не в ту БД
- Убедитесь, что `DATABASE_URL` или `sqlalchemy.url` в `alembic.ini` указывают на нужную БД. Всегда делайте `pg_dump` перед применением миграций.

5) wg-easy: 401 Unauthorized / DO NOT USE PASSWORD
- wg-easy требует `PASSWORD_HASH` (bcrypt hash) вместо plaintext `PASSWORD` в контейнере. Сгенерируйте хэш и выставьте его через `PASSWORD_HASH` env var или через ui/installer.
- Проверяйте логи контейнера и API endpoint (51821).


## Рекомендации по безопасности и продакшн

- Храните секреты в Secret Manager (GitHub/GCP/AWS) или env vars на сервере; не в репозитории.
- Не храните приватные WG ключи в БД в открытом виде; используйте серверное хранилище ключей или шифруйте поля.
- Настройте HTTPS (nginx/letsencrypt) и систему запуска (systemd) для uvicorn/gunicorn.
- Настройте мониторинг и логирование, бэкапы (pg_dump) перед миграцией/деплоем.


## Полезные команды (сборник)

PowerShell (Windows):

```powershell
# venv
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel

# PATH добавление (только для сессии)
$env:Path = 'C:\Program Files\PostgreSQL\17\bin;' + $env:Path

# install
python -m pip install -r vpn_api/requirements.txt
python -m pip install -r vpn_api/requirements-dev.txt

# run
python -m uvicorn vpn_api.main:app --reload

# tests
python -m pytest -q

# alembic
alembic revision --autogenerate -m "msg"
alembic upgrade head
```

Bash (Linux/macOS):

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r vpn_api/requirements.txt
pip install -r vpn_api/requirements-dev.txt
python -m uvicorn vpn_api.main:app --reload
python -m pytest -q
```


## Что дальше (рекомендации для команды)

- Конвертировать create/delete peer endpoints в async, чтобы корректно вызывать асинхронный адаптер wg-easy без `asyncio.run`.
- Добавить интеграционный smoke тест, который в CI при включённом флаге (например, WG_EASY_SMOKE_TEST=true) проверяет создание/удаление клиента через реальный wg-easy (в staging) — это поможет ловить regressions.
- Подумать об альтернативе локальному `psycopg2` на Windows: `requirements-local.txt` без `psycopg2-binary` + sqlite fallback для работы разработчиков.
- Документировать пошагово процесс бэкапа/восстановления (scripts/restore.sh и scripts/backup.ps1).


---

Последнее обновление: 2025-09-18 — актуально для Windows локальной разработки и CI на Python 3.12.

Если хотите, я могу:
- добавить `requirements-local.txt` и инструкции;
- открыть PR с README и запустить CI;
- или дополнить раздел про `wg-easy` конкретными примерами curl/HTTP запросов и примером создания bcrypt‑хеша для `PASSWORD_HASH`.

Скажите, что предпочитаете, и я выполню следующий шаг.
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

# VPN API

# VPN API — Пошаговая инструкция для разработчиков и деплоя

Это практическое руководство по развёртыванию, тестированию и эксплуатации проекта VPN API (FastAPI + SQLAlchemy) с интеграцией в wg-easy. Документ рассчитан так, чтобы любой инженер, имеющий доступ к серверам и репозиторию, мог корректно настроить окружение и выполнить деплой.

Содержание (быстрый обзор)
- Требования
- Быстрый старт (локально)
- Конфигурация серверов (App host и wg-easy host)
- Переменные окружения и пример `.env.production`
- Бэкап БД и миграции (Alembic)
- Разворачивание и перезапуск сервиса
- Интеграция с wg-easy (auth header, PASSWORD_HASH)
- SSH / apply_peer workflow
- Smoke tests и проверка работоспособности
- Откат/удаление тестовых данных
- CI и GitHub Actions заметки
- Troubleshooting — частые ошибки и решения

---

## Требования
- Python 3.12 (локально и в CI)
- Postgres (production); для локальной разработки можно использовать SQLite
- Docker & docker-compose (для запуска wg-easy на отдельном хосте)
- Доступ по SSH к wg-easy хосту (если вы используете `WG_HOST_SSH` для выполнения скриптов)

---

## Быстрый старт (локально)

1. Клонируйте репозиторий и создайте виртуальное окружение:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r vpn_api/requirements.txt
python -m pip install -r vpn_api/requirements-dev.txt
```

2. Запустите приложение (локально, dev):

```powershell
python -m uvicorn vpn_api.main:app --reload
# Откройте http://127.0.0.1:8000/docs
```

3. Запуск тестов

```powershell
python -m pytest -q
```

---

## Конфигурация серверов

Мы предполагаем два логических хоста (можно быть на отдельных маши-нах или контейнерах):

- App host — где работает Docker Compose с сервисом `web` (FastAPI) и `db` (Postgres) — например: 146.103.99.70
- wg-easy host — где запущен контейнер `wg-easy` и `wg` — например: 62.84.98.109

Основная идея: `web` сервер взаимодействует с wg-easy через HTTP API (wg-easy) для создания/удаления клиентов; дополнительно `web` может запускать хостовые скрипты на wg-easy host по SSH для применения/удаления конфигураций WireGuard (wg).

### Подготовка wg-easy host

1. Установите Docker и запустите контейнер `wg-easy` согласно официальной инструкции.
2. Сгенерируйте `PASSWORD_HASH` и задайте его как переменную окружения контейнера (wg-easy использует bcrypt хэш, а не plaintext пароль).

Пример генерации bcrypt хэша (на Linux / macOS):

```bash
python3 - <<'PY'
from passlib.hash import bcrypt
print(bcrypt.hash('supersecret'))
PY
```

Скопируйте результат и задайте в `docker-compose.yml` wg-easy контейнера:

```yaml
environment:
  - PASSWORD_HASH="$2b$12$...."
  - WG_PORT=51820
  # другие параметры
```

Если вы используете plaintext `WG_EASY_PASSWORD` в коде/adapter-е, убедитесь, что wg-easy сконфигурирован соответствующим образом (чаще используют PASSWORD_HASH).

3. Настройте SSH доступ для App host (если используете `WG_HOST_SSH`):

- На App host создайте/получите публичный ключ (ed25519 рекомендуется):

```bash
# на App host
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""  # если ключа нет
cat ~/.ssh/id_ed25519.pub
```

- Добавьте содержимое `id_ed25519.pub` в `/root/.ssh/authorized_keys` на wg-easy host (root или пользователь, который может выполнять `/srv/vpn-api/scripts/*`).

- Проверьте подключение в Batch режиме:

```bash
ssh -o BatchMode=yes root@62.84.98.109 'echo ok'
```

Если подключение не проходит — проверьте `sshd` конфигурацию и права на `~/.ssh` и `authorized_keys`.

---

## Переменные окружения и пример `.env.production`

Ниже приведён пример содержимого `/.env.production` для App host (вставьте свои значения):

```.env
# Database
DATABASE_URL=postgresql://vpnuser:strongpassword@127.0.0.1:5432/vpndb

# JWT
SECRET_KEY=some-very-long-random-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
PROMOTE_SECRET=bootstrap-secret

# WG / wg-easy
WG_KEY_POLICY=wg-easy
WG_EASY_URL=http://62.84.98.109:8588/   # пример URL API wg-easy
WG_EASY_PASSWORD=supersecret              # если адаптер использует пароль
# либо если wg-easy ожидает PASSWORD_HASH, то в контейнере wg-easy должен быть установлен PASSWORD_HASH

# WG apply helper
WG_APPLY_ENABLED=0                         # 0 — не применять автоматом, 1 — применять (только когда уверены)
WG_HOST_SSH=root@62.84.98.109              # где запускать скрипты apply/remove
WG_INTERFACE=wg0
WG_APPLY_SCRIPT=/srv/vpn-api/scripts/wg_apply.sh
WG_REMOVE_SCRIPT=/srv/vpn-api/scripts/wg_remove.sh
WG_GEN_SCRIPT=/srv/vpn-api/scripts/wg_gen_key.sh

# Опции окружения
DEV_INIT_DB=0
```

Важные замечания:
- `PASSWORD_HASH` генерируется и хранится в окружении wg-easy контейнера; если вы используете адаптер по паролю, adapter должен отправлять ту форму строки, которую wg-easy ожидает (мы обнаружили, что wg-easy сравнивает именно raw-значение, без префикса `Bearer `).
- `WG_APPLY_ENABLED` по умолчанию должен быть `0` в production, чтобы не выполнять `wg set` автоматически без контроля.

---

## Бэкап БД и миграции (обязательно перед upgrade)

На этапе миграций всегда делайте резервную копию БД. Пример (на CI host / runner):

```bash
# Экспорт DATABASE_URL в CI как secret и затем:
python parse_db.py > dbinfo.env
set -a; . ./dbinfo.env; set +a  # экспортирует PGHOST/PGUSER/PGPASSWORD/PGDATABASE
pg_dump --host="$PGHOST" --port="${PGPORT:-5432}" --username="$PGUSER" --dbname="$PGDATABASE" -F c -f backup.dump -v
```

После успешного бэкапа выполняйте миграции:

```bash
DATABASE_URL="postgresql://..." alembic -c alembic.ini upgrade head
```

Если вы используете GitHub Actions — ознакомьтесь с `.github/workflows/run_migrations.yml` (в репозитории). Workflow должен использовать `secrets.DATABASE_URL`.

---

## Разворачивание и перезапуск сервиса (Docker Compose)

1. Остановите старый контейнер (опционально):

```bash
cd /srv/vpn-api
- Настройте HTTPS (nginx/letsencrypt) и систему запуска (systemd) для uvicorn/gunicorn.
```

2. Обновите код (git pull), пересоберите `web`:

```bash
- Настройте мониторинг и логирование, бэкапы (pg_dump) перед миграцией/деплоем.

```

3. Проверьте логи и OpenAPI:

```bash

# Или внутри хоста:
## Полезные команды (сборник)

```

---

## Интеграция с wg-easy — ключевые моменты

1. Authorization header: wg-easy (в studied версиях) сравнивает raw-значение, а не `Bearer <token>`. Если адаптер отправляет `Authorization: Bearer supersecret`, wg-easy может не распознать его и возвращать ошибку. В adapter-е `vpn_api/wg_easy_adapter.py` реализовано поведение, которое отправляет raw-значение при fallback.

2. Проблемы с `PASSWORD_HASH` и `.env`: если в `.env.production` есть символы `$` в значении, не забудьте корректно экранировать/кавычить значение, иначе shell/docker-compose может попытаться интерполировать переменные.

3. Проверка работоспособности wg-easy API (на App host):

```bash
# Проверка raw header
curl -sS -H "Authorization: supersecret" http://62.84.98.109:8588/clients
# Проверка Bearer (если адаптер отправляет Bearer, это может вернуть ошибку)
curl -sS -H "Authorization: Bearer supersecret" http://62.84.98.109:8588/clients
```

4. Логика в коде:
- Adapter сначала пытается использовать обёртку/клиент (если доступен), затем падает на HTTP fallback и отправляет raw header.
- При создании клиента на wg-easy, `peers._create_wg_easy_client` возвращает `{'id':..., 'publicKey':...}` и `VpnPeer.wg_client_id` сохраняется.

---

## SSH / apply_peer workflow

Если вы хотите, чтобы применение конфигурации WireGuard происходило автоматически:

1. Включите `WG_APPLY_ENABLED=1` (включайте только временно/на staging).
2. Убедитесь, что `WG_HOST_SSH` настроен как `user@wg-easy-host` и что App host может подключаться по SSH без пароля.
3. Скрипт `scripts/wg_apply.sh` должен быть доступен на wg-easy host и иметь права на запуск. Проверяйте, что внутри контейнера wg-easy есть интерфейс `wg0` (или заданный `WG_INTERFACE`).

Пример ручного запуска apply (с App host):

```bash
ssh root@62.84.98.109 'sudo /srv/vpn-api/scripts/wg_apply.sh wg0 <publicKey> 10.8.0.14/32'
```

Если в контейнере `web` отсутствует бинарь `ssh`, используйте вызов скрипта с хоста (не внутри контейнера), или располагайте SSH в образе web.

---

## Smoke tests и проверка работоспособности после деплоя

1. Проверка API:

```bash
curl -sS http://127.0.0.1:8000/  # ожидаем {"msg":"VPN API is running"}
PowerShell (Windows):
```

2. Регистрация и базовый admin flow (ручной):

```bash
# register user
curl -sS -X POST -H "Content-Type: application/json" -d '{"email":"user@example.com","password":"password123"}' http://127.0.0.1:8000/auth/register
# register admin
curl -sS -X POST -H "Content-Type: application/json" -d '{"email":"admin@example.com","password":"password123"}' http://127.0.0.1:8000/auth/register
# promote admin (bootstrap)
curl -sS -X POST "http://127.0.0.1:8000/auth/admin/promote?user_id=2&secret=bootstrap-secret"
# create tariff
# obtain admin token via /auth/login, then POST /tariffs/ with Authorization header
```

3. Проверка wg-easy integration (smoke):

- Создайте клиента через внутренние утилиты или через вызываемые endpoint'ы проекта; проверьте, что `wg show` на wg-easy хосте содержит publicKey.

```bash
# example: inside web container or via API
# then on wg-easy host:

```

---

## Откат и удаление тестовых данных

1. Удалите временный тестовый peer на wg-easy (через API или вызовом скрипта):

```bash
# если сохранили wg_client_id:
curl -X DELETE -H "Authorization: supersecret" http://62.84.98.109:8588/clients/<wg_client_id>

# либо вызвать wg_remove.sh
ssh root@62.84.98.109 'sudo /srv/vpn-api/scripts/wg_remove.sh wg0 <publicKey>'
```

2. Удалите временную запись из БД (через psql или admin endpoint'ы). Всегда делайте это аккуратно и после бэкапа.

3. Верните `WG_APPLY_ENABLED=0` и удалите временные SSH-ключи из `authorized_keys` на wg-easy host, если они добавлялись только для деплойного теста.

---

## CI / GitHub Actions (миграции)

В репозитории есть workflow `run_migrations.yml`. Основные моменты:
- Workflow использует `secrets.DATABASE_URL` для подключения и выполняет `pg_dump` перед миграцией, затем `alembic upgrade head`.
- Убедитесь, что `secrets.DATABASE_URL` доступен в Actions перед запуском миграций и что вы подтверждаете вручную (workflow_dispatch с confirm=true).

Пример секции в workflow, куда подставляется секрет:

```yaml
env:
  DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

---

## Troubleshooting — частые ошибки и решения (с примерами)

1) Ошибка: "SECRET_KEY must be set in environment variables"
- Причина: сервис пытается создать/проверить JWT без установленного `SECRET_KEY`.
- Решение: установить `SECRET_KEY` в `.env.production` или в окружении процесса перед запуском.

2) Ошибка: wg-easy возвращает 500 при Authorization: Bearer <token>
- Причина: wg-easy в текущей версии ожидает raw header (например, "Authorization: supersecret").
- Решение: в `vpn_api/wg_easy_adapter.py` гарантируйте отправку raw-значения при HTTP fallback (в репозитории патч уже есть).

3) Ошибка: FileNotFoundError: No such file or directory: 'ssh' внутри контейнера web
- Причина: образ web не содержит ssh client'а.
- Решение: либо выполнить host-side ssh вызовы, либо добавить `openssh-client` в Dockerfile образа web.

4) Alembic не применяет миграцию или подключается не к той базе
- Проверьте `alembic.ini` и `DATABASE_URL`. В CI используйте `parse_db.py` чтобы безопасно распарсить URL и проверить параметры.

---

## Что можно улучшить (рекомендации)

- Добавить опцию сборки образа `web` с `openssh-client` (вариант: мета-параметр BUILD_WITH_SSH=true).
- Покрыть адаптер wg-easy единичным интеграционным тестом (смоки в staging окружении).
- Автоматизировать создание `PASSWORD_HASH` при установке wg-easy в докер‑compose с помощью prestart скрипта.

---

Если хотите, могу подготовить PR с:
- добавлением `requirements-local.txt` и инструкцией для Windows dev,
- улучшениями в Dockerfile (опционально `openssh-client`),
- и отдельным `README-deploy.md` для оператора.

Готов продолжать — скажите, какие разделы хотите дополнить (например: конкретный docker-compose пример для wg-easy, шаблоны systemd unit для uvicorn, или подробная команда для генерации bcrypt hash на Windows).
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

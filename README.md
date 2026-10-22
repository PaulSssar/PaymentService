# Payment Service

Микросервис для обработки платежей с паттернами **Outbox**, **Idempotency** и **Retry with DLQ**.

## Стек

- **Python 3.12+**, FastAPI, Pydantic v2
- **SQLAlchemy 2.0** (async, asyncpg)
- **PostgreSQL 16**
- **RabbitMQ** (через FastStream)
- **Alembic** для миграций
- **Docker + docker-compose**

## Структура

```
app/
├── api/v1/payments.py          # REST API: POST/GET /api/v1/payments
├── core/config.py              # Конфигурация (pydantic-settings)
├── core/security.py            # X-API-Key валидация
├── db/models.py                # ORM: Payment, Outbox
├── db/session.py               # Async engine + session
├── db/repositories/            # CRUD-репозитории
├── schemas/payment.py          # Pydantic v2 схемы
├── services/
│   ├── payment_service.py      # Бизнес-логика + идемпотентность
│   └── webhook.py              # Webhook с retry (exponential backoff)
├── workers/
│   ├── consumer.py             # FastStream consumer обработки
│   └── outbox_publisher.py     # Воркер публикации outbox в RabbitMQ
├── main.py                     # FastAPI app + lifespan
└── alembic/                    # Миграции
```

## Запуск

### 1. Клонировать и настроить

```bash
git clone <repo-url>
cd PaymentService
cp .env.example .env  # если есть
```

### 2. Запустить через docker-compose

```bash
docker-compose up --build
```

Поднимутся 4 сервиса:
- **postgres** — `localhost:5432`
- **rabbitmq** — `localhost:5672` (UI: `localhost:15672`, guest/guest)
- **api** — `localhost:8000`
- **consumer** — воркер обработки
- **outbox-publisher** — воркер публикации outbox

### 3. Проверить health

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

## API

### Создание платежа

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H "Content-Type: application/json" \
  -H "X-API-Key: super-secret-api-key" \
  -H "Idempotency-Key: unique-key-123" \
  -d '{
    "amount": 100.50,
    "currency": "RUB",
    "description": "Оплата заказа #42",
    "webhook_url": "https://example.com/webhooks/payment"
  }'
```

**Ответ (202 Accepted):**

```json
{
  "id": "a3f2b1c4-d5e6-7890-abcd-ef1234567890",
  "amount": 100.50,
  "currency": "RUB",
  "description": "Оплата заказа #42",
  "metadata": null,
  "status": "pending",
  "idempotency_key": "unique-key-123",
  "webhook_url": "https://example.com/webhooks/payment",
  "created_at": "2026-10-20T12:00:00Z",
  "processed_at": null
}
```

### Получить платёж

```bash
curl http://localhost:8000/api/v1/payments/a3f2b1c4-d5e6-7890-abcd-ef1234567890 \
  -H "X-API-Key: super-secret-api-key"
```

### Idempotency

Повторный запрос с тем же `Idempotency-Key` вернёт тот же платёж (202), не создавая дубликат.

## Архитектура обработки

```
┌──────────┐     POST /payments      ┌─────────────┐
│  Client  │ ──────────────────────► │   FastAPI   │
└──────────┘                         │  (API)      │
                                     └──────┬──────┘
                                            │
                                            ▼
                                     ┌─────────────┐
                                     │  PostgreSQL │
                                     │  ┌─────────┐│
                                     │  │ Payment ││
                                     │  │ Outbox  ││
                                     │  └─────────┘│
                                     └──────┬──────┘
                                            │
                  ┌─────────────────────────┼─────────────────────────┐
                  │                         │                         │
                  ▼                         ▼                         ▼
           ┌─────────────┐          ┌─────────────┐          ┌─────────────┐
           │  Consumer   │          │ Outbox      │          │  Webhook    │
           │  (FastStream)│         │ Publisher   │          │  (aiohttp)  │
           │  processing │          │ (poll 2s)   │          │  retry 3x   │
           └─────────────┘          └─────────────┘          └──────┬──────┘
                                                                    │
                                          ┌─────────────────────────┘
                                          ▼
                                   ┌─────────────┐
                                   │  RabbitMQ   │
                                   │ ┌───────────┐│
                                   │ │DLQ / Retry││
                                   │ └───────────┘│
                                   └─────────────┘
```

## Retry и DLQ

- **Webhook**: 3 попытки с exponential backoff (1s, 2s, 4s)
- **Сообщения**: header `x-retry-count`, после 3 nack — в DLQ
- **Outbox**: `FOR UPDATE SKIP LOCKED` для безопасного параллельного чтения

## Локальная разработка

```bash
# Установить зависимости
pip install -e ".[dev]"

# Запустить PostgreSQL и RabbitMQ локально
# Или использовать docker-compose только для них:
docker-compose up postgres rabbitmq

# Запустить API
uvicorn app.main:app --reload --port 8000

# Запустить consumer (отдельний терминал)
python -m app.workers.consumer

# Запустить outbox publisher (отдельний терминал)
python -m app.workers.outbox_publisher
```

## Переменные окружения

| Переменная | Описание | По умолчанию |
|---|---|---|
| `API_KEY` | API ключ для валидации | *(required)* |
| `DATABASE_URL` | PostgreSQL async URL | *(required)* |
| `RABBITMQ_URL` | RabbitMQ URL | `amqp://guest:guest@localhost:5672/` |
| `WEBHOOK_TIMEOUT` | Таймаут webhook (сек) | `10` |
| `WEBHOOK_MAX_RETRIES` | Макс. попыток webhook | `3` |
| `OUTBOX_POLL_INTERVAL` | Интервал опроса outbox (сек) | `2.0` |
| `OUTBOX_BATCH_SIZE` | Размер батча outbox | `50` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |

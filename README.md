# Temporal Take‑Home (Python) — Trellis style

Production-like scaffold implementing the assignment:

- **OrderWorkflow** (parent) with signals, timer (manual review), payment, then child **ShippingWorkflow**.
- Activities wrap provided function stubs and persist to Postgres with **idempotency**.
- **FastAPI** exposes endpoints to start workflows, send signals, and inspect status.
- **Temporal** dev server + **Postgres** via Docker Compose.
- Structured logging and simple tests.

> Entire workflow designed to complete within ~15 seconds using aggressive timeouts/retries.

## Quick Start

```bash
# 1) Clone/extract
cp .env.sample .env

# 2) Launch everything (Temporal, Postgres, app)
docker compose up --build
```

Open:
- API: http://localhost:8000/docs
- Temporal Web (bundled with dev server image): http://localhost:8233  (if enabled in image; otherwise use tctl)

## API

- `POST /orders/{order_id}/start` — body: `{ "payment_id": "pmt-123", "address": {...} }`
- `POST /orders/{order_id}/signals/cancel`
- `POST /orders/{order_id}/signals/update-address` — body: `{ "address": {...} }`
- `GET  /orders/{order_id}/status`

## DB & Migrations

- Postgres container `postgres` with DB `app`.
- Auto-applies migrations from `app/migrations/001_init.sql` on app start.

Tables:
- `orders(id TEXT PRIMARY KEY, state TEXT, address_json JSONB, created_at TIMESTAMPTZ DEFAULT now(), updated_at TIMESTAMPTZ DEFAULT now())`
- `payments(payment_id TEXT PRIMARY KEY, order_id TEXT REFERENCES orders(id), status TEXT, amount INT, created_at TIMESTAMPTZ DEFAULT now())`
- `events(id BIGSERIAL PRIMARY KEY, order_id TEXT, type TEXT, payload_json JSONB, ts TIMESTAMPTZ DEFAULT now())`

## Run tests

> Minimal smoke test to validate workflow wiring. (Temporal’s full test harness is optional.)

```bash
docker compose exec app pytest -q
```

## Notes

- Activities are retried with tight timeouts to surface `flaky_call()` failures/timeouts.
- Payment activity is **idempotent** via unique `payment_id` upsert.
- Shipping runs on a **separate task queue** to demonstrate isolation.

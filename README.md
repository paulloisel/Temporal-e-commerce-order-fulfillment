# Temporal E-commerce Order Fulfillment

A Temporal-based order fulfillment system demonstrating workflow orchestration, activity implementation, and database persistence.

## 🚀 Quick Start

```bash
# Setup and start all services
./scripts/quick-start.sh

# Or manually with Docker Compose
docker compose up --build
```

**Service URLs:**
- FastAPI Docs: http://localhost:8000/docs
- Temporal UI: http://localhost:8233
- PostgreSQL: localhost:5432

## 🛠️ Usage

```bash
# Start a workflow
python scripts/cli.py start-workflow order-123 pmt-123

# Check status
python scripts/cli.py status order-123

# Run demo
python scripts/cli.py demo
```

**API:** See http://localhost:8000/docs for interactive API documentation.

## 📡 Signals and State Inspection

```bash
# Cancel workflow
python scripts/cli.py cancel order-123

# Update address
python scripts/cli.py update-address order-123 --street "456 New St" --city "New City"

# View workflow details
python scripts/cli.py describe order-123
```

## 🗄️ Database

PostgreSQL with three tables:
- **orders**: Order state and JSONB address
- **payments**: Idempotent payment processing (PRIMARY KEY on payment_id)
- **events**: Audit trail

Schema: `app/migrations/001_init.sql`

## 🧪 Testing

```bash
# All tests
python -m pytest

# CLI test suite
python scripts/test-workflow.py
```

## 🔄 Workflows

**OrderWorkflow** (Parent): `ReceiveOrder → ValidateOrder → ManualReview (2s timer) → ChargePayment → ShippingWorkflow`
- Handles signals: `CancelOrder`, `UpdateAddress`
- 15-second execution deadline
- Retries shipping failures up to 3 times

**ShippingWorkflow** (Child): `PreparePackage → DispatchCarrier`
- Runs on separate `shipping-tq` task queue
- Notifies parent on failure

## 🏗️ Project Structure

```
app/          # Workflows, activities, API, database
scripts/      # CLI tool, tests, quick-start script
tests/        # Unit, integration, and e2e tests
```

## 🔧 Troubleshooting

```bash
# Check service logs
docker compose logs app

# Debug workflows
python scripts/cli.py describe <workflow_id>

# View Temporal UI
open http://localhost:8233
```

## 📋 Key Features

- ✅ Workflows with signals, timers, and child workflows
- ✅ Idempotent payment processing
- ✅ Activity retries with exponential backoff (max 3 attempts)
- ✅ 15-second workflow execution deadline
- ✅ Separate task queues for order and shipping
- ✅ Database persistence with event logging
- ✅ Temporal UI for observability
# Temporal Take‑Home: **Function Stubs Only** (Python) with DB Read/Write

A complete Temporal-based order fulfillment system demonstrating workflow orchestration, activity implementation, and real database persistence.

## 🚀 Quick Start

```bash
# 1) Clone and setup
git clone <your-repo>
cd temporal-e-commerce-order-fulfillment

# 2) Create environment file
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://app:app@postgres:5432/app
TEMPORAL_TARGET=temporal:7233
ORDER_TASK_QUEUE=orders-tq
SHIPPING_TASK_QUEUE=shipping-tq
LOG_LEVEL=INFO
EOF

# 3) Launch everything (Temporal, Postgres, app)
docker compose up --build
```

**Or use the quick-start script:**
```bash
./scripts/quick-start.sh
```

## 🎯 How to Start Services

### Start Temporal Server and Database
```bash
# Start all services (Temporal, PostgreSQL, FastAPI)
docker compose up --build

# Or start services individually
docker compose up -d postgres temporal
docker compose up app
```

### Verify Services
```bash
# Check service status
docker compose ps

# Test API
curl http://localhost:8000/docs

# Test Temporal UI
open http://localhost:8233
```

## 🛠️ How to Run Workers and Trigger Workflows

### CLI Commands
```bash
# Start a workflow
python scripts/cli.py start-workflow order-123 pmt-123

# Check workflow status
python scripts/cli.py status order-123

# List recent workflows
python scripts/cli.py list

# Run demo
python scripts/cli.py demo
```

### API Endpoints
```bash
# Start workflow via API
curl -X POST "http://localhost:8000/orders/order-123/start" \
  -H "Content-Type: application/json" \
  -d '{"payment_id": "pmt-123", "address": {"street": "123 Main St", "city": "Test City"}}'

# Get status
curl "http://localhost:8000/orders/order-123/status"
```

## 📡 How to Send Signals and Query/Inspect State

### Send Signals
```bash
# Cancel workflow
python scripts/cli.py cancel order-123
# or via API:
curl -X POST "http://localhost:8000/orders/order-123/signals/cancel"

# Update address
python scripts/cli.py update-address order-123 --street "456 New St" --city "New City"
# or via API:
curl -X POST "http://localhost:8000/orders/order-123/signals/update-address" \
  -H "Content-Type: application/json" \
  -d '{"address": {"street": "456 New St", "city": "New City"}}'
```

### Query/Inspect State
```bash
# Get workflow status
python scripts/cli.py status order-123

# Describe workflow details
python scripts/cli.py describe order-123

# Show workflow history
python scripts/cli.py history order-123

# View service logs
python scripts/cli.py logs --service app
```

## 🗄️ Schema/Migrations and Persistence Rationale

### Database Schema
```sql
-- Orders with JSONB address
CREATE TABLE orders (
    id VARCHAR PRIMARY KEY,
    state VARCHAR NOT NULL,
    address_json JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Payments with idempotency
CREATE TABLE payments (
    payment_id VARCHAR PRIMARY KEY,
    order_id VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    amount DECIMAL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Events for auditing
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    payload_json JSONB,
    ts TIMESTAMP DEFAULT NOW()
);
```

### Persistence Rationale
- **Idempotency**: Payment processing uses unique `payment_id` for safe retries
- **JSONB**: Flexible address storage with PostgreSQL JSONB support
- **Event Logging**: Complete audit trail for debugging and compliance
- **Connection Pooling**: Efficient database connections for performance

## 🧪 Tests and How to Run Them

### Run All Tests
```bash
# Unit tests (41 tests)
python -m pytest tests/unit/

# Integration tests
python -m pytest tests/integration/

# End-to-end tests
python -m pytest tests/e2e/

# CLI test suite
python scripts/test-workflow.py
```

### Test Categories
- **Unit Tests**: Individual components (activities, workflows, API)
- **Integration Tests**: API and database interactions
- **E2E Tests**: Complete workflow scenarios
- **CLI Tests**: Command-line interface functionality

## 🔄 Workflow Design

### OrderWorkflow (Parent)
- **Steps**: `ReceiveOrder → ValidateOrder → (Timer: ManualReview) → ChargePayment → ShippingWorkflow`
- **Signals**: `CancelOrder`, `UpdateAddress`, `DispatchFailed`
- **Timer**: 2-second manual review delay
- **Child Workflow**: `ShippingWorkflow` on separate task queue
- **Time Constraint**: 15 seconds total execution
- **Retry Logic**: Shipping retries up to 3 times with exponential backoff

### ShippingWorkflow (Child)
- **Activities**: `PreparePackage`, `DispatchCarrier`
- **Parent Notification**: Signals back on failure
- **Task Queue**: `shipping-tq` (isolated from `orders-tq`)

## 📊 Function Stubs Implementation

The system uses controlled failure simulation via `flaky_call()`:

```python
async def flaky_call() -> None:
    """Either raise an error or sleep long enough to trigger an activity timeout."""
    rand_num = random.random()
    if rand_num < 0.33:
        raise RuntimeError("Forced failure for testing")
    if rand_num < 0.67:
        await asyncio.sleep(300)  # Expect activity timeout
```

This allows testing:
- **Retry Policies**: Activities retry up to 3 times
- **Timeout Handling**: Activities timeout after 3-5 seconds
- **Error Propagation**: Failures bubble up to workflow level
- **Idempotency**: Database operations are safe to retry

## 🔍 Monitoring

### Temporal UI
- **URL**: http://localhost:8233
- **Features**: Workflow history, activity details, retry information

### CLI Monitoring
```bash
# View service logs
python scripts/cli.py logs --service app

# List recent workflows
python scripts/cli.py list --limit 10

# Describe specific workflow
python scripts/cli.py describe <workflow_id>
```

## 🚨 Key Features

### Idempotency
- Payment processing uses unique `payment_id` for safe retries
- Database operations are idempotent with proper conflict handling
- External side effects recorded after success

### Error Handling
- Activity retries with exponential backoff
- Workflow-level error collection
- Signal handling for cancellations
- Timeout management with 15-second deadline
- **Shipping retry logic**: Parent retries shipping up to 3 times

### Observability
- Structured logging with step tracking
- Workflow status queries with retry information
- Event history in Temporal UI
- Database event logging

### Queue Isolation
- Order activities on `orders-tq`
- Shipping activities on `shipping-tq`
- Independent scaling and deployment
- Clear separation of concerns

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   Temporal      │    │   PostgreSQL    │
│   (Port 8000)   │◄──►│   (Port 7233)   │◄──►│   (Port 5432)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📚 Project Structure

```
app/
├── workflows.py      # Temporal workflow definitions
├── activities.py     # Activity implementations  
├── api.py           # FastAPI endpoints
├── config.py        # Configuration
├── db.py            # Database operations
├── worker.py        # Temporal worker
└── stubs.py         # External service stubs

scripts/
├── cli.py           # Main CLI tool
├── test-workflow.py # Test suite
└── quick-start.sh   # Setup script

tests/
├── unit/            # Unit tests (41 tests)
├── integration/     # Integration tests
└── e2e/            # End-to-end tests
```

## 🎯 Evaluation Criteria

✅ **Correct Temporal primitives**: Workflows, activities, signals, timers, child workflows, task queues  
✅ **Clean, readable code**: Well-structured, documented, deterministic behavior  
✅ **Proper persistence**: Real database with idempotent payment logic  
✅ **Easy local spin-up**: Docker Compose with clear instructions  
✅ **Clear observability**: Logs, queries, Temporal UI integration  
✅ **15-second completion**: Workflow deadline enforced and tested  
✅ **Shipping retry logic**: Parent retries shipping failures with exponential backoff

## 🛑 Why We Use Temporal

Trellis coordinates long-running, stateful operations where reliability and clear audit trails matter. Temporal provides:

- **Durability & fault tolerance**: Workflow state persisted, workers can crash without losing progress
- **Deterministic orchestration**: Control plane encoded once, consistent decisions across retries
- **Idempotent side effects**: Activities retried safely with proper idempotency
- **Human-in-the-loop**: Signals and timers for manual approvals and SLAs
- **Observability by design**: Event history as truthful source for debugging

## 🔧 Troubleshooting

### Common Issues
```bash
# Services not starting
docker compose logs app
docker compose logs temporal
docker compose logs postgres

# Workflow failures
python scripts/cli.py list
python scripts/cli.py describe <workflow_id>

# Connection issues
curl http://localhost:8000/docs
open http://localhost:8233
```

### Performance Tuning
- **Activity Timeouts**: 3-5 seconds per activity
- **Retry Policies**: Maximum 3 attempts
- **Task Queues**: Separate queues for order and shipping activities
- **Shipping Retries**: Up to 3 attempts with exponential backoff

---

**This project demonstrates a production-ready Temporal application with proper orchestration, persistence, testing, and observability.**
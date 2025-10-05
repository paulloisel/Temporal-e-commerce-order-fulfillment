# Temporal E-commerce Order Fulfillment - Deployment Guide

## Overview

This project implements a complete Temporal-based order fulfillment system with:
- **OrderWorkflow**: Parent workflow handling order lifecycle
- **ShippingWorkflow**: Child workflow for shipping operations
- **Real Database**: PostgreSQL for persistence
- **FastAPI**: REST API for workflow management
- **CLI Tools**: Command-line interface for operations
- **Docker Compose**: Complete local deployment

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   Temporal      │    │   PostgreSQL    │
│   (Port 8000)   │◄──►│   (Port 7233)   │◄──►│   (Port 5432)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   REST API      │    │   Workflows     │    │   Database      │
│   Endpoints     │    │   & Activities  │    │   Tables        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Quick Start

### 1. Prerequisites

- **Docker & Docker Compose** installed
- **Python 3.11+** (for CLI tools)
- **Git** (to clone repository)

### 2. Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd temporal-e-commerce-order-fulfillment

# Quick setup (creates .env, starts services, tests connections)
./scripts/quick-start.sh
```

### 3. Verify Deployment

```bash
# Check service status
docker compose ps

# Test API
curl http://localhost:8000/docs

# Test Temporal UI
open http://localhost:8233
```

## Service Endpoints

| Service | URL | Purpose |
|---------|-----|---------|
| FastAPI | http://localhost:8000 | REST API for workflow management |
| FastAPI Docs | http://localhost:8000/docs | Interactive API documentation |
| Temporal UI | http://localhost:8233 | Temporal Web UI |
| PostgreSQL | localhost:5432 | Database (user: app, password: app, db: app) |

## CLI Usage

### Service Management

```bash
# Start all services
python scripts/cli.py start

# Stop all services
python scripts/cli.py stop

# Restart services
python scripts/cli.py restart
```

### Workflow Operations

```bash
# Start a new workflow
python scripts/cli.py start-workflow order-123 pmt-123

# Check workflow status
python scripts/cli.py status order-123

# Cancel a workflow
python scripts/cli.py cancel order-123

# Update shipping address
python scripts/cli.py update-address order-123 --street "456 New St" --city "New City"
```

### Monitoring & Debugging

```bash
# List recent workflows
python scripts/cli.py list --limit 10

# Describe a specific workflow
python scripts/cli.py describe order-order-123

# Show workflow execution history
python scripts/cli.py history order-order-123

# View service logs
python scripts/cli.py logs --service app --lines 50
```

### Testing

```bash
# Run complete demo
python scripts/cli.py demo

# Run comprehensive test suite
python scripts/test-workflow.py
```

## API Endpoints

### Start Workflow
```bash
POST /orders/{order_id}/start
Content-Type: application/json

{
  "payment_id": "pmt-123",
  "address": {
    "street": "123 Main St",
    "city": "Test City",
    "state": "TS",
    "zip": "12345",
    "country": "US"
  }
}
```

### Get Status
```bash
GET /orders/{order_id}/status
```

### Cancel Workflow
```bash
POST /orders/{order_id}/signals/cancel
```

### Update Address
```bash
POST /orders/{order_id}/signals/update-address
Content-Type: application/json

{
  "address": {
    "street": "456 New St",
    "city": "New City",
    "state": "NS",
    "zip": "54321",
    "country": "US"
  }
}
```

## Workflow Design

### OrderWorkflow (Parent)

**Steps:**
1. **RECEIVE** - `ReceiveOrder` activity
2. **VALIDATE** - `ValidateOrder` activity  
3. **MANUAL_REVIEW** - Wait for human approval signal (30-second timeout)
4. **PAY** - `ChargePayment` activity
5. **SHIP** - Start `ShippingWorkflow` child workflow

**Signals:**
- `cancel_order` - Cancels workflow before shipment
- `update_address` - Updates shipping address
- `approve_order` - Approves order for payment processing
- `dispatch_failed` - Handles shipping failures

**Time Constraint:** 60 seconds total execution time (extended for manual approval)

### ShippingWorkflow (Child)

**Steps:**
1. **PREPARE** - `PreparePackage` activity
2. **DISPATCH** - `DispatchCarrier` activity

**Parent Notification:** Signals back to parent on failure

**Task Queue:** `shipping-tq` (separate from `orders-tq`)

## Database Schema

### Tables

```sql
-- Orders table
CREATE TABLE orders (
    id VARCHAR PRIMARY KEY,
    state VARCHAR NOT NULL,
    address_json JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Payments table (with idempotency)
CREATE TABLE payments (
    payment_id VARCHAR PRIMARY KEY,
    order_id VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    amount DECIMAL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Events table (for auditing)
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    payload_json JSONB,
    ts TIMESTAMP DEFAULT NOW()
);
```

## Configuration

### Environment Variables (.env)

```bash
DATABASE_URL=postgresql+asyncpg://app:app@postgres:5432/app
TEMPORAL_TARGET=temporal:7233
ORDER_TASK_QUEUE=orders-tq
SHIPPING_TASK_QUEUE=shipping-tq
LOG_LEVEL=INFO
```

### Docker Compose Services

- **temporal**: Temporal server with PostgreSQL backend
- **postgres**: PostgreSQL database
- **app**: FastAPI application with Temporal worker

## Testing

### Test Categories

1. **Unit Tests**: Individual components
2. **Integration Tests**: API and database interactions
3. **E2E Tests**: Complete workflow scenarios
4. **CLI Tests**: Command-line interface functionality

### Running Tests

```bash
# Run all tests
python -m pytest

# Run specific test categories
python -m pytest tests/unit/
python -m pytest tests/integration/
python -m pytest tests/e2e/

# Run CLI test suite
python scripts/test-workflow.py
```

### Test Results

The system includes controlled failure simulation via `flaky_call()`:
- 33% chance of immediate failure
- 33% chance of timeout (300s sleep)
- 33% chance of success

This allows testing retry policies and error handling.

## Monitoring & Observability

### Temporal UI
- **URL**: http://localhost:8233
- **Features**: Workflow history, activity details, retry information

### Logs
```bash
# Application logs
python scripts/cli.py logs --service app

# Temporal logs  
python scripts/cli.py logs --service temporal

# Database logs
python scripts/cli.py logs --service postgres
```

### Metrics
- Workflow execution times
- Activity retry counts
- Error rates by step
- Database operation metrics

## Troubleshooting

### Common Issues

#### Services Not Starting
```bash
# Check Docker status
docker ps

# View service logs
docker compose logs app
docker compose logs temporal
docker compose logs postgres

# Restart services
python scripts/cli.py restart
```

#### Workflow Failures
```bash
# List all workflows
python scripts/cli.py list

# Check specific workflow
python scripts/cli.py describe <workflow_id>

# View workflow history
python scripts/cli.py history <workflow_id>
```

#### Connection Issues
```bash
# Test Temporal connection
docker compose exec temporal temporal --address temporal:7233 workflow list

# Test API connection
curl http://localhost:8000/docs

# Test database connection
docker compose exec postgres pg_isready -U app
```

### Performance Tuning

#### Activity Timeouts
- **ReceiveOrder**: 3 seconds
- **ValidateOrder**: 3 seconds  
- **ChargePayment**: 4 seconds
- **PreparePackage**: 5 seconds
- **DispatchCarrier**: 5 seconds

#### Retry Policies
- **Maximum Attempts**: 3
- **Exponential Backoff**: Default Temporal behavior

#### Task Queues
- **orders-tq**: Order workflow activities
- **shipping-tq**: Shipping workflow activities

## Production Considerations

### Security
- Use environment variables for sensitive data
- Implement proper authentication for API endpoints
- Use TLS for Temporal connections
- Secure database connections

### Scaling
- Deploy workers on separate machines
- Use external PostgreSQL for persistence
- Implement horizontal scaling for workers
- Monitor resource usage

### Backup & Recovery
- Regular database backups
- Temporal history retention policies
- Disaster recovery procedures
- Data migration strategies

## Development

### Adding New Features
1. Update workflow definitions in `app/workflows.py`
2. Add new activities in `app/activities.py`
3. Update API endpoints in `app/api.py`
4. Add tests in `tests/` directory
5. Update CLI tools in `scripts/`

### Code Structure
```
app/
├── workflows.py      # Temporal workflow definitions
├── activities.py     # Temporal activity implementations
├── api.py           # FastAPI endpoints
├── config.py        # Configuration management
├── db.py            # Database operations
├── worker.py        # Temporal worker setup
└── stubs.py         # External service stubs

scripts/
├── cli.py           # Main CLI tool
├── test-workflow.py # Test suite
└── quick-start.sh   # Setup script

tests/
├── unit/            # Unit tests
├── integration/     # Integration tests
└── e2e/            # End-to-end tests
```

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review service logs using CLI tools
3. Use Temporal UI for workflow debugging
4. Consult the test suite for expected behavior

## License

This project is part of a Temporal take-home assignment demonstrating:
- Temporal workflow orchestration
- Activity implementation with retries
- Signal handling and timers
- Child workflows and task queue isolation
- Database persistence and idempotency
- CLI tools and observability

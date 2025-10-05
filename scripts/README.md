# Temporal E-commerce Order Fulfillment - CLI Scripts

This directory contains command-line tools for managing and testing the Temporal deployment.

## Scripts Overview

### 1. `cli.py` - Main CLI Tool
Comprehensive command-line interface for managing the Temporal deployment.

**Usage:**
```bash
python scripts/cli.py <command> [options]
```

**Available Commands:**
- `start` - Start all services (Temporal, PostgreSQL, App)
- `stop` - Stop all services
- `restart` - Restart all services
- `start-workflow <order_id> <payment_id>` - Start a new workflow
- `status <order_id>` - Get workflow status
- `cancel <order_id>` - Cancel a workflow
- `update-address <order_id> [options]` - Update workflow address
- `approve <order_id>` - Approve workflow for payment
- `list [--limit N]` - List recent workflows
- `describe <workflow_id>` - Describe a specific workflow
- `history <workflow_id>` - Show workflow execution history
- `logs [--service SERVICE] [--lines N]` - Show service logs
- `demo` - Run a complete workflow demonstration

**Examples:**
```bash
# Start services
python scripts/cli.py start

# Start a workflow
python scripts/cli.py start-workflow order-123 pmt-123

# Check status
python scripts/cli.py status order-123

# Cancel a workflow
python scripts/cli.py cancel order-123

# Update address
python scripts/cli.py update-address order-123 --street "456 New St" --city "New City"

# Approve workflow for payment
python scripts/cli.py approve order-123

# List workflows
python scripts/cli.py list --limit 10

# Describe a workflow
python scripts/cli.py describe order-order-123

# Show workflow history
python scripts/cli.py history order-order-123

# Show app logs
python scripts/cli.py logs --service app --lines 100

# Run demo
python scripts/cli.py demo
```

### 2. `quick-start.sh` - Quick Setup Script
Bash script to quickly set up and start the entire deployment.

**Usage:**
```bash
./scripts/quick-start.sh
```

**What it does:**
- Creates `.env` file if it doesn't exist
- Starts all services with Docker Compose
- Waits for services to be ready
- Tests all service connections
- Provides usage instructions

### 3. `test-workflow.py` - Comprehensive Test Suite
Python script that runs comprehensive tests of the workflow system.

**Usage:**
```bash
python scripts/test-workflow.py
```

**Test Categories:**
1. **Successful Workflow** - Tests normal workflow completion
2. **Workflow Cancellation** - Tests cancel signal handling
3. **Address Update** - Tests address update signal
4. **Batch Workflows** - Tests multiple workflows in parallel

**Output:**
- Real-time test progress
- Detailed test results
- JSON report saved to `test_report.json`
- Success/failure summary

## Prerequisites

1. **Docker and Docker Compose** installed
2. **Python 3.11+** with required packages:
   ```bash
   pip install aiohttp temporalio
   ```
3. **Services running** (use `quick-start.sh` or `cli.py start`)

## Quick Start

1. **Set up and start services:**
   ```bash
   ./scripts/quick-start.sh
   ```

2. **Run a demo:**
   ```bash
   python scripts/cli.py demo
   ```

3. **Run comprehensive tests:**
   ```bash
   python scripts/test-workflow.py
   ```

## Service Endpoints

When services are running:
- **FastAPI Docs**: http://localhost:8000/docs
- **Temporal UI**: http://localhost:8233
- **PostgreSQL**: localhost:5432 (user: app, password: app, db: app)

## Troubleshooting

### Services not starting
```bash
# Check Docker status
docker ps

# View service logs
python scripts/cli.py logs --service app
python scripts/cli.py logs --service temporal
python scripts/cli.py logs --service postgres

# Restart services
python scripts/cli.py restart
```

### Workflow issues
```bash
# List all workflows
python scripts/cli.py list

# Check specific workflow
python scripts/cli.py describe <workflow_id>

# View workflow history
python scripts/cli.py history <workflow_id>
```

### Connection issues
```bash
# Test Temporal connection
docker compose exec temporal temporal --address temporal:7233 workflow list

# Test API connection
curl http://localhost:8000/docs

# Test database connection
docker compose exec postgres pg_isready -U app
```

## Development

### Adding new CLI commands
Edit `scripts/cli.py` and add new subcommands to the argument parser.

### Adding new tests
Edit `scripts/test-workflow.py` and add new test methods to the `WorkflowTester` class.

### Customizing the deployment
Edit `docker-compose.yml` and environment variables in `.env`.

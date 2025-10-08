# CLI Scripts

Command-line tools for managing and testing the Temporal deployment.

## `cli.py` - Main CLI Tool

```bash
python scripts/cli.py <command> [options]
```

**Common Commands:**
- `start` / `stop` / `restart` - Manage services
- `start-workflow <order_id> <payment_id>` - Start workflow
- `status <order_id>` - Get workflow status
- `cancel <order_id>` - Cancel workflow
- `update-address <order_id> [options]` - Update address
- `list` / `describe <id>` / `history <id>` - Inspect workflows
- `logs [--service SERVICE]` - View logs
- `demo` - Run demonstration

## `quick-start.sh` - Setup Script

```bash
./scripts/quick-start.sh
```

Sets up environment, starts services, and tests connections.

## `test-workflow.py` - Test Suite

```bash
python scripts/test-workflow.py
```

Runs comprehensive workflow tests (successful workflow, cancellation, address updates, batch workflows).

## Quick Start

```bash
# Setup and start
./scripts/quick-start.sh

# Run demo
python scripts/cli.py demo

# Run tests
python scripts/test-workflow.py
```

## Troubleshooting

See main README.md or use:
```bash
python scripts/cli.py logs --service app
python scripts/cli.py describe <workflow_id>
```

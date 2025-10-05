# Testing Guide

## Overview

This guide covers the comprehensive testing strategy for the Temporal E-commerce Order Fulfillment system, including unit tests, integration tests, end-to-end tests, and CLI testing tools.

## Test Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_activities.py   # Activity function tests
│   ├── test_api.py         # API endpoint tests
│   ├── test_db.py          # Database operation tests
│   └── test_workflows.py   # Workflow logic tests
├── integration/            # Integration tests
│   ├── test_api_integration.py  # API with real services
│   └── test_workflow_integration.py  # Workflow with real Temporal
└── e2e/                   # End-to-end tests
    ├── test_complete_workflows.py  # Full workflow scenarios
    ├── test_error_scenarios.py    # Error handling tests
    └── test_signal_handling.py    # Signal processing tests
```

## Running Tests

### All Tests
```bash
python -m pytest
```

### Specific Categories
```bash
# Unit tests only
python -m pytest tests/unit/

# Integration tests only
python -m pytest tests/integration/

# End-to-end tests only
python -m pytest tests/e2e/

# Specific test file
python -m pytest tests/unit/test_activities.py
```

### With Coverage
```bash
# Install coverage
pip install pytest-cov

# Run with coverage
python -m pytest --cov=app --cov-report=html
```

### CLI Test Suite
```bash
# Comprehensive workflow testing
python scripts/test-workflow.py
```

## Test Categories

### 1. Unit Tests

Test individual components in isolation with mocks.

#### Activity Tests (`test_activities.py`)
```python
@pytest.mark.asyncio
async def test_receive_order_success():
    """Test successful order reception."""
    result = await receive_order("test-db-url", "order-123")
    assert result["order_id"] == "order-123"
    assert "items" in result
```

#### API Tests (`test_api.py`)
```python
def test_start_workflow():
    """Test workflow start endpoint."""
    response = client.post(
        "/orders/test-order/start",
        json={"payment_id": "pmt-123", "address": {}}
    )
    assert response.status_code == 200
    assert "workflow_id" in response.json()
```

#### Database Tests (`test_db.py`)
```python
@pytest.mark.asyncio
async def test_orders_crud():
    """Test order CRUD operations."""
    async with db_pool.acquire() as conn:
        # Test insert
        await conn.execute(
            "INSERT INTO orders (id, state) VALUES ($1, $2)",
            "test-order", "PENDING"
        )
        
        # Test select
        row = await conn.fetchrow("SELECT * FROM orders WHERE id = $1", "test-order")
        assert row["state"] == "PENDING"
```

#### Workflow Tests (`test_workflows.py`)
```python
@pytest.mark.asyncio
async def test_order_workflow_logic():
    """Test workflow logic with mocked activities."""
    with patch('app.activities.receive_order') as mock_receive:
        mock_receive.return_value = {"order_id": "test", "items": []}
        
        result = await temporal_environment.execute_workflow(
            OrderWorkflow.run,
            "test-db", "order-123", "pmt-123", {}
        )
        
        assert result["status"] == "completed"
```

### 2. Integration Tests

Test components working together with real services.

#### API Integration (`test_api_integration.py`)
```python
@pytest.mark.asyncio
async def test_workflow_lifecycle():
    """Test complete workflow lifecycle via API."""
    # Start workflow
    response = await client.post("/orders/integration-test/start", json={
        "payment_id": "pmt-integration",
        "address": {"street": "123 Test St", "city": "Test", "state": "TS", "zip": "12345", "country": "US"}
    })
    assert response.status_code == 200
    
    # Check status
    status_response = await client.get("/orders/integration-test/status")
    assert status_response.status_code == 200
    assert "step" in status_response.json()
```

#### Workflow Integration (`test_workflow_integration.py`)
```python
@pytest.mark.asyncio
async def test_workflow_with_real_temporal():
    """Test workflow execution with real Temporal server."""
    handle = await temporal_client.start_workflow(
        OrderWorkflow.run,
        args=["test-db", "integration-order", "pmt-integration", {}],
        id="integration-test-workflow",
        task_queue="orders-tq"
    )
    
    result = await handle.result()
    assert result["status"] in ["completed", "failed"]
```

### 3. End-to-End Tests

Test complete user scenarios with real deployment.

#### Complete Workflows (`test_complete_workflows.py`)
```python
@pytest.mark.asyncio
async def test_happy_path_complete_order_flow():
    """Test successful order completion end-to-end."""
    # This test runs against real services
    # and verifies the complete order lifecycle
    pass

@pytest.mark.asyncio
async def test_order_cancellation_flow():
    """Test order cancellation end-to-end."""
    # Tests cancellation signal handling
    pass
```

#### Error Scenarios (`test_error_scenarios.py`)
```python
@pytest.mark.asyncio
async def test_payment_failure_retry_flow():
    """Test payment failure and retry logic."""
    # Tests flaky_call() failure simulation
    # and retry policy behavior
    pass
```

#### Signal Handling (`test_signal_handling.py`)
```python
@pytest.mark.asyncio
async def test_cancel_signal_processing():
    """Test cancel signal processing."""
    # Tests signal handling in running workflows
    pass
```

## CLI Testing

### Workflow Test Suite (`scripts/test-workflow.py`)

The CLI test suite provides comprehensive testing of the workflow system:

```bash
python scripts/test-workflow.py
```

**Test Categories:**
1. **Successful Workflow**: Tests normal completion
2. **Workflow Cancellation**: Tests cancel signal
3. **Address Update**: Tests address update signal
4. **Batch Workflows**: Tests multiple workflows in parallel

**Output:**
- Real-time test progress
- Detailed results per test
- JSON report (`test_report.json`)
- Success/failure summary

### CLI Demo (`scripts/cli.py demo`)

```bash
python scripts/cli.py demo
```

**What it does:**
1. Starts a new workflow
2. Monitors progress for 5 seconds
3. Shows step transitions
4. Displays final status
5. Shows workflow in Temporal CLI

## Test Data Management

### Database Fixtures
```python
@pytest.fixture
async def clean_db(db_pool):
    """Clean database before each test."""
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM events")
        await conn.execute("DELETE FROM payments")
        await conn.execute("DELETE FROM orders")
```

### Mock Data
```python
SAMPLE_ORDER = {
    "order_id": "test-order-123",
    "items": [{"sku": "ABC", "qty": 1}],
    "address": {
        "street": "123 Test St",
        "city": "Test City",
        "state": "TS",
        "zip": "12345",
        "country": "US"
    }
}
```

## Flaky Call Testing

The system uses controlled failure simulation for testing:

```python
async def flaky_call() -> None:
    """Either raise an error or sleep long enough to trigger an activity timeout."""
    rand_num = random.random()
    if rand_num < 0.33:
        raise RuntimeError("Forced failure for testing")
    if rand_num < 0.67:
        await asyncio.sleep(300)  # Expect activity timeout
```

**Testing Scenarios:**
- **33% Immediate Failure**: Tests retry logic
- **33% Timeout**: Tests timeout handling
- **33% Success**: Tests normal flow

## Performance Testing

### Load Testing
```bash
# Test multiple workflows in parallel
python scripts/test-workflow.py  # Includes batch testing

# Manual load test
for i in {1..10}; do
  python scripts/cli.py start-workflow "load-test-$i" "pmt-$i" &
done
wait
```

### Timeout Testing
```bash
# Test 15-second deadline
python scripts/cli.py start-workflow timeout-test pmt-timeout
python scripts/cli.py status timeout-test  # Monitor until completion
```

## Continuous Integration

### GitHub Actions Example
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      - name: Start services
        run: docker compose up -d
      - name: Wait for services
        run: sleep 30
      - name: Run tests
        run: python -m pytest --cov=app
      - name: Run CLI tests
        run: python scripts/test-workflow.py
```

## Test Reports

### Coverage Reports
```bash
# Generate HTML coverage report
python -m pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### JSON Test Reports
```bash
# CLI test suite generates detailed JSON report
python scripts/test-workflow.py
cat test_report.json | jq '.summary'
```

### Temporal UI
- **URL**: http://localhost:8233
- **Use for**: Workflow history analysis, activity details, retry information

## Debugging Tests

### Verbose Output
```bash
python -m pytest -v
```

### Specific Test
```bash
python -m pytest tests/unit/test_activities.py::test_receive_order_success -v
```

### Debug Mode
```bash
python -m pytest --pdb
```

### Log Output
```bash
python -m pytest -s  # Don't capture output
```

## Best Practices

### Test Organization
- One test file per module
- Descriptive test names
- Arrange-Act-Assert pattern
- Independent tests (no dependencies)

### Mocking Strategy
- Mock external dependencies
- Use real database for integration tests
- Mock Temporal for unit tests
- Use real Temporal for E2E tests

### Data Management
- Clean database between tests
- Use fixtures for common data
- Avoid hardcoded test data
- Use factories for complex objects

### Error Testing
- Test both success and failure paths
- Test timeout scenarios
- Test retry logic
- Test signal handling

## Troubleshooting

### Common Issues

#### Tests Hanging
```bash
# Check if services are running
docker compose ps

# Check service logs
docker compose logs app
```

#### Database Connection Issues
```bash
# Test database connection
docker compose exec postgres pg_isready -U app

# Reset database
docker compose down
docker compose up -d
```

#### Temporal Connection Issues
```bash
# Test Temporal connection
docker compose exec temporal temporal --address temporal:7233 workflow list
```

### Test Environment Setup
```bash
# Ensure clean environment
docker compose down
docker compose up -d
sleep 10

# Run tests
python -m pytest
```

## Metrics and Monitoring

### Test Metrics
- Test execution time
- Success/failure rates
- Coverage percentages
- Flaky test identification

### Performance Metrics
- Workflow completion times
- Activity execution times
- Database query performance
- API response times

### Monitoring Commands
```bash
# View test results
cat test_report.json | jq '.summary'

# Check coverage
python -m pytest --cov=app --cov-report=term

# Monitor workflows
python scripts/cli.py list --limit 20
```

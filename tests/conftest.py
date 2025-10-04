"""
Test configuration and fixtures for the Temporal E-commerce Order Fulfillment System.
"""
import asyncio
import pytest
import asyncpg
import os
import tempfile
import shutil
from typing import AsyncGenerator, Dict, Any
from temporalio.testing import WorkflowEnvironment
from temporalio.client import Client
from temporalio.worker import Worker

# Test configuration
TEST_DATABASE_URL = "postgresql://test:test@localhost:5433/test_db"
TEST_ORDER_TASK_QUEUE = "test-orders-tq"
TEST_SHIPPING_TASK_QUEUE = "test-shipping-tq"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def temporal_environment() -> AsyncGenerator[WorkflowEnvironment, None]:
    """Create a Temporal test environment."""
    async with WorkflowEnvironment() as env:
        yield env

@pytest.fixture(scope="session")
async def temporal_client(temporal_environment: WorkflowEnvironment) -> Client:
    """Get a Temporal client connected to the test environment."""
    return temporal_environment.client

@pytest.fixture(scope="session")
async def db_pool() -> AsyncGenerator[asyncpg.Pool, None]:
    """Create a database connection pool for testing."""
    # Note: In real tests, you'd want to use a test database
    # For now, we'll use the main database URL
    from app.config import DATABASE_URL
    pool = await asyncpg.create_pool(DATABASE_URL.replace("+asyncpg", ""))
    yield pool
    await pool.close()

@pytest.fixture
async def clean_db(db_pool: asyncpg.Pool):
    """Clean the database before each test."""
    async with db_pool.acquire() as conn:
        # Clean up test data
        await conn.execute("DELETE FROM events WHERE order_id LIKE 'test-%'")
        await conn.execute("DELETE FROM payments WHERE order_id LIKE 'test-%'")
        await conn.execute("DELETE FROM orders WHERE id LIKE 'test-%'")
    yield
    # Clean up after test
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM events WHERE order_id LIKE 'test-%'")
        await conn.execute("DELETE FROM payments WHERE order_id LIKE 'test-%'")
        await conn.execute("DELETE FROM orders WHERE id LIKE 'test-%'")

@pytest.fixture
def sample_order() -> Dict[str, Any]:
    """Sample order data for testing."""
    return {
        "order_id": "test-order-123",
        "items": [{"sku": "TEST-SKU", "qty": 2}],
        "customer_id": "test-customer-456"
    }

@pytest.fixture
def sample_address() -> Dict[str, Any]:
    """Sample address data for testing."""
    return {
        "street": "123 Test St",
        "city": "Test City",
        "state": "TS",
        "zip": "12345",
        "country": "US"
    }

@pytest.fixture
def sample_payment_id() -> str:
    """Sample payment ID for testing."""
    return "test-payment-789"

@pytest.fixture
async def worker_environment(temporal_client: Client):
    """Create a worker environment for testing."""
    from app.workflows import OrderWorkflow, ShippingWorkflow
    from app.activities import receive_order, validate_order, charge_payment, prepare_package, dispatch_carrier
    
    async with Worker(
        temporal_client,
        task_queue=TEST_ORDER_TASK_QUEUE,
        workflows=[OrderWorkflow],
        activities=[receive_order, validate_order, charge_payment],
    ), Worker(
        temporal_client,
        task_queue=TEST_SHIPPING_TASK_QUEUE,
        workflows=[ShippingWorkflow],
        activities=[prepare_package, dispatch_carrier],
    ):
        yield

@pytest.fixture
def mock_flaky_call(monkeypatch):
    """Mock the flaky_call function to control test behavior."""
    import app.stubs
    
    def mock_flaky_call_success():
        """Mock flaky_call that always succeeds."""
        pass
    
    def mock_flaky_call_failure():
        """Mock flaky_call that always fails."""
        raise RuntimeError("Mocked failure for testing")
    
    def mock_flaky_call_timeout():
        """Mock flaky_call that times out."""
        import asyncio
        raise asyncio.TimeoutError("Mocked timeout for testing")
    
    # Store original function
    original_flaky_call = app.stubs.flaky_call
    
    def restore_flaky_call():
        app.stubs.flaky_call = original_flaky_call
    
    # Return a context manager for easy use
    class MockFlakyCall:
        def __init__(self, behavior="success"):
            self.behavior = behavior
            self.original = original_flaky_call
        
        def __enter__(self):
            if self.behavior == "success":
                monkeypatch.setattr(app.stubs, "flaky_call", mock_flaky_call_success)
            elif self.behavior == "failure":
                monkeypatch.setattr(app.stubs, "flaky_call", mock_flaky_call_failure)
            elif self.behavior == "timeout":
                monkeypatch.setattr(app.stubs, "flaky_call", mock_flaky_call_timeout)
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            monkeypatch.setattr(app.stubs, "flaky_call", self.original)
    
    return MockFlakyCall

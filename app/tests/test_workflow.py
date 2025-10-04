import asyncio
import pytest
import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.mark.asyncio
async def test_placeholder():
    """Placeholder test to keep CI green; full Temporal tests require the dev server."""
    await asyncio.sleep(0.01)

@pytest.mark.asyncio
async def test_basic_imports():
    """Test that all modules can be imported successfully."""
    try:
        from app import workflows, activities, api, config, db
        assert workflows is not None
        assert activities is not None
        assert api is not None
        assert config is not None
        assert db is not None
    except ImportError as e:
        pytest.fail(f"Failed to import modules: {e}")

@pytest.mark.asyncio
async def test_config_values():
    """Test that configuration values are accessible."""
    from app.config import DATABASE_URL, TEMPORAL_TARGET, ORDER_TASK_QUEUE, SHIPPING_TASK_QUEUE
    
    assert DATABASE_URL is not None
    assert TEMPORAL_TARGET is not None
    assert ORDER_TASK_QUEUE is not None
    assert SHIPPING_TASK_QUEUE is not None
    
    # Verify they are strings
    assert isinstance(DATABASE_URL, str)
    assert isinstance(TEMPORAL_TARGET, str)
    assert isinstance(ORDER_TASK_QUEUE, str)
    assert isinstance(SHIPPING_TASK_QUEUE, str)

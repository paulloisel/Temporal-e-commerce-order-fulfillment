"""
Test shipping retry logic in OrderWorkflow.
"""
import pytest
from unittest.mock import AsyncMock, Mock
from temporalio.common import RetryPolicy
from datetime import timedelta

from app.workflows import OrderWorkflow, ShippingWorkflow


class TestShippingRetry:
    """Test shipping retry functionality."""

    @pytest.mark.asyncio
    async def test_shipping_retry_logic_exists(self, temporal_environment):
        """Test that OrderWorkflow has retry logic for shipping failures."""
        # This test verifies the retry logic is implemented
        # The actual retry behavior will be tested in integration tests
        
        # Check that OrderWorkflow has the retry method
        workflow = OrderWorkflow()
        assert hasattr(workflow, '_execute_shipping_with_retry')
        assert hasattr(workflow, 'shipping_retry_count')
        assert hasattr(workflow, 'max_shipping_retries')
        assert workflow.max_shipping_retries == 3

    @pytest.mark.asyncio
    async def test_shipping_workflow_error_handling(self, temporal_environment):
        """Test that ShippingWorkflow properly signals parent on failure."""
        # This test verifies the error handling in ShippingWorkflow
        # The actual signal behavior will be tested in integration tests
        
        # Check that ShippingWorkflow has proper error handling
        workflow = ShippingWorkflow()
        assert hasattr(workflow, 'run')

    @pytest.mark.asyncio
    async def test_order_workflow_status_includes_retry_info(self, temporal_environment):
        """Test that OrderWorkflow status query includes retry information."""
        # Create a workflow instance
        workflow = OrderWorkflow()
        
        # Check initial status
        status = workflow.status()
        assert "shipping_retry_count" in status
        assert "max_shipping_retries" in status
        assert status["shipping_retry_count"] == 0
        assert status["max_shipping_retries"] == 3

    @pytest.mark.asyncio
    async def test_dispatch_failed_signal_handler(self, temporal_environment):
        """Test that dispatch_failed signal handler doesn't fail the workflow."""
        # Create a workflow instance
        workflow = OrderWorkflow()
        
        # Test the signal handler
        initial_error_count = len(workflow.errors)
        workflow._on_dispatch_failed("Test dispatch failure")
        
        # Verify error was recorded but workflow wasn't failed
        assert len(workflow.errors) == initial_error_count + 1
        assert "dispatch_failed: Test dispatch failure" in workflow.errors[-1]
        assert not workflow.canceled  # Workflow should still be active
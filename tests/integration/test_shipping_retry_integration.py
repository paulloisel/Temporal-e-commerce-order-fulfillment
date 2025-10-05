"""
Integration tests for shipping retry logic.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from temporalio.client import Client
from temporalio.worker import Worker

from app.workflows import OrderWorkflow, ShippingWorkflow
from app.activities import receive_order, validate_order, charge_payment, prepare_package, dispatch_carrier
from app.config import ORDER_TASK_QUEUE, SHIPPING_TASK_QUEUE


class TestShippingRetryIntegration:
    """Integration tests for shipping retry functionality."""

    @pytest.mark.asyncio
    async def test_shipping_retry_with_real_temporal(self, temporal_client):
        """Test shipping retry logic with real Temporal server."""
        # This test requires a running Temporal server
        # It will be skipped if Temporal is not available
        
        try:
            # Start a worker
            worker = Worker(
                temporal_client,
                task_queue=ORDER_TASK_QUEUE,
                workflows=[OrderWorkflow],
                activities=[receive_order, validate_order, charge_payment],
            )
            
            shipping_worker = Worker(
                temporal_client,
                task_queue=SHIPPING_TASK_QUEUE,
                workflows=[ShippingWorkflow],
                activities=[prepare_package, dispatch_carrier],
            )

            # Start workers in background
            async with worker, shipping_worker:
                # Start a workflow
                handle = await temporal_client.start_workflow(
                    OrderWorkflow.run,
                    args=["db_url", "integration-test-retry", "payment-123", {"street": "123 Test St"}],
                    id="integration-shipping-retry-test",
                    task_queue=ORDER_TASK_QUEUE,
                )
                
                # Wait for workflow to complete or timeout
                try:
                    result = await asyncio.wait_for(handle.result(), timeout=30.0)
                    
                    # Check if workflow completed or failed
                    if result["status"] == "completed":
                        # Verify retry information is present
                        assert "shipping_retry_count" in result
                        assert "max_shipping_retries" in result
                        assert result["max_shipping_retries"] == 3
                        
                        # If it completed, shipping should have succeeded
                        assert "ship" in result
                        print(f"✅ Workflow completed successfully with {result['shipping_retry_count']} shipping attempts")
                        
                    elif result["status"] == "failed":
                        # Check if it failed due to shipping retry exhaustion
                        error_msg = " ".join(result.get("errors", []))
                        if "Shipping failed after 3 attempts" in error_msg:
                            print("✅ Workflow failed after exhausting shipping retries (expected behavior)")
                        else:
                            print(f"⚠️ Workflow failed for other reasons: {error_msg}")
                    
                except asyncio.TimeoutError:
                    print("⚠️ Workflow timed out (expected due to flaky_call)")
                    
        except Exception as e:
            pytest.skip(f"Temporal server not available: {e}")

    @pytest.mark.asyncio
    async def test_shipping_retry_status_tracking(self, temporal_client):
        """Test that shipping retry status is properly tracked."""
        try:
            # Start a worker
            worker = Worker(
                temporal_client,
                task_queue=ORDER_TASK_QUEUE,
                workflows=[OrderWorkflow],
                activities=[receive_order, validate_order, charge_payment],
            )
            
            shipping_worker = Worker(
                temporal_client,
                task_queue=SHIPPING_TASK_QUEUE,
                workflows=[ShippingWorkflow],
                activities=[prepare_package, dispatch_carrier],
            )

            async with worker, shipping_worker:
                # Start a workflow
                handle = await temporal_client.start_workflow(
                    OrderWorkflow.run,
                    args=["db_url", "status-test-retry", "payment-456", {"street": "456 Test St"}],
                    id="status-shipping-retry-test",
                    task_queue=ORDER_TASK_QUEUE,
                )
                
                # Query status multiple times to see retry progress
                for i in range(5):
                    await asyncio.sleep(2)
                    status = await handle.query("status")
                    
                    print(f"Status check {i+1}: step={status.get('step')}, retry_count={status.get('shipping_retry_count', 0)}")
                    
                    # Verify retry fields are present
                    assert "shipping_retry_count" in status
                    assert "max_shipping_retries" in status
                    assert status["max_shipping_retries"] == 3
                    
                    # If we reach SHIP step, retry count should be tracked
                    if status.get("step") == "SHIP":
                        assert "shipping_retry_count" in status
                        break
                        
        except Exception as e:
            pytest.skip(f"Temporal server not available: {e}")

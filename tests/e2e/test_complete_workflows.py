"""
End-to-end tests for complete workflow scenarios.
"""
import pytest
import asyncio
from unittest.mock import patch
from temporalio.testing import WorkflowEnvironment
from app.workflows import OrderWorkflow, ShippingWorkflow
from app.config import DATABASE_URL

class TestCompleteWorkflows:
    """Test complete end-to-end workflow scenarios."""
    
    @pytest.mark.asyncio
    async def test_happy_path_complete_order_flow(self, temporal_environment: WorkflowEnvironment, clean_db, db_pool, sample_order, sample_payment_id, sample_address):
        """Test complete happy path order fulfillment."""
        order_id = sample_order["order_id"]
        
        # Mock all external service calls to succeed
        with patch('app.stubs.order_received') as mock_order_received, \
             patch('app.stubs.order_validated') as mock_order_validated, \
             patch('app.stubs.payment_charged') as mock_payment_charged, \
             patch('app.stubs.package_prepared') as mock_prepare, \
             patch('app.stubs.carrier_dispatched') as mock_dispatch:
            
            mock_order_received.return_value = sample_order
            mock_order_validated.return_value = True
            mock_payment_charged.return_value = {"status": "charged", "amount": 100}
            mock_prepare.return_value = "Package prepared successfully"
            mock_dispatch.return_value = "Carrier dispatched successfully"
            
            # Execute complete workflow
            result = await temporal_environment.execute_workflow(
                OrderWorkflow.run,
                DATABASE_URL.replace("+asyncpg", ""),
                order_id,
                sample_payment_id,
                sample_address,
            )
            
            # Verify workflow completed successfully
            assert result["status"] == "completed"
            assert result["order_id"] == order_id
            assert result["step"] == "SHIP"
            assert result["ship"] == "Carrier dispatched successfully"
            assert result["errors"] == []
            
            # Verify database state
            async with db_pool.acquire() as conn:
                # Check order final state
                order_row = await conn.fetchrow("SELECT * FROM orders WHERE id = $1", order_id)
                assert order_row is not None
                assert order_row["state"] == "SHIPPED"
                
                # Check payment was recorded
                payment_row = await conn.fetchrow("SELECT * FROM payments WHERE payment_id = $1", sample_payment_id)
                assert payment_row is not None
                assert payment_row["status"] == "charged"
                assert payment_row["amount"] == 100
                
                # Check all events were logged
                events = await conn.fetch(
                    "SELECT * FROM events WHERE order_id = $1 ORDER BY ts",
                    order_id
                )
                event_types = [event["type"] for event in events]
                assert "order_received" in event_types
                assert "order_validated" in event_types
                assert "payment_charged" in event_types
                assert "package_prepared" in event_types
                assert "carrier_dispatched" in event_types
    
    @pytest.mark.asyncio
    async def test_order_cancellation_flow(self, temporal_environment: WorkflowEnvironment, clean_db, db_pool, sample_order, sample_payment_id, sample_address):
        """Test order cancellation during processing."""
        order_id = sample_order["order_id"]
        
        with patch('app.stubs.order_received') as mock_order_received:
            mock_order_received.return_value = sample_order
            
            # Start workflow
            handle = await temporal_environment.start_workflow(
                OrderWorkflow.run,
                DATABASE_URL.replace("+asyncpg", ""),
                order_id,
                sample_payment_id,
                sample_address,
            )
            
            # Wait a bit for workflow to start
            await asyncio.sleep(0.1)
            
            # Send cancel signal
            await handle.signal("cancel_order")
            
            # Wait for workflow to complete
            result = await handle.result()
            
            # Verify cancellation
            assert result["status"] == "failed"
            assert "Canceled" in result["errors"][0]
            
            # Verify database state
            async with db_pool.acquire() as conn:
                # Check order was created but not completed
                order_row = await conn.fetchrow("SELECT * FROM orders WHERE id = $1", order_id)
                assert order_row is not None
                assert order_row["state"] == "RECEIVED"  # Should be in initial state
                
                # Check no payment was recorded
                payment_row = await conn.fetchrow("SELECT * FROM payments WHERE payment_id = $1", sample_payment_id)
                assert payment_row is None
    
    @pytest.mark.asyncio
    async def test_address_update_flow(self, temporal_environment: WorkflowEnvironment, clean_db, db_pool, sample_order, sample_payment_id, sample_address):
        """Test address update during order processing."""
        order_id = sample_order["order_id"]
        
        with patch('app.stubs.order_received') as mock_order_received, \
             patch('app.stubs.order_validated') as mock_order_validated, \
             patch('app.stubs.payment_charged') as mock_payment_charged, \
             patch('app.stubs.package_prepared') as mock_prepare, \
             patch('app.stubs.carrier_dispatched') as mock_dispatch:
            
            mock_order_received.return_value = sample_order
            mock_order_validated.return_value = True
            mock_payment_charged.return_value = {"status": "charged", "amount": 100}
            mock_prepare.return_value = "Package prepared successfully"
            mock_dispatch.return_value = "Carrier dispatched successfully"
            
            # Start workflow
            handle = await temporal_environment.start_workflow(
                OrderWorkflow.run,
                DATABASE_URL.replace("+asyncpg", ""),
                order_id,
                sample_payment_id,
                sample_address,
            )
            
            # Wait a bit for workflow to start
            await asyncio.sleep(0.1)
            
            # Send address update signal
            new_address = {"street": "789 Updated St", "city": "Updated City", "zip": "54321"}
            await handle.signal("update_address", new_address)
            
            # Wait for workflow to complete
            result = await handle.result()
            
            # Verify completion
            assert result["status"] == "completed"
            assert result["order_id"] == order_id
            assert result["step"] == "SHIP"
    
    @pytest.mark.asyncio
    async def test_payment_failure_retry_flow(self, temporal_environment: WorkflowEnvironment, clean_db, db_pool, sample_order, sample_payment_id, sample_address):
        """Test payment failure and retry scenario."""
        order_id = sample_order["order_id"]
        
        with patch('app.stubs.order_received') as mock_order_received, \
             patch('app.stubs.order_validated') as mock_order_validated, \
             patch('app.stubs.payment_charged') as mock_payment_charged:
            
            mock_order_received.return_value = sample_order
            mock_order_validated.return_value = True
            
            # Mock payment to fail first two times, then succeed
            call_count = 0
            def payment_side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise RuntimeError("Payment service temporarily unavailable")
                return {"status": "charged", "amount": 100}
            
            mock_payment_charged.side_effect = payment_side_effect
            
            # Execute workflow
            result = await temporal_environment.execute_workflow(
                OrderWorkflow.run,
                DATABASE_URL.replace("+asyncpg", ""),
                order_id,
                sample_payment_id,
                sample_address,
            )
            
            # Verify workflow failed due to payment retry exhaustion
            assert result["status"] == "failed"
            assert result["step"] == "PAY"
            assert "Payment service temporarily unavailable" in result["errors"][0]
            
            # Verify payment was attempted multiple times
            assert call_count == 3  # 3 attempts due to retry policy
    
    @pytest.mark.asyncio
    async def test_shipping_failure_flow(self, temporal_environment: WorkflowEnvironment, clean_db, db_pool, sample_order, sample_payment_id, sample_address):
        """Test shipping failure scenario."""
        order_id = sample_order["order_id"]
        
        with patch('app.stubs.order_received') as mock_order_received, \
             patch('app.stubs.order_validated') as mock_order_validated, \
             patch('app.stubs.payment_charged') as mock_payment_charged, \
             patch('app.stubs.package_prepared') as mock_prepare, \
             patch('app.stubs.carrier_dispatched') as mock_dispatch:
            
            mock_order_received.return_value = sample_order
            mock_order_validated.return_value = True
            mock_payment_charged.return_value = {"status": "charged", "amount": 100}
            mock_prepare.return_value = "Package prepared successfully"
            mock_dispatch.side_effect = RuntimeError("Carrier service unavailable")
            
            # Execute workflow
            result = await temporal_environment.execute_workflow(
                OrderWorkflow.run,
                DATABASE_URL.replace("+asyncpg", ""),
                order_id,
                sample_payment_id,
                sample_address,
            )
            
            # Verify workflow failed due to shipping failure
            assert result["status"] == "failed"
            assert result["step"] == "SHIP"
            assert "Carrier service unavailable" in result["errors"][0]
            
            # Verify payment was still processed
            async with db_pool.acquire() as conn:
                payment_row = await conn.fetchrow("SELECT * FROM payments WHERE payment_id = $1", sample_payment_id)
                assert payment_row is not None
                assert payment_row["status"] == "charged"
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_orders_flow(self, temporal_environment: WorkflowEnvironment, clean_db, db_pool, sample_payment_id, sample_address):
        """Test multiple concurrent order processing."""
        order_ids = ["test-order-1", "test-order-2", "test-order-3"]
        sample_orders = [
            {"order_id": order_id, "items": [{"sku": f"SKU-{i}", "qty": 1}]}
            for i, order_id in enumerate(order_ids)
        ]
        
        with patch('app.stubs.order_received') as mock_order_received, \
             patch('app.stubs.order_validated') as mock_order_validated, \
             patch('app.stubs.payment_charged') as mock_payment_charged, \
             patch('app.stubs.package_prepared') as mock_prepare, \
             patch('app.stubs.carrier_dispatched') as mock_dispatch:
            
            def mock_order_received_side_effect(order_id):
                return {"order_id": order_id, "items": [{"sku": "TEST-SKU", "qty": 1}]}
            
            mock_order_received.side_effect = mock_order_received_side_effect
            mock_order_validated.return_value = True
            mock_payment_charged.return_value = {"status": "charged", "amount": 100}
            mock_prepare.return_value = "Package prepared successfully"
            mock_dispatch.return_value = "Carrier dispatched successfully"
            
            # Start multiple workflows concurrently
            tasks = []
            for i, order_id in enumerate(order_ids):
                task = temporal_environment.execute_workflow(
                    OrderWorkflow.run,
                    DATABASE_URL.replace("+asyncpg", ""),
                    order_id,
                    f"{sample_payment_id}-{i}",
                    sample_address,
                )
                tasks.append(task)
            
            # Wait for all workflows to complete
            results = await asyncio.gather(*tasks)
            
            # Verify all workflows completed successfully
            for i, result in enumerate(results):
                assert result["status"] == "completed"
                assert result["order_id"] == order_ids[i]
                assert result["step"] == "SHIP"
                assert result["ship"] == "Carrier dispatched successfully"
            
            # Verify all orders in database
            async with db_pool.acquire() as conn:
                for order_id in order_ids:
                    order_row = await conn.fetchrow("SELECT * FROM orders WHERE id = $1", order_id)
                    assert order_row is not None
                    assert order_row["state"] == "SHIPPED"
    
    @pytest.mark.asyncio
    async def test_workflow_timeout_flow(self, temporal_environment: WorkflowEnvironment, clean_db, db_pool, sample_order, sample_payment_id, sample_address):
        """Test workflow timeout scenario."""
        order_id = sample_order["order_id"]
        
        with patch('app.stubs.order_received') as mock_order_received:
            mock_order_received.return_value = sample_order
            
            # Mock a long-running activity to trigger timeout
            with patch('app.stubs.order_validated') as mock_order_validated:
                mock_order_validated.side_effect = asyncio.TimeoutError("Activity timeout")
                
                # Execute workflow
                result = await temporal_environment.execute_workflow(
                    OrderWorkflow.run,
                    DATABASE_URL.replace("+asyncpg", ""),
                    order_id,
                    sample_payment_id,
                    sample_address,
                )
                
                # Verify workflow failed due to timeout
                assert result["status"] == "failed"
                assert result["step"] == "VALIDATE"
                assert "timeout" in result["errors"][0].lower()
                
                # Verify order was still created
                async with db_pool.acquire() as conn:
                    order_row = await conn.fetchrow("SELECT * FROM orders WHERE id = $1", order_id)
                    assert order_row is not None
                    assert order_row["state"] == "RECEIVED"

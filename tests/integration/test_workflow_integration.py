"""
Integration tests for workflow components.
"""
import pytest
import asyncio
from unittest.mock import patch
from temporalio.testing import WorkflowEnvironment
from app.workflows import OrderWorkflow, ShippingWorkflow
from app.activities import receive_order, validate_order, charge_payment, prepare_package, dispatch_carrier
from app.config import DATABASE_URL

class TestWorkflowIntegration:
    """Test workflow integration with activities and database."""
    
    @pytest.mark.asyncio
    async def test_complete_order_workflow_integration(self, temporal_environment: WorkflowEnvironment, clean_db, sample_order, sample_payment_id, sample_address):
        """Test complete order workflow with real database operations."""
        order_id = sample_order["order_id"]
        
        # Use real activities with mocked external calls
        with patch('app.stubs.order_received') as mock_order_received, \
             patch('app.stubs.order_validated') as mock_order_validated, \
             patch('app.stubs.payment_charged') as mock_payment_charged:
            
            mock_order_received.return_value = sample_order
            mock_order_validated.return_value = True
            mock_payment_charged.return_value = {"status": "charged", "amount": 100}
            
            # Mock child workflow
            with patch('app.workflows.workflow.start_child_workflow') as mock_child:
                mock_child.return_value.result.return_value = "shipped"
                
                result = await temporal_environment.execute_workflow(
                    OrderWorkflow.run,
                    DATABASE_URL.replace("+asyncpg", ""),
                    order_id,
                    sample_payment_id,
                    sample_address,
                )
                
                assert result["status"] == "completed"
                assert result["order_id"] == order_id
                assert result["step"] == "SHIP"
                assert result["ship"] == "shipped"
                assert result["errors"] == []
    
    @pytest.mark.asyncio
    async def test_shipping_workflow_integration(self, temporal_environment: WorkflowEnvironment, clean_db, sample_order):
        """Test shipping workflow with real database operations."""
        order_id = sample_order["order_id"]
        
        # Use real activities with mocked external calls
        with patch('app.stubs.package_prepared') as mock_prepare, \
             patch('app.stubs.carrier_dispatched') as mock_dispatch:
            
            mock_prepare.return_value = "Package prepared successfully"
            mock_dispatch.return_value = "Carrier dispatched successfully"
            
            result = await temporal_environment.execute_workflow(
                ShippingWorkflow.run,
                DATABASE_URL.replace("+asyncpg", ""),
                sample_order,
            )
            
            assert result == "Carrier dispatched successfully"
    
    @pytest.mark.asyncio
    async def test_workflow_with_database_persistence(self, temporal_environment: WorkflowEnvironment, clean_db, db_pool, sample_order, sample_payment_id, sample_address):
        """Test that workflow properly persists data to database."""
        order_id = sample_order["order_id"]
        
        with patch('app.stubs.order_received') as mock_order_received, \
             patch('app.stubs.order_validated') as mock_order_validated, \
             patch('app.stubs.payment_charged') as mock_payment_charged:
            
            mock_order_received.return_value = sample_order
            mock_order_validated.return_value = True
            mock_payment_charged.return_value = {"status": "charged", "amount": 100}
            
            # Mock child workflow
            with patch('app.workflows.workflow.start_child_workflow') as mock_child:
                mock_child.return_value.result.return_value = "shipped"
                
                await temporal_environment.execute_workflow(
                    OrderWorkflow.run,
                    DATABASE_URL.replace("+asyncpg", ""),
                    order_id,
                    sample_payment_id,
                    sample_address,
                )
                
                # Verify database state
                async with db_pool.acquire() as conn:
                    # Check order was created
                    order_row = await conn.fetchrow("SELECT * FROM orders WHERE id = $1", order_id)
                    assert order_row is not None
                    assert order_row["state"] == "SHIPPED"  # Final state after shipping
                    
                    # Check payment was recorded
                    payment_row = await conn.fetchrow("SELECT * FROM payments WHERE payment_id = $1", sample_payment_id)
                    assert payment_row is not None
                    assert payment_row["status"] == "charged"
                    assert payment_row["amount"] == 100
                    
                    # Check events were logged
                    events = await conn.fetch(
                        "SELECT * FROM events WHERE order_id = $1 ORDER BY ts",
                        order_id
                    )
                    assert len(events) >= 3  # At least order_received, order_validated, payment_charged
                    
                    event_types = [event["type"] for event in events]
                    assert "order_received" in event_types
                    assert "order_validated" in event_types
                    assert "payment_charged" in event_types
    
    @pytest.mark.asyncio
    async def test_workflow_error_handling_integration(self, temporal_environment: WorkflowEnvironment, clean_db, sample_order, sample_payment_id, sample_address):
        """Test workflow error handling with real database operations."""
        order_id = sample_order["order_id"]
        
        with patch('app.stubs.order_received') as mock_order_received, \
             patch('app.stubs.order_validated') as mock_order_validated:
            
            mock_order_received.return_value = sample_order
            mock_order_validated.side_effect = ValueError("Validation failed")
            
            result = await temporal_environment.execute_workflow(
                OrderWorkflow.run,
                DATABASE_URL.replace("+asyncpg", ""),
                order_id,
                sample_payment_id,
                sample_address,
            )
            
            assert result["status"] == "failed"
            assert result["step"] == "VALIDATE"
            assert "Validation failed" in result["errors"][0]
    
    @pytest.mark.asyncio
    async def test_workflow_signal_handling_integration(self, temporal_environment: WorkflowEnvironment, clean_db, sample_order, sample_payment_id, sample_address):
        """Test workflow signal handling with real database operations."""
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
            
            # Send cancel signal
            await handle.signal("cancel_order")
            
            # Wait for workflow to complete
            result = await handle.result()
            
            assert result["status"] == "failed"
            assert "Canceled" in result["errors"][0]
    
    @pytest.mark.asyncio
    async def test_concurrent_workflows_integration(self, temporal_environment: WorkflowEnvironment, clean_db, sample_payment_id, sample_address):
        """Test multiple concurrent workflows."""
        order_ids = ["test-order-1", "test-order-2", "test-order-3"]
        sample_orders = [
            {"order_id": order_id, "items": [{"sku": f"SKU-{i}", "qty": 1}]}
            for i, order_id in enumerate(order_ids)
        ]
        
        with patch('app.stubs.order_received') as mock_order_received, \
             patch('app.stubs.order_validated') as mock_order_validated, \
             patch('app.stubs.payment_charged') as mock_payment_charged:
            
            def mock_order_received_side_effect(order_id):
                return {"order_id": order_id, "items": [{"sku": "TEST-SKU", "qty": 1}]}
            
            mock_order_received.side_effect = mock_order_received_side_effect
            mock_order_validated.return_value = True
            mock_payment_charged.return_value = {"status": "charged", "amount": 100}
            
            # Mock child workflow
            with patch('app.workflows.workflow.start_child_workflow') as mock_child:
                mock_child.return_value.result.return_value = "shipped"
                
                # Start multiple workflows concurrently
                tasks = []
                for order_id in order_ids:
                    task = temporal_environment.execute_workflow(
                        OrderWorkflow.run,
                        DATABASE_URL.replace("+asyncpg", ""),
                        order_id,
                        f"{sample_payment_id}-{order_id}",
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
    
    @pytest.mark.asyncio
    async def test_workflow_timeout_integration(self, temporal_environment: WorkflowEnvironment, clean_db, sample_order, sample_payment_id, sample_address):
        """Test workflow timeout with real database operations."""
        order_id = sample_order["order_id"]
        
        with patch('app.stubs.order_received') as mock_order_received:
            mock_order_received.return_value = sample_order
            
            # Mock a long-running activity to trigger timeout
            with patch('app.stubs.order_validated') as mock_order_validated:
                mock_order_validated.side_effect = asyncio.TimeoutError("Activity timeout")
                
                result = await temporal_environment.execute_workflow(
                    OrderWorkflow.run,
                    DATABASE_URL.replace("+asyncpg", ""),
                    order_id,
                    sample_payment_id,
                    sample_address,
                )
                
                assert result["status"] == "failed"
                assert "timeout" in result["errors"][0].lower()

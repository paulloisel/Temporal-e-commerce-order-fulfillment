"""
End-to-end tests for signal handling scenarios.
"""
import pytest
import asyncio
from unittest.mock import patch
from temporalio.testing import WorkflowEnvironment
from app.workflows import OrderWorkflow, ShippingWorkflow
from app.config import DATABASE_URL

class TestSignalHandling:
    """Test signal handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_cancel_signal_during_order_reception(self, temporal_environment: WorkflowEnvironment, clean_db, sample_order, sample_payment_id, sample_address):
        """Test cancel signal during order reception phase."""
        order_id = sample_order["order_id"]
        
        with patch('app.stubs.order_received') as mock_order_received:
            # Make order reception take some time
            async def slow_order_reception(order_id):
                await asyncio.sleep(0.1)
                return sample_order
            
            mock_order_received.side_effect = slow_order_reception
            
            # Start workflow
            handle = await temporal_environment.start_workflow(
                OrderWorkflow.run,
                DATABASE_URL.replace("+asyncpg", ""),
                order_id,
                sample_payment_id,
                sample_address,
            )
            
            # Send cancel signal immediately
            await handle.signal("cancel_order")
            
            # Wait for workflow to complete
            result = await handle.result()
            
            # Verify cancellation
            assert result["status"] == "failed"
            assert "Canceled" in result["errors"][0]
    
    @pytest.mark.asyncio
    async def test_cancel_signal_during_validation(self, temporal_environment: WorkflowEnvironment, clean_db, sample_order, sample_payment_id, sample_address):
        """Test cancel signal during validation phase."""
        order_id = sample_order["order_id"]
        
        with patch('app.stubs.order_received') as mock_order_received, \
             patch('app.stubs.order_validated') as mock_order_validated:
            
            mock_order_received.return_value = sample_order
            
            # Make validation take some time
            async def slow_validation(order):
                await asyncio.sleep(0.1)
                return True
            
            mock_order_validated.side_effect = slow_validation
            
            # Start workflow
            handle = await temporal_environment.start_workflow(
                OrderWorkflow.run,
                DATABASE_URL.replace("+asyncpg", ""),
                order_id,
                sample_payment_id,
                sample_address,
            )
            
            # Wait a bit for workflow to reach validation
            await asyncio.sleep(0.05)
            
            # Send cancel signal
            await handle.signal("cancel_order")
            
            # Wait for workflow to complete
            result = await handle.result()
            
            # Verify cancellation
            assert result["status"] == "failed"
            assert "Canceled" in result["errors"][0]
    
    @pytest.mark.asyncio
    async def test_cancel_signal_during_payment(self, temporal_environment: WorkflowEnvironment, clean_db, sample_order, sample_payment_id, sample_address):
        """Test cancel signal during payment phase."""
        order_id = sample_order["order_id"]
        
        with patch('app.stubs.order_received') as mock_order_received, \
             patch('app.stubs.order_validated') as mock_order_validated, \
             patch('app.stubs.payment_charged') as mock_payment_charged:
            
            mock_order_received.return_value = sample_order
            mock_order_validated.return_value = True
            
            # Make payment take some time
            async def slow_payment(order, payment_id, db):
                await asyncio.sleep(0.1)
                return {"status": "charged", "amount": 100}
            
            mock_payment_charged.side_effect = slow_payment
            
            # Start workflow
            handle = await temporal_environment.start_workflow(
                OrderWorkflow.run,
                DATABASE_URL.replace("+asyncpg", ""),
                order_id,
                sample_payment_id,
                sample_address,
            )
            
            # Wait for workflow to reach payment phase
            await asyncio.sleep(0.2)
            
            # Send cancel signal
            await handle.signal("cancel_order")
            
            # Wait for workflow to complete
            result = await handle.result()
            
            # Verify cancellation
            assert result["status"] == "failed"
            assert "Canceled" in result["errors"][0]
    
    @pytest.mark.asyncio
    async def test_address_update_signal_early(self, temporal_environment: WorkflowEnvironment, clean_db, sample_order, sample_payment_id, sample_address):
        """Test address update signal early in workflow."""
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
            
            # Send address update signal early
            new_address = {"street": "789 Early Update St", "city": "Early City", "zip": "11111"}
            await handle.signal("update_address", new_address)
            
            # Wait for workflow to complete
            result = await handle.result()
            
            # Verify completion (address update should not cause failure)
            assert result["status"] == "completed"
            assert result["order_id"] == order_id
            assert result["step"] == "SHIP"
    
    @pytest.mark.asyncio
    async def test_address_update_signal_during_shipping(self, temporal_environment: WorkflowEnvironment, clean_db, sample_order, sample_payment_id, sample_address):
        """Test address update signal during shipping phase."""
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
            
            # Make dispatch take some time
            async def slow_dispatch(order):
                await asyncio.sleep(0.1)
                return "Carrier dispatched successfully"
            
            mock_dispatch.side_effect = slow_dispatch
            
            # Start workflow
            handle = await temporal_environment.start_workflow(
                OrderWorkflow.run,
                DATABASE_URL.replace("+asyncpg", ""),
                order_id,
                sample_payment_id,
                sample_address,
            )
            
            # Wait for workflow to reach shipping phase
            await asyncio.sleep(0.3)
            
            # Send address update signal during shipping
            new_address = {"street": "999 Late Update St", "city": "Late City", "zip": "99999"}
            await handle.signal("update_address", new_address)
            
            # Wait for workflow to complete
            result = await handle.result()
            
            # Verify completion (address update should not cause failure)
            assert result["status"] == "completed"
            assert result["order_id"] == order_id
            assert result["step"] == "SHIP"
    
    @pytest.mark.asyncio
    async def test_multiple_signals_handling(self, temporal_environment: WorkflowEnvironment, clean_db, sample_order, sample_payment_id, sample_address):
        """Test handling multiple signals."""
        order_id = sample_order["order_id"]
        
        with patch('app.stubs.order_received') as mock_order_received, \
             patch('app.stubs.order_validated') as mock_order_validated:
            
            mock_order_received.return_value = sample_order
            
            # Make validation take some time
            async def slow_validation(order):
                await asyncio.sleep(0.2)
                return True
            
            mock_order_validated.side_effect = slow_validation
            
            # Start workflow
            handle = await temporal_environment.start_workflow(
                OrderWorkflow.run,
                DATABASE_URL.replace("+asyncpg", ""),
                order_id,
                sample_payment_id,
                sample_address,
            )
            
            # Send multiple signals
            await handle.signal("update_address", {"street": "123 First Update"})
            await handle.signal("update_address", {"street": "456 Second Update"})
            await handle.signal("cancel_order")
            
            # Wait for workflow to complete
            result = await handle.result()
            
            # Verify cancellation (cancel should take precedence)
            assert result["status"] == "failed"
            assert "Canceled" in result["errors"][0]
    
    @pytest.mark.asyncio
    async def test_dispatch_failed_signal_from_child(self, temporal_environment: WorkflowEnvironment, clean_db, sample_order, sample_payment_id, sample_address):
        """Test dispatch_failed signal from child workflow."""
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
            
            # Verify workflow failed due to dispatch failure
            assert result["status"] == "failed"
            assert result["step"] == "SHIP"
            assert "Carrier service unavailable" in result["errors"][0]
    
    @pytest.mark.asyncio
    async def test_signal_after_workflow_completion(self, temporal_environment: WorkflowEnvironment, clean_db, sample_order, sample_payment_id, sample_address):
        """Test sending signals after workflow completion."""
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
            
            # Wait for workflow to complete
            result = await handle.result()
            
            # Verify completion
            assert result["status"] == "completed"
            
            # Try to send signals after completion (should not cause errors)
            await handle.signal("cancel_order")
            await handle.signal("update_address", {"street": "Post-completion update"})
            
            # These signals should be ignored since workflow is completed
    
    @pytest.mark.asyncio
    async def test_signal_handling_with_workflow_queries(self, temporal_environment: WorkflowEnvironment, clean_db, sample_order, sample_payment_id, sample_address):
        """Test signal handling combined with workflow queries."""
        order_id = sample_order["order_id"]
        
        with patch('app.stubs.order_received') as mock_order_received, \
             patch('app.stubs.order_validated') as mock_order_validated:
            
            mock_order_received.return_value = sample_order
            
            # Make validation take some time
            async def slow_validation(order):
                await asyncio.sleep(0.2)
                return True
            
            mock_order_validated.side_effect = slow_validation
            
            # Start workflow
            handle = await temporal_environment.start_workflow(
                OrderWorkflow.run,
                DATABASE_URL.replace("+asyncpg", ""),
                order_id,
                sample_payment_id,
                sample_address,
            )
            
            # Query status before signals
            status1 = await handle.query("status")
            assert status1["step"] == "RECEIVE"
            assert status1["canceled"] is False
            
            # Send address update signal
            new_address = {"street": "789 Query Test St", "city": "Query City"}
            await handle.signal("update_address", new_address)
            
            # Query status after address update
            status2 = await handle.query("status")
            assert status2["step"] == "RECEIVE"  # Still in same step
            assert status2["canceled"] is False
            
            # Send cancel signal
            await handle.signal("cancel_order")
            
            # Query status after cancel
            status3 = await handle.query("status")
            assert status3["canceled"] is True
            
            # Wait for workflow to complete
            result = await handle.result()
            
            # Verify cancellation
            assert result["status"] == "failed"
            assert "Canceled" in result["errors"][0]

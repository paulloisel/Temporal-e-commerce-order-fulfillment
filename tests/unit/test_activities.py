"""
Unit tests for Temporal activities.
"""
import pytest
import json
import asyncpg
from unittest.mock import AsyncMock, patch
from app.activities import (
    receive_order, validate_order, charge_payment, 
    prepare_package, dispatch_carrier
)
from app.config import DATABASE_URL

class TestReceiveOrder:
    """Test the ReceiveOrder activity."""
    
    @pytest.mark.asyncio
    async def test_receive_order_success(self, clean_db, sample_order):
        """Test successful order reception."""
        order_id = sample_order["order_id"]
        
        with patch('app.activities.order_received') as mock_order_received:
            mock_order_received.return_value = sample_order
            
            result = await receive_order(DATABASE_URL.replace("+asyncpg", ""), order_id)
            
            assert result == sample_order
            mock_order_received.assert_called_once_with(order_id)
    
    @pytest.mark.asyncio
    async def test_receive_order_database_persistence(self, clean_db, sample_order, db_pool):
        """Test that order is persisted to database."""
        order_id = sample_order["order_id"]
        
        with patch('app.activities.order_received') as mock_order_received:
            mock_order_received.return_value = sample_order
            
            await receive_order(DATABASE_URL.replace("+asyncpg", ""), order_id)
            
            # Verify order was inserted
            async with db_pool.acquire() as conn:
                order_row = await conn.fetchrow("SELECT * FROM orders WHERE id = $1", order_id)
                assert order_row is not None
                assert order_row["state"] == "RECEIVED"
                
                # Verify event was logged
                event_row = await conn.fetchrow(
                    "SELECT * FROM events WHERE order_id = $1 AND type = 'order_received'", 
                    order_id
                )
                assert event_row is not None
                assert json.loads(event_row["payload_json"]) == sample_order
    
    @pytest.mark.asyncio
    async def test_receive_order_idempotency(self, clean_db, sample_order):
        """Test that duplicate order reception is handled gracefully."""
        order_id = sample_order["order_id"]
        
        with patch('app.activities.order_received') as mock_order_received:
            mock_order_received.return_value = sample_order
            
            # Insert order first time
            await receive_order(DATABASE_URL.replace("+asyncpg", ""), order_id)
            
            # Try to insert again (should not fail)
            await receive_order(DATABASE_URL.replace("+asyncpg", ""), order_id)
            
            # Should have been called twice
            assert mock_order_received.call_count == 2

class TestValidateOrder:
    """Test the ValidateOrder activity."""
    
    @pytest.mark.asyncio
    async def test_validate_order_success(self, clean_db, sample_order, db_pool):
        """Test successful order validation."""
        order_id = sample_order["order_id"]
        
        # First create the order
        with patch('app.activities.order_received') as mock_order_received:
            mock_order_received.return_value = sample_order
            await receive_order(DATABASE_URL.replace("+asyncpg", ""), order_id)
        
        with patch('app.activities.order_validated') as mock_order_validated:
            mock_order_validated.return_value = True
            
            result = await validate_order(DATABASE_URL.replace("+asyncpg", ""), sample_order)
            
            assert result is True
            mock_order_validated.assert_called_once_with(sample_order)
            
            # Verify order state was updated
            async with db_pool.acquire() as conn:
                order_row = await conn.fetchrow("SELECT * FROM orders WHERE id = $1", order_id)
                assert order_row["state"] == "VALIDATED"
    
    @pytest.mark.asyncio
    async def test_validate_order_failure(self, clean_db, sample_order):
        """Test order validation failure."""
        with patch('app.activities.order_validated') as mock_order_validated:
            mock_order_validated.side_effect = ValueError("Invalid order")
            
            with pytest.raises(ValueError, match="Invalid order"):
                await validate_order(DATABASE_URL.replace("+asyncpg", ""), sample_order)

class TestChargePayment:
    """Test the ChargePayment activity."""
    
    @pytest.mark.asyncio
    async def test_charge_payment_success(self, clean_db, sample_order, sample_payment_id, db_pool):
        """Test successful payment charging."""
        order_id = sample_order["order_id"]
        
        # First create the order
        with patch('app.activities.order_received') as mock_order_received:
            mock_order_received.return_value = sample_order
            await receive_order(DATABASE_URL.replace("+asyncpg", ""), order_id)
        
        with patch('app.activities.payment_charged') as mock_payment_charged:
            mock_payment_charged.return_value = {"status": "charged", "amount": 100}
            
            result = await charge_payment(DATABASE_URL.replace("+asyncpg", ""), sample_order, sample_payment_id)
            
            assert result["status"] == "charged"
            assert result["amount"] == 100
            assert "idempotent" not in result  # First time, not idempotent
            
            # Verify payment was recorded
            async with db_pool.acquire() as conn:
                payment_row = await conn.fetchrow("SELECT * FROM payments WHERE payment_id = $1", sample_payment_id)
                assert payment_row is not None
                assert payment_row["status"] == "charged"
                assert payment_row["amount"] == 100
    
    @pytest.mark.asyncio
    async def test_charge_payment_idempotency(self, clean_db, sample_order, sample_payment_id):
        """Test payment idempotency."""
        order_id = sample_order["order_id"]
        
        # First create the order
        with patch('app.activities.order_received') as mock_order_received:
            mock_order_received.return_value = sample_order
            await receive_order(DATABASE_URL.replace("+asyncpg", ""), order_id)
        
        with patch('app.activities.payment_charged') as mock_payment_charged:
            mock_payment_charged.return_value = {"status": "charged", "amount": 100}
            
            # Charge payment first time
            result1 = await charge_payment(DATABASE_URL.replace("+asyncpg", ""), sample_order, sample_payment_id)
            
            # Charge payment second time (should be idempotent)
            result2 = await charge_payment(DATABASE_URL.replace("+asyncpg", ""), sample_order, sample_payment_id)
            
            assert result2["idempotent"] is True
            assert result2["status"] == "charged"
            assert result2["amount"] == 100
            
            # Payment function should only be called once
            assert mock_payment_charged.call_count == 1

class TestPreparePackage:
    """Test the PreparePackage activity."""
    
    @pytest.mark.asyncio
    async def test_prepare_package_success(self, clean_db, sample_order, db_pool):
        """Test successful package preparation."""
        order_id = sample_order["order_id"]
        
        with patch('app.activities.package_prepared') as mock_package_prepared:
            mock_package_prepared.return_value = "Package ready for shipping"
            
            result = await prepare_package(DATABASE_URL.replace("+asyncpg", ""), sample_order)
            
            assert result == "Package ready for shipping"
            mock_package_prepared.assert_called_once_with(sample_order)
            
            # Verify event was logged
            async with db_pool.acquire() as conn:
                event_row = await conn.fetchrow(
                    "SELECT * FROM events WHERE order_id = $1 AND type = 'package_prepared'", 
                    order_id
                )
                assert event_row is not None
                assert json.loads(event_row["payload_json"])["result"] == "Package ready for shipping"

class TestDispatchCarrier:
    """Test the DispatchCarrier activity."""
    
    @pytest.mark.asyncio
    async def test_dispatch_carrier_success(self, clean_db, sample_order, db_pool):
        """Test successful carrier dispatch."""
        order_id = sample_order["order_id"]
        
        # First create the order
        with patch('app.activities.order_received') as mock_order_received:
            mock_order_received.return_value = sample_order
            await receive_order(DATABASE_URL.replace("+asyncpg", ""), order_id)
        
        with patch('app.activities.carrier_dispatched') as mock_carrier_dispatched:
            mock_carrier_dispatched.return_value = "Carrier dispatched successfully"
            
            result = await dispatch_carrier(DATABASE_URL.replace("+asyncpg", ""), sample_order)
            
            assert result == "Carrier dispatched successfully"
            mock_carrier_dispatched.assert_called_once_with(sample_order)
            
            # Verify order state was updated
            async with db_pool.acquire() as conn:
                order_row = await conn.fetchrow("SELECT * FROM orders WHERE id = $1", order_id)
                assert order_row["state"] == "SHIPPED"
                
                # Verify event was logged
                event_row = await conn.fetchrow(
                    "SELECT * FROM events WHERE order_id = $1 AND type = 'carrier_dispatched'", 
                    order_id
                )
                assert event_row is not None

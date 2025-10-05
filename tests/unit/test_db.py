"""
Unit tests for database operations.
"""
import pytest
import asyncpg
import json
from app.db import get_pool, apply_migrations, init
from app.config import DATABASE_URL

class TestDatabaseOperations:
    """Test database operations."""
    
    @pytest.mark.asyncio
    async def test_get_pool(self):
        """Test database pool creation."""
        pool = await get_pool()
        assert isinstance(pool, asyncpg.Pool)
        await pool.close()
    
    @pytest.mark.asyncio
    async def test_apply_migrations(self, db_pool):
        """Test database migrations."""
        # This test verifies that migrations can be applied
        # In a real test environment, you'd use a separate test database
        await apply_migrations(db_pool)
        
        # Verify tables exist
        async with db_pool.acquire() as conn:
            # Check orders table
            result = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'orders'
                )
            """)
            assert result is True
            
            # Check payments table
            result = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'payments'
                )
            """)
            assert result is True
            
            # Check events table
            result = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'events'
                )
            """)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_database_connection(self, db_pool):
        """Test basic database connectivity."""
        async with db_pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            assert result == 1
    
    @pytest.mark.asyncio
    async def test_order_crud_operations(self, clean_db, db_pool, sample_order):
        """Test CRUD operations on orders table."""
        order_id = sample_order["order_id"]
        
        async with db_pool.acquire() as conn:
            # Create order
            await conn.execute(
                "INSERT INTO orders(id, state, address_json) VALUES($1, $2, $3)",
                order_id, "RECEIVED", '{"street": "123 Test St"}'
            )
            
            # Read order
            order_row = await conn.fetchrow("SELECT * FROM orders WHERE id = $1", order_id)
            assert order_row is not None
            assert order_row["id"] == order_id
            assert order_row["state"] == "RECEIVED"
            
            # Update order
            await conn.execute(
                "UPDATE orders SET state = $1 WHERE id = $2",
                "VALIDATED", order_id
            )
            
            # Verify update
            order_row = await conn.fetchrow("SELECT * FROM orders WHERE id = $1", order_id)
            assert order_row["state"] == "VALIDATED"
            
            # Delete order
            await conn.execute("DELETE FROM orders WHERE id = $1", order_id)
            
            # Verify deletion
            order_row = await conn.fetchrow("SELECT * FROM orders WHERE id = $1", order_id)
            assert order_row is None
    
    @pytest.mark.asyncio
    async def test_payment_crud_operations(self, clean_db, db_pool, sample_order, sample_payment_id):
        """Test CRUD operations on payments table."""
        order_id = sample_order["order_id"]
        
        async with db_pool.acquire() as conn:
            # Create order first (foreign key constraint)
            await conn.execute(
                "INSERT INTO orders(id, state, address_json) VALUES($1, $2, $3)",
                order_id, "RECEIVED", '{}'
            )
            
            # Create payment
            await conn.execute(
                "INSERT INTO payments(payment_id, order_id, status, amount) VALUES($1, $2, $3, $4)",
                sample_payment_id, order_id, "charged", 100
            )
            
            # Read payment
            payment_row = await conn.fetchrow("SELECT * FROM payments WHERE payment_id = $1", sample_payment_id)
            assert payment_row is not None
            assert payment_row["payment_id"] == sample_payment_id
            assert payment_row["order_id"] == order_id
            assert payment_row["status"] == "charged"
            assert payment_row["amount"] == 100
            
            # Update payment
            await conn.execute(
                "UPDATE payments SET status = $1 WHERE payment_id = $2",
                "refunded", sample_payment_id
            )
            
            # Verify update
            payment_row = await conn.fetchrow("SELECT * FROM payments WHERE payment_id = $1", sample_payment_id)
            assert payment_row["status"] == "refunded"
    
    @pytest.mark.asyncio
    async def test_events_crud_operations(self, clean_db, db_pool, sample_order):
        """Test CRUD operations on events table."""
        order_id = sample_order["order_id"]
        
        async with db_pool.acquire() as conn:
            # Create event
            await conn.execute(
                "INSERT INTO events(order_id, type, payload_json) VALUES($1, $2, $3)",
                order_id, "test_event", '{"test": "data"}'
            )
            
            # Read event
            event_row = await conn.fetchrow(
                "SELECT * FROM events WHERE order_id = $1 AND type = $2",
                order_id, "test_event"
            )
            assert event_row is not None
            assert event_row["order_id"] == order_id
            assert event_row["type"] == "test_event"
            assert event_row["payload_json"] == '{"test": "data"}'
            
            # Read multiple events
            events = await conn.fetch(
                "SELECT * FROM events WHERE order_id = $1 ORDER BY ts",
                order_id
            )
            assert len(events) == 1
    
    @pytest.mark.asyncio
    async def test_foreign_key_constraints(self, clean_db, db_pool, sample_payment_id):
        """Test foreign key constraints."""
        async with db_pool.acquire() as conn:
            # Try to create payment without existing order (should fail)
            with pytest.raises(asyncpg.ForeignKeyViolationError):
                await conn.execute(
                    "INSERT INTO payments(payment_id, order_id, status, amount) VALUES($1, $2, $3, $4)",
                    sample_payment_id, "non-existent-order", "charged", 100
                )
    
    @pytest.mark.asyncio
    async def test_jsonb_operations(self, clean_db, db_pool, sample_order):
        """Test JSONB operations."""
        order_id = sample_order["order_id"]
        address_data = {"street": "123 Test St", "city": "Test City", "zip": "12345"}
        
        async with db_pool.acquire() as conn:
            # Insert JSONB data
            await conn.execute(
                "INSERT INTO orders(id, state, address_json) VALUES($1, $2, $3)",
                order_id, "RECEIVED", json.dumps(address_data)
            )
            
            # Query JSONB data
            order_row = await conn.fetchrow("SELECT * FROM orders WHERE id = $1", order_id)
            assert json.loads(order_row["address_json"]) == address_data
            
            # Query specific JSONB fields
            street = await conn.fetchval(
                "SELECT address_json->>'street' FROM orders WHERE id = $1",
                order_id
            )
            assert street == "123 Test St"
            
            # Update JSONB data
            new_address = {"street": "456 New St", "city": "New City", "zip": "67890"}
            await conn.execute(
                "UPDATE orders SET address_json = $1 WHERE id = $2",
                json.dumps(new_address), order_id
            )
            
            # Verify update
            order_row = await conn.fetchrow("SELECT * FROM orders WHERE id = $1", order_id)
            assert json.loads(order_row["address_json"]) == new_address
    
    @pytest.mark.asyncio
    async def test_timestamp_operations(self, clean_db, db_pool, sample_order):
        """Test timestamp operations."""
        order_id = sample_order["order_id"]
        
        async with db_pool.acquire() as conn:
            # Insert order
            await conn.execute(
                "INSERT INTO orders(id, state, address_json) VALUES($1, $2, $3)",
                order_id, "RECEIVED", '{}'
            )
            
            # Check timestamps
            order_row = await conn.fetchrow("SELECT * FROM orders WHERE id = $1", order_id)
            assert order_row["created_at"] is not None
            assert order_row["updated_at"] is not None
            assert order_row["created_at"] == order_row["updated_at"]
            
            # Update order and check updated_at
            import asyncio
            await asyncio.sleep(0.1)  # Longer delay to ensure timestamp difference
            await conn.execute(
                "UPDATE orders SET state = $1, updated_at = now() WHERE id = $2",
                "VALIDATED", order_id
            )
            
            updated_order = await conn.fetchrow("SELECT * FROM orders WHERE id = $1", order_id)
            assert updated_order["updated_at"] > updated_order["created_at"]

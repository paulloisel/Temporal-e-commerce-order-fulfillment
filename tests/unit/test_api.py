"""
Unit tests for FastAPI endpoints.
"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.api import app
from app.config import DATABASE_URL

class TestAPIEndpoints:
    """Test FastAPI endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_temporal_client(self):
        """Mock Temporal client."""
        with patch('app.api.Client.connect') as mock_connect:
            mock_client = AsyncMock()
            mock_connect.return_value = mock_client
            yield mock_client
    
    def test_start_order_workflow(self, client, mock_temporal_client, sample_order, sample_payment_id, sample_address):
        """Test starting an order workflow."""
        # Mock workflow handle
        mock_handle = AsyncMock()
        mock_handle.id = f"order-{sample_order['order_id']}"
        mock_handle.first_execution_run_id = "run-123"
        mock_temporal_client.start_workflow.return_value = mock_handle
        
        response = client.post(
            f"/orders/{sample_order['order_id']}/start",
            json={
                "payment_id": sample_payment_id,
                "address": sample_address
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"] == f"order-{sample_order['order_id']}"
        assert data["run_id"] == "run-123"
        
        # Verify workflow was started with correct parameters
        mock_temporal_client.start_workflow.assert_called_once()
        call_args = mock_temporal_client.start_workflow.call_args
        assert call_args[0][1] == DATABASE_URL.replace("+asyncpg", "")  # db_url
        assert call_args[0][2] == sample_order["order_id"]  # order_id
        assert call_args[0][3] == sample_payment_id  # payment_id
        assert call_args[0][4] == sample_address  # address
    
    def test_start_order_workflow_without_address(self, client, mock_temporal_client, sample_order, sample_payment_id):
        """Test starting an order workflow without address."""
        # Mock workflow handle
        mock_handle = AsyncMock()
        mock_handle.id = f"order-{sample_order['order_id']}"
        mock_handle.first_execution_run_id = "run-123"
        mock_temporal_client.start_workflow.return_value = mock_handle
        
        response = client.post(
            f"/orders/{sample_order['order_id']}/start",
            json={"payment_id": sample_payment_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"] == f"order-{sample_order['order_id']}"
        
        # Verify workflow was started with empty address
        call_args = mock_temporal_client.start_workflow.call_args
        assert call_args[0][4] == {}  # empty address
    
    def test_cancel_order(self, client, mock_temporal_client, sample_order):
        """Test canceling an order."""
        # Mock workflow handle
        mock_handle = AsyncMock()
        mock_temporal_client.get_workflow_handle.return_value = mock_handle
        
        response = client.post(f"/orders/{sample_order['order_id']}/signals/cancel")
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        
        # Verify signal was sent
        mock_temporal_client.get_workflow_handle.assert_called_once_with(f"order-{sample_order['order_id']}")
        mock_handle.signal.assert_called_once_with("cancel_order")
    
    def test_update_address(self, client, mock_temporal_client, sample_order, sample_address):
        """Test updating order address."""
        # Mock workflow handle
        mock_handle = AsyncMock()
        mock_temporal_client.get_workflow_handle.return_value = mock_handle
        
        new_address = {"street": "789 Updated St", "city": "Updated City"}
        
        response = client.post(
            f"/orders/{sample_order['order_id']}/signals/update-address",
            json={"address": new_address}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        
        # Verify signal was sent with correct address
        mock_temporal_client.get_workflow_handle.assert_called_once_with(f"order-{sample_order['order_id']}")
        mock_handle.signal.assert_called_once_with("update_address", new_address)
    
    def test_get_order_status(self, client, mock_temporal_client, sample_order):
        """Test getting order status."""
        # Mock workflow handle and status
        mock_handle = AsyncMock()
        mock_status = {
            "order": sample_order,
            "step": "PAY",
            "errors": [],
            "canceled": False
        }
        mock_handle.query.return_value = mock_status
        mock_temporal_client.get_workflow_handle.return_value = mock_handle
        
        response = client.get(f"/orders/{sample_order['order_id']}/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data == mock_status
        
        # Verify query was made
        mock_temporal_client.get_workflow_handle.assert_called_once_with(f"order-{sample_order['order_id']}")
        mock_handle.query.assert_called_once_with("status")
    
    def test_get_order_status_not_found(self, client, mock_temporal_client, sample_order):
        """Test getting status for non-existent order."""
        # Mock workflow handle that raises exception
        mock_handle = AsyncMock()
        mock_handle.query.side_effect = Exception("Workflow not found")
        mock_temporal_client.get_workflow_handle.return_value = mock_handle
        
        response = client.get(f"/orders/{sample_order['order_id']}/status")
        
        assert response.status_code == 404
        data = response.json()
        assert "Workflow not found" in data["detail"]
    
    def test_invalid_json_payload(self, client, sample_order):
        """Test API with invalid JSON payload."""
        response = client.post(
            f"/orders/{sample_order['order_id']}/start",
            json={"invalid": "payload"}
        )
        
        # Should return 422 for validation error
        assert response.status_code == 422
    
    def test_missing_payment_id(self, client, sample_order):
        """Test API with missing required payment_id."""
        response = client.post(
            f"/orders/{sample_order['order_id']}/start",
            json={"address": {"street": "123 Test St"}}
        )
        
        # Should return 422 for validation error
        assert response.status_code == 422
    
    def test_api_documentation(self, client):
        """Test that API documentation is accessible."""
        response = client.get("/docs")
        assert response.status_code == 200
        
        response = client.get("/openapi.json")
        assert response.status_code == 200

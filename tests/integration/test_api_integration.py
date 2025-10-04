"""
Integration tests for API endpoints with Temporal workflows.
"""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, Mock
from fastapi.testclient import TestClient
from app.api import app
from app.config import DATABASE_URL

class TestAPIIntegration:
    """Test API integration with Temporal workflows."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    @pytest.fixture
    def client_with_mock(self, mock_temporal_client):
        """Create a test client with mocked Temporal client."""
        client = TestClient(app)
        # Manually set the client in app state since on_event("startup") doesn't run in tests
        client.app.state.client = mock_temporal_client
        return client
    
    @pytest.fixture
    def mock_temporal_client(self):
        """Mock Temporal client for integration tests."""
        with patch('app.api.Client.connect') as mock_connect:
            mock_client = AsyncMock()
            mock_connect.return_value = mock_client
            yield mock_client
    
    def test_complete_order_flow_api_integration(self, client_with_mock, mock_temporal_client, sample_order, sample_payment_id, sample_address):
        """Test complete order flow through API."""
        # Mock workflow handle
        mock_handle = AsyncMock()
        mock_handle.id = f"order-{sample_order['order_id']}"
        mock_handle.first_execution_run_id = "run-123"
        mock_temporal_client.start_workflow.return_value = mock_handle
        
        # Start order workflow
        start_response = client_with_mock.post(
            f"/orders/{sample_order['order_id']}/start",
            json={
                "payment_id": sample_payment_id,
                "address": sample_address
            }
        )
        
        assert start_response.status_code == 200
        start_data = start_response.json()
        assert start_data["workflow_id"] == f"order-{sample_order['order_id']}"
        assert start_data["run_id"] == "run-123"
        
        # Verify workflow was started
        mock_temporal_client.start_workflow.assert_called_once()
        call_args = mock_temporal_client.start_workflow.call_args
        assert call_args[0][2] == sample_order["order_id"]  # order_id
        assert call_args[0][3] == sample_payment_id  # payment_id
        assert call_args[0][4] == sample_address  # address
    
    def test_order_cancellation_flow_api_integration(self, client_with_mock, mock_temporal_client, sample_order):
        """Test order cancellation flow through API."""
        # Mock workflow handle
        mock_handle = AsyncMock()
        mock_get_handle = Mock(return_value=mock_handle)
        mock_temporal_client.get_workflow_handle = mock_get_handle
        
        # Cancel order
        cancel_response = client_with_mock.post(f"/orders/{sample_order['order_id']}/signals/cancel")
        
        assert cancel_response.status_code == 200
        cancel_data = cancel_response.json()
        assert cancel_data["ok"] is True
        
        # Verify cancel signal was sent
        mock_get_handle.assert_called_once_with(f"order-{sample_order['order_id']}")
        mock_handle.signal.assert_called_once_with("cancel_order")
    
    def test_address_update_flow_api_integration(self, client_with_mock, mock_temporal_client, sample_order, sample_address):
        """Test address update flow through API."""
        # Mock workflow handle
        mock_handle = AsyncMock()
        mock_get_handle = Mock(return_value=mock_handle)
        mock_temporal_client.get_workflow_handle = mock_get_handle
        
        # Update address
        new_address = {"street": "789 Updated St", "city": "Updated City", "zip": "54321"}
        update_response = client_with_mock.post(
            f"/orders/{sample_order['order_id']}/signals/update-address",
            json={"address": new_address}
        )
        
        assert update_response.status_code == 200
        update_data = update_response.json()
        assert update_data["ok"] is True
        
        # Verify update signal was sent
        mock_get_handle.assert_called_once_with(f"order-{sample_order['order_id']}")
        mock_handle.signal.assert_called_once_with("update_address", new_address)
    
    def test_order_status_query_api_integration(self, client_with_mock, mock_temporal_client, sample_order):
        """Test order status query through API."""
        # Mock workflow handle and status
        mock_handle = AsyncMock()
        mock_status = {
            "order": sample_order,
            "step": "PAY",
            "errors": [],
            "canceled": False
        }
        mock_handle.query.return_value = mock_status
        mock_get_handle = Mock(return_value=mock_handle)
        mock_temporal_client.get_workflow_handle = mock_get_handle
        
        # Query status
        status_response = client_with_mock.get(f"/orders/{sample_order['order_id']}/status")
        
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data == mock_status
        
        # Verify query was made
        mock_get_handle.assert_called_once_with(f"order-{sample_order['order_id']}")
        mock_handle.query.assert_called_once_with("status")
    
    def test_api_error_handling_integration(self, client_with_mock, mock_temporal_client, sample_order):
        """Test API error handling."""
        # Mock workflow handle that raises exception
        mock_handle = AsyncMock()
        mock_handle.query.side_effect = Exception("Workflow not found")
        mock_get_handle = Mock(return_value=mock_handle)
        mock_temporal_client.get_workflow_handle = mock_get_handle
        
        # Query status for non-existent order
        status_response = client_with_mock.get(f"/orders/{sample_order['order_id']}/status")
        
        assert status_response.status_code == 404
        status_data = status_response.json()
        assert "Workflow not found" in status_data["detail"]
    
    def test_api_validation_integration(self, client_with_mock, sample_order):
        """Test API input validation."""
        # Test missing payment_id
        response = client_with_mock.post(
            f"/orders/{sample_order['order_id']}/start",
            json={"address": {"street": "123 Test St"}}
        )
        assert response.status_code == 422
        
        # Test invalid JSON
        response = client_with_mock.post(
            f"/orders/{sample_order['order_id']}/start",
            json={"invalid": "payload"}
        )
        assert response.status_code == 422
        
        # Test missing address in update
        response = client_with_mock.post(
            f"/orders/{sample_order['order_id']}/signals/update-address",
            json={"invalid": "payload"}
        )
        assert response.status_code == 422
    
    def test_api_documentation_integration(self, client):
        """Test API documentation endpoints."""
        # Test OpenAPI JSON
        response = client.get("/openapi.json")
        assert response.status_code == 200
        openapi_data = response.json()
        assert "openapi" in openapi_data
        assert "info" in openapi_data
        assert "paths" in openapi_data
        
        # Verify expected endpoints exist
        paths = openapi_data["paths"]
        assert "/orders/{order_id}/start" in paths
        assert "/orders/{order_id}/signals/cancel" in paths
        assert "/orders/{order_id}/signals/update-address" in paths
        assert "/orders/{order_id}/status" in paths
        
        # Test Swagger UI
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_concurrent_api_requests_integration(self, client_with_mock, mock_temporal_client, sample_payment_id, sample_address):
        """Test concurrent API requests."""
        order_ids = ["test-order-1", "test-order-2", "test-order-3"]
        
        # Mock workflow handles
        mock_handles = []
        for order_id in order_ids:
            mock_handle = AsyncMock()
            mock_handle.id = f"order-{order_id}"
            mock_handle.first_execution_run_id = f"run-{order_id}"
            mock_handles.append(mock_handle)
        
        mock_temporal_client.start_workflow.side_effect = mock_handles
        
        # Make concurrent requests
        responses = []
        for order_id in order_ids:
            response = client_with_mock.post(
                f"/orders/{order_id}/start",
                json={
                    "payment_id": f"{sample_payment_id}-{order_id}",
                    "address": sample_address
                }
            )
            responses.append(response)
        
        # Verify all requests succeeded
        for i, response in enumerate(responses):
            assert response.status_code == 200
            data = response.json()
            assert data["workflow_id"] == f"order-{order_ids[i]}"
            assert data["run_id"] == f"run-{order_ids[i]}"
        
        # Verify all workflows were started
        assert mock_temporal_client.start_workflow.call_count == len(order_ids)
    
    def test_api_workflow_lifecycle_integration(self, client_with_mock, mock_temporal_client, sample_order, sample_payment_id, sample_address):
        """Test complete workflow lifecycle through API."""
        # Mock workflow handle
        mock_handle = AsyncMock()
        mock_handle.id = f"order-{sample_order['order_id']}"
        mock_handle.first_execution_run_id = "run-123"
        mock_temporal_client.start_workflow.return_value = mock_handle
        mock_get_handle = Mock(return_value=mock_handle)
        mock_temporal_client.get_workflow_handle = mock_get_handle
        
        # 1. Start workflow
        start_response = client_with_mock.post(
            f"/orders/{sample_order['order_id']}/start",
            json={
                "payment_id": sample_payment_id,
                "address": sample_address
            }
        )
        assert start_response.status_code == 200
        
        # 2. Query initial status
        mock_handle.query.return_value = {
            "order": sample_order,
            "step": "RECEIVE",
            "errors": [],
            "canceled": False
        }
        status_response = client_with_mock.get(f"/orders/{sample_order['order_id']}/status")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["step"] == "RECEIVE"
        
        # 3. Update address
        new_address = {"street": "456 Updated St", "city": "Updated City"}
        update_response = client_with_mock.post(
            f"/orders/{sample_order['order_id']}/signals/update-address",
            json={"address": new_address}
        )
        assert update_response.status_code == 200
        
        # 4. Cancel order
        cancel_response = client_with_mock.post(f"/orders/{sample_order['order_id']}/signals/cancel")
        assert cancel_response.status_code == 200
        
        # 5. Query final status
        mock_handle.query.return_value = {
            "order": sample_order,
            "step": "CANCELED",
            "errors": ["Canceled"],
            "canceled": True
        }
        final_status_response = client_with_mock.get(f"/orders/{sample_order['order_id']}/status")
        assert final_status_response.status_code == 200
        final_status_data = final_status_response.json()
        assert final_status_data["canceled"] is True

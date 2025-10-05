# API Reference

## Overview

The Temporal E-commerce Order Fulfillment system provides a REST API for managing order workflows. All endpoints return JSON responses.

**Base URL**: `http://localhost:8000`

## Authentication

Currently no authentication is required. In production, implement proper API key or JWT authentication.

## Endpoints

### Start Workflow

Start a new order workflow.

**Endpoint**: `POST /orders/{order_id}/start`

**Parameters**:
- `order_id` (path): Unique identifier for the order

**Request Body**:
```json
{
  "payment_id": "string",
  "address": {
    "street": "string",
    "city": "string", 
    "state": "string",
    "zip": "string",
    "country": "string"
  }
}
```

**Response**:
```json
{
  "workflow_id": "string",
  "run_id": "string"
}
```

**Example**:
```bash
curl -X POST "http://localhost:8000/orders/order-123/start" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_id": "pmt-123",
    "address": {
      "street": "123 Main St",
      "city": "Test City",
      "state": "TS",
      "zip": "12345",
      "country": "US"
    }
  }'
```

### Get Workflow Status

Get the current status of a workflow.

**Endpoint**: `GET /orders/{order_id}/status`

**Parameters**:
- `order_id` (path): Order identifier

**Response**:
```json
{
  "order": {
    "order_id": "string",
    "items": [
      {
        "sku": "string",
        "qty": "number"
      }
    ]
  },
  "step": "string",
  "errors": ["string"],
  "canceled": "boolean"
}
```

**Possible Steps**:
- `INIT`: Initial state
- `RECEIVE`: Receiving order
- `VALIDATE`: Validating order
- `MANUAL_REVIEW`: Manual review in progress
- `PAY`: Processing payment
- `SHIP`: Shipping workflow

**Example**:
```bash
curl "http://localhost:8000/orders/order-123/status"
```

### Cancel Workflow

Cancel a running workflow.

**Endpoint**: `POST /orders/{order_id}/signals/cancel`

**Parameters**:
- `order_id` (path): Order identifier

**Response**:
```json
{
  "ok": true
}
```

**Example**:
```bash
curl -X POST "http://localhost:8000/orders/order-123/signals/cancel"
```

### Update Address

Update the shipping address for a workflow.

**Endpoint**: `POST /orders/{order_id}/signals/update-address`

**Parameters**:
- `order_id` (path): Order identifier

**Request Body**:
```json
{
  "address": {
    "street": "string",
    "city": "string",
    "state": "string", 
    "zip": "string",
    "country": "string"
  }
}
```

**Response**:
```json
{
  "ok": true
}
```

**Example**:
```bash
curl -X POST "http://localhost:8000/orders/order-123/signals/update-address" \
  -H "Content-Type: application/json" \
  -d '{
    "address": {
      "street": "456 New St",
      "city": "New City",
      "state": "NS",
      "zip": "54321",
      "country": "US"
    }
  }'
```

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "detail": "Error message"
}
```

**Common HTTP Status Codes**:
- `200`: Success
- `404`: Workflow not found
- `422`: Validation error
- `500`: Internal server error

## Workflow Lifecycle

### Normal Flow
1. **Start**: POST `/orders/{order_id}/start`
2. **Monitor**: GET `/orders/{order_id}/status` (polling)
3. **Complete**: Workflow finishes automatically

### With Signals
1. **Start**: POST `/orders/{order_id}/start`
2. **Update**: POST `/orders/{order_id}/signals/update-address`
3. **Cancel**: POST `/orders/{order_id}/signals/cancel`
4. **Monitor**: GET `/orders/{order_id}/status`

## Rate Limiting

Currently no rate limiting is implemented. In production, implement appropriate rate limiting based on your requirements.

## Webhooks

Webhooks are not currently implemented. Consider adding webhook notifications for workflow completion events in production.

## SDK Examples

### Python
```python
import aiohttp
import asyncio

async def start_workflow(order_id, payment_id, address):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"http://localhost:8000/orders/{order_id}/start",
            json={
                "payment_id": payment_id,
                "address": address
            }
        ) as response:
            return await response.json()

async def get_status(order_id):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"http://localhost:8000/orders/{order_id}/status"
        ) as response:
            return await response.json()

# Usage
order_id = "order-123"
payment_id = "pmt-123"
address = {
    "street": "123 Main St",
    "city": "Test City",
    "state": "TS",
    "zip": "12345",
    "country": "US"
}

# Start workflow
result = await start_workflow(order_id, payment_id, address)
print(f"Started: {result}")

# Monitor status
status = await get_status(order_id)
print(f"Status: {status}")
```

### JavaScript/Node.js
```javascript
const axios = require('axios');

async function startWorkflow(orderId, paymentId, address) {
    const response = await axios.post(
        `http://localhost:8000/orders/${orderId}/start`,
        {
            payment_id: paymentId,
            address: address
        }
    );
    return response.data;
}

async function getStatus(orderId) {
    const response = await axios.get(
        `http://localhost:8000/orders/${orderId}/status`
    );
    return response.data;
}

// Usage
const orderId = "order-123";
const paymentId = "pmt-123";
const address = {
    street: "123 Main St",
    city: "Test City",
    state: "TS",
    zip: "12345",
    country: "US"
};

// Start workflow
startWorkflow(orderId, paymentId, address)
    .then(result => console.log("Started:", result))
    .catch(error => console.error("Error:", error));

// Get status
getStatus(orderId)
    .then(status => console.log("Status:", status))
    .catch(error => console.error("Error:", error));
```

### cURL Examples

```bash
# Start workflow
curl -X POST "http://localhost:8000/orders/order-123/start" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_id": "pmt-123",
    "address": {
      "street": "123 Main St",
      "city": "Test City",
      "state": "TS",
      "zip": "12345",
      "country": "US"
    }
  }'

# Get status
curl "http://localhost:8000/orders/order-123/status"

# Cancel workflow
curl -X POST "http://localhost:8000/orders/order-123/signals/cancel"

# Update address
curl -X POST "http://localhost:8000/orders/order-123/signals/update-address" \
  -H "Content-Type: application/json" \
  -d '{
    "address": {
      "street": "456 New St",
      "city": "New City",
      "state": "NS",
      "zip": "54321",
      "country": "US"
    }
  }'
```

## Testing

Use the interactive API documentation at http://localhost:8000/docs to test endpoints directly in your browser.

## Production Considerations

### Security
- Implement authentication (API keys, JWT, OAuth)
- Use HTTPS/TLS encryption
- Validate and sanitize all inputs
- Implement rate limiting
- Add request logging and monitoring

### Performance
- Implement connection pooling
- Add caching where appropriate
- Monitor response times
- Scale horizontally as needed

### Reliability
- Implement circuit breakers
- Add retry logic for external calls
- Monitor error rates
- Implement health checks

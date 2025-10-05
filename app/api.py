from __future__ import annotations
import os
from typing import Optional, Dict, Any
from datetime import timedelta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from temporalio.client import Client
from .config import TEMPORAL_TARGET, ORDER_TASK_QUEUE, SHIPPING_TASK_QUEUE, DATABASE_URL
from .workflows import OrderWorkflow

app = FastAPI(title="Temporal Take-Home API")

class StartBody(BaseModel):
    payment_id: str
    address: Optional[Dict[str, Any]] = None

@app.on_event("startup")
async def _connect():
    app.state.client = await Client.connect(TEMPORAL_TARGET)

@app.post("/orders/{order_id}/start")
async def start(order_id: str, body: StartBody):
    client: Client = app.state.client
    handle = await client.start_workflow(
        OrderWorkflow.run,
        args=[
            DATABASE_URL.replace("+asyncpg", ""),  # pass raw URL for asyncpg
            order_id,
            body.payment_id,
            body.address or {},
        ],
        id=f"order-{order_id}",
        task_queue=ORDER_TASK_QUEUE,
        run_timeout=timedelta(seconds=60),  # Extended timeout for manual approval
    )
    return {"workflow_id": handle.id, "run_id": handle.first_execution_run_id}

@app.post("/orders/{order_id}/signals/cancel")
async def cancel(order_id: str):
    client: Client = app.state.client
    handle = client.get_workflow_handle(f"order-{order_id}")
    await handle.signal("cancel_order")
    return {"ok": True}

class UpdateAddressBody(BaseModel):
    address: Dict[str, Any]

@app.post("/orders/{order_id}/signals/update-address")
async def update_address(order_id: str, body: UpdateAddressBody):
    client: Client = app.state.client
    handle = client.get_workflow_handle(f"order-{order_id}")
    await handle.signal("update_address", body.address)
    return {"ok": True}

@app.post("/orders/{order_id}/signals/approve")
async def approve_order(order_id: str):
    client: Client = app.state.client
    handle = client.get_workflow_handle(f"order-{order_id}")
    await handle.signal("approve_order")
    return {"ok": True}

@app.get("/orders/{order_id}/status")
async def status(order_id: str):
    client: Client = app.state.client
    handle = client.get_workflow_handle(f"order-{order_id}")
    try:
        status = await handle.query("status")
    except Exception as e:
        raise HTTPException(404, f"Workflow not found or not queryable: {e}")
    return status

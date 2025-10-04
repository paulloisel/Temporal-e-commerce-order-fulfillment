from __future__ import annotations
import json
import asyncpg
import structlog
from typing import Dict, Any
from temporalio import activity
from .stubs import (
    order_received, order_validated, payment_charged,
    order_shipped, package_prepared, carrier_dispatched
)

log = structlog.get_logger(__name__)

# Activity helpers
async def _conn() -> asyncpg.Connection:
    return await asyncpg.connect(activity.info().inputs[0])  # first arg always DATABASE_URL (no +asyncpg)

@activity.defn(name="ReceiveOrder")
async def receive_order(db_url: str, order_id: str) -> Dict[str, Any]:
    conn = await asyncpg.connect(db_url)
    try:
        payload = await order_received(order_id)
        await conn.execute(
            "INSERT INTO orders(id, state, address_json) VALUES($1, $2, $3) ON CONFLICT (id) DO NOTHING",
            order_id, "RECEIVED", json.dumps({})
        )
        await conn.execute(
            "INSERT INTO events(order_id, type, payload_json) VALUES ($1, $2, $3)",
            order_id, "order_received", json.dumps(payload)
        )
        return payload
    finally:
        await conn.close()

@activity.defn(name="ValidateOrder")
async def validate_order(db_url: str, order: Dict[str, Any]) -> bool:
    conn = await asyncpg.connect(db_url)
    try:
        ok = await order_validated(order)
        await conn.execute("UPDATE orders SET state='VALIDATED', updated_at=now() WHERE id=$1", order["order_id"])
        await conn.execute("INSERT INTO events(order_id, type, payload_json) VALUES ($1, $2, $3)",
                           order["order_id"], "order_validated", json.dumps({"ok": ok}))
        return ok
    finally:
        await conn.close()

@activity.defn(name="ChargePayment")
async def charge_payment(db_url: str, order: Dict[str, Any], payment_id: str) -> Dict[str, Any]:
    conn = await asyncpg.connect(db_url)
    try:
        # Idempotency: if payment_id exists, return stored status
        existing = await conn.fetchrow("SELECT status, amount FROM payments WHERE payment_id=$1", payment_id)
        if existing:
            return {"status": existing["status"], "amount": existing["amount"], "idempotent": True}

        result = await payment_charged(order, payment_id, None)
        await conn.execute(
            "INSERT INTO payments(payment_id, order_id, status, amount) VALUES($1,$2,$3,$4) ON CONFLICT (payment_id) DO NOTHING",
            payment_id, order["order_id"], result["status"], result["amount"]
        )
        await conn.execute("UPDATE orders SET state='PAID', updated_at=now() WHERE id=$1", order["order_id"])
        await conn.execute("INSERT INTO events(order_id, type, payload_json) VALUES ($1, $2, $3)",
                           order["order_id"], "payment_charged", json.dumps({"payment_id": payment_id, **result}))
        return result
    finally:
        await conn.close()

@activity.defn(name="PreparePackage")
async def prepare_package(db_url: str, order: Dict[str, Any]) -> str:
    conn = await asyncpg.connect(db_url)
    try:
        res = await package_prepared(order)
        await conn.execute("INSERT INTO events(order_id, type, payload_json) VALUES ($1, $2, $3)",
                           order["order_id"], "package_prepared", json.dumps({"result": res}))
        return res
    finally:
        await conn.close()

@activity.defn(name="DispatchCarrier")
async def dispatch_carrier(db_url: str, order: Dict[str, Any]) -> str:
    conn = await asyncpg.connect(db_url)
    try:
        res = await carrier_dispatched(order)
        await conn.execute("UPDATE orders SET state='SHIPPED', updated_at=now() WHERE id=$1", order["order_id"])
        await conn.execute("INSERT INTO events(order_id, type, payload_json) VALUES ($1, $2, $3)",
                           order["order_id"], "carrier_dispatched", json.dumps({"result": res}))
        return res
    finally:
        await conn.close()

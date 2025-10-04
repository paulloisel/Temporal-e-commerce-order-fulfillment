import asyncio, random
from typing import Dict, Any, Optional

async def flaky_call() -> None:
    """Either raise an error or sleep long enough to trigger an activity timeout."""
    rand_num = random.random()
    if rand_num < 0.33:
        raise RuntimeError("Forced failure for testing")
    if rand_num < 0.67:
        await asyncio.sleep(300)  # Expect the activity layer to time out before this completes

async def order_received(order_id: str) -> Dict[str, Any]:
    await flaky_call()
    return {"order_id": order_id, "items": [{"sku": "ABC", "qty": 1}]}

async def order_validated(order: Dict[str, Any]) -> bool:
    await flaky_call()
    if not order.get("items"):
        raise ValueError("No items to validate")
    return True

async def payment_charged(order: Dict[str, Any], payment_id: str, db: Optional[Any] = None) -> Dict[str, Any]:
    await flaky_call()
    amount = sum(i.get("qty", 1) for i in order.get("items", []))
    return {"status": "charged", "amount": amount}

async def order_shipped(order: Dict[str, Any]) -> str:
    await flaky_call()
    return "Shipped"

async def package_prepared(order: Dict[str, Any]) -> str:
    await flaky_call()
    return "Package ready"

async def carrier_dispatched(order: Dict[str, Any]) -> str:
    await flaky_call()
    return "Dispatched"

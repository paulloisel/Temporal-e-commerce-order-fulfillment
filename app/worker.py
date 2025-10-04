import asyncio
import structlog
from temporalio.client import Client
from temporalio.worker import Worker
from .config import TEMPORAL_TARGET, ORDER_TASK_QUEUE, SHIPPING_TASK_QUEUE
from .workflows import OrderWorkflow, ShippingWorkflow
from .activities import receive_order, validate_order, charge_payment, prepare_package, dispatch_carrier

log = structlog.get_logger(__name__)

async def main():
    client = await Client.connect(TEMPORAL_TARGET)
    # Single process registering both queues for simplicity
    async with Worker(
        client,
        task_queue=ORDER_TASK_QUEUE,
        workflows=[OrderWorkflow],
        activities=[receive_order, validate_order, charge_payment],
    ), Worker(
        client,
        task_queue=SHIPPING_TASK_QUEUE,
        workflows=[ShippingWorkflow],
        activities=[prepare_package, dispatch_carrier],
    ):
        log.info("worker.started", order_tq=ORDER_TASK_QUEUE, shipping_tq=SHIPPING_TASK_QUEUE)
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

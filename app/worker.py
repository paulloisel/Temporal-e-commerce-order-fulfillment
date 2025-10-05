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
    
    # Create workers for each task queue
    # Register all activities on both queues to ensure availability
    all_activities = [receive_order, validate_order, charge_payment, prepare_package, dispatch_carrier]
    
    order_worker = Worker(
        client,
        task_queue=ORDER_TASK_QUEUE,
        workflows=[OrderWorkflow],
        activities=all_activities,
    )
    
    shipping_worker = Worker(
        client,
        task_queue=SHIPPING_TASK_QUEUE,
        workflows=[ShippingWorkflow],
        activities=all_activities,
    )
    
    # Start both workers
    async with order_worker, shipping_worker:
        log.info("worker.started", order_tq=ORDER_TASK_QUEUE, shipping_tq=SHIPPING_TASK_QUEUE)
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

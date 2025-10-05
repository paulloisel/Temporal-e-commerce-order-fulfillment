from __future__ import annotations
import asyncio
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional, Dict, Any
from temporalio import workflow
from temporalio.common import RetryPolicy

from .config import ORDER_TASK_QUEUE, SHIPPING_TASK_QUEUE

# Signals
@workflow.signal
async def cancel_order() -> None: ...
@workflow.signal
async def update_address(address: Dict[str, Any]) -> None: ...
@workflow.signal
async def dispatch_failed(reason: str) -> None: ...

@workflow.defn
class ShippingWorkflow:
    def __init__(self) -> None:
        self.order: Dict[str, Any] = {}
        self.failed_reason: Optional[str] = None

    @workflow.run
    async def run(self, db_url: str, order: Dict[str, Any]) -> str:
        self.order = order
        try:
            await workflow.execute_activity("PreparePackage", 
                                            args=[db_url, order],
                                            start_to_close_timeout=timedelta(seconds=5),
                                            retry_policy=RetryPolicy(maximum_attempts=3),
                                            task_queue=SHIPPING_TASK_QUEUE)
            res = await workflow.execute_activity("DispatchCarrier", 
                                                  args=[db_url, order],
                                                  start_to_close_timeout=timedelta(seconds=5),
                                                  retry_policy=RetryPolicy(maximum_attempts=3),
                                                  task_queue=SHIPPING_TASK_QUEUE)
            return res
        except Exception as e:
            # Signal parent that dispatch failed
            await workflow.signal_external_workflow(workflow.info().parent_workflow_id, "dispatch_failed", str(e))
            raise

@workflow.defn
class OrderWorkflow:
    def __init__(self) -> None:
        self.order: Dict[str, Any] = {}
        self.address: Dict[str, Any] = {}
        self.canceled: bool = False
        self.errors: list[str] = []
        self.step: str = "INIT"

    @workflow.run
    async def run(self, db_url: str, order_id: str, payment_id: str, address: Dict[str, Any]) -> Dict[str, Any]:
        workflow.set_signal_handler("cancel_order", self._on_cancel)
        workflow.set_signal_handler("update_address", self._on_update_address)
        workflow.set_signal_handler("dispatch_failed", self._on_dispatch_failed)

        try:
            self.step = "RECEIVE"
            self.order = await workflow.execute_activity("ReceiveOrder", 
                                                        args=[db_url, order_id],
                                                        start_to_close_timeout=timedelta(seconds=3),
                                                        retry_policy=RetryPolicy(maximum_attempts=3),
                                                        task_queue=ORDER_TASK_QUEUE)
            if self.canceled: raise workflow.ApplicationError("Canceled")

            self.step = "VALIDATE"
            await workflow.execute_activity("ValidateOrder", 
                                            args=[db_url, self.order],
                                            start_to_close_timeout=timedelta(seconds=3),
                                            retry_policy=RetryPolicy(maximum_attempts=3),
                                            task_queue=ORDER_TASK_QUEUE)
            if self.canceled: raise workflow.ApplicationError("Canceled")

            # Manual review timer (simulated delay)
            self.step = "MANUAL_REVIEW"
            await asyncio.sleep(2)

            self.step = "PAY"
            await workflow.execute_activity("ChargePayment", 
                                            args=[db_url, self.order, payment_id],
                                            start_to_close_timeout=timedelta(seconds=4),
                                            retry_policy=RetryPolicy(maximum_attempts=3),
                                            task_queue=ORDER_TASK_QUEUE)
            if self.canceled: raise workflow.ApplicationError("Canceled")

            # Child workflow on separate task queue
            self.step = "SHIP"
            handle = await workflow.start_child_workflow(ShippingWorkflow.run, 
                                                         args=[db_url, self.order],
                                                         id=f"ship-{order_id}",
                                                         task_queue=SHIPPING_TASK_QUEUE,
                                                         retry_policy=RetryPolicy(maximum_attempts=1))
            res = await handle.result()

            return {"status": "completed", "order_id": order_id, "step": self.step, "ship": res, "errors": self.errors}
        except Exception as e:
            self.errors.append(str(e))
            return {"status": "failed", "order_id": order_id, "step": self.step, "errors": self.errors}

    def _on_cancel(self) -> None:
        self.canceled = True

    def _on_update_address(self, address: Dict[str, Any]) -> None:
        self.address = address

    def _on_dispatch_failed(self, reason: str) -> None:
        self.errors.append(f"dispatch_failed: {reason}")

    @workflow.query
    def status(self) -> Dict[str, Any]:
        return {"order": self.order, "step": self.step, "errors": self.errors, "canceled": self.canceled}

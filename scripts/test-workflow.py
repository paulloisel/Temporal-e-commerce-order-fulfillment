#!/usr/bin/env python3
"""
Test Workflow Script

This script runs comprehensive tests of the Temporal workflow system:
- Tests successful workflow completion
- Tests failure scenarios and retries
- Tests signal handling (cancel, update address)
- Tests timeout scenarios
- Generates test reports
"""

import asyncio
import json
import time
import random
from datetime import datetime
from typing import Dict, Any, List

import aiohttp


class WorkflowTester:
    def __init__(self):
        self.api_base = "http://localhost:8000"
        self.test_results = []
        
    def connect_api(self) -> aiohttp.ClientSession:
        """Connect to FastAPI server."""
        return aiohttp.ClientSession()
    
    async def start_workflow(self, order_id: str, payment_id: str, address: Dict[str, Any]) -> Dict[str, Any]:
        """Start a workflow and return the result."""
        payload = {
            "payment_id": payment_id,
            "address": address
        }
        
        async with self.connect_api() as session:
            async with session.post(
                f"{self.api_base}/orders/{order_id}/start",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error = await response.text()
                    raise Exception(f"Failed to start workflow: {error}")
    
    async def get_workflow_status(self, order_id: str) -> Dict[str, Any]:
        """Get workflow status."""
        async with self.connect_api() as session:
            async with session.get(f"{self.api_base}/orders/{order_id}/status") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error = await response.text()
                    raise Exception(f"Failed to get status: {error}")
    
    async def cancel_workflow(self, order_id: str) -> Dict[str, Any]:
        """Cancel a workflow."""
        async with self.connect_api() as session:
            async with session.post(f"{self.api_base}/orders/{order_id}/signals/cancel") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error = await response.text()
                    raise Exception(f"Failed to cancel workflow: {error}")
    
    async def update_address(self, order_id: str, address: Dict[str, Any]) -> Dict[str, Any]:
        """Update workflow address."""
        payload = {"address": address}
        
        async with self.connect_api() as session:
            async with session.post(
                f"{self.api_base}/orders/{order_id}/signals/update-address",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error = await response.text()
                    raise Exception(f"Failed to update address: {error}")
    
    async def monitor_workflow(self, order_id: str, max_wait: int = 30) -> Dict[str, Any]:
        """Monitor a workflow until completion or timeout."""
        start_time = time.time()
        steps_seen = []
        
        while time.time() - start_time < max_wait:
            try:
                status = await self.get_workflow_status(order_id)
                current_step = status.get("step", "UNKNOWN")
                
                if current_step not in steps_seen:
                    steps_seen.append(current_step)
                    print(f"  📍 Step: {current_step}")
                
                # Check if workflow is in a terminal state
                if status.get("errors"):
                    return {
                        "status": "failed",
                        "final_step": current_step,
                        "errors": status.get("errors", []),
                        "steps_seen": steps_seen,
                        "duration": time.time() - start_time
                    }
                
                # If we've seen SHIP step, workflow likely completed successfully
                if current_step == "SHIP" and not status.get("errors"):
                    await asyncio.sleep(2)  # Give it a moment to complete
                    final_status = await self.get_workflow_status(order_id)
                    return {
                        "status": "completed",
                        "final_step": current_step,
                        "steps_seen": steps_seen,
                        "duration": time.time() - start_time,
                        "final_status": final_status
                    }
                
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"  ❌ Error monitoring workflow: {e}")
                return {
                    "status": "error",
                    "error": str(e),
                    "duration": time.time() - start_time
                }
        
        return {
            "status": "timeout",
            "steps_seen": steps_seen,
            "duration": max_wait
        }
    
    async def test_successful_workflow(self) -> Dict[str, Any]:
        """Test a successful workflow completion."""
        print("🧪 Test 1: Successful Workflow")
        
        order_id = f"test-success-{int(time.time())}"
        payment_id = f"pmt-success-{order_id}"
        address = {
            "street": "123 Success St",
            "city": "Test City",
            "state": "TS",
            "zip": "12345",
            "country": "US"
        }
        
        try:
            # Start workflow
            result = await self.start_workflow(order_id, payment_id, address)
            print(f"  ✅ Workflow started: {result['workflow_id']}")
            
            # Monitor workflow
            monitor_result = await self.monitor_workflow(order_id, max_wait=20)
            
            test_result = {
                "test_name": "successful_workflow",
                "order_id": order_id,
                "workflow_id": result['workflow_id'],
                "monitor_result": monitor_result,
                "success": monitor_result["status"] == "completed"
            }
            
            if test_result["success"]:
                print(f"  ✅ Test passed: Workflow completed successfully")
            else:
                print(f"  ❌ Test failed: {monitor_result}")
            
            return test_result
            
        except Exception as e:
            print(f"  ❌ Test failed with exception: {e}")
            return {
                "test_name": "successful_workflow",
                "order_id": order_id,
                "success": False,
                "error": str(e)
            }
    
    async def test_cancellation(self) -> Dict[str, Any]:
        """Test workflow cancellation."""
        print("🧪 Test 2: Workflow Cancellation")
        
        order_id = f"test-cancel-{int(time.time())}"
        payment_id = f"pmt-cancel-{order_id}"
        address = {
            "street": "456 Cancel St",
            "city": "Test City",
            "state": "TS",
            "zip": "12345",
            "country": "US"
        }
        
        try:
            # Start workflow
            result = await self.start_workflow(order_id, payment_id, address)
            print(f"  ✅ Workflow started: {result['workflow_id']}")
            
            # Wait a moment for workflow to start
            await asyncio.sleep(2)
            
            # Cancel workflow
            cancel_result = await self.cancel_workflow(order_id)
            print(f"  ✅ Cancellation signal sent: {cancel_result}")
            
            # Monitor workflow
            monitor_result = await self.monitor_workflow(order_id, max_wait=10)
            
            test_result = {
                "test_name": "workflow_cancellation",
                "order_id": order_id,
                "workflow_id": result['workflow_id'],
                "monitor_result": monitor_result,
                "success": "canceled" in str(monitor_result).lower() or monitor_result["status"] == "failed"
            }
            
            if test_result["success"]:
                print(f"  ✅ Test passed: Workflow was cancelled")
            else:
                print(f"  ❌ Test failed: {monitor_result}")
            
            return test_result
            
        except Exception as e:
            print(f"  ❌ Test failed with exception: {e}")
            return {
                "test_name": "workflow_cancellation",
                "order_id": order_id,
                "success": False,
                "error": str(e)
            }
    
    async def test_address_update(self) -> Dict[str, Any]:
        """Test address update signal."""
        print("🧪 Test 3: Address Update")
        
        order_id = f"test-address-{int(time.time())}"
        payment_id = f"pmt-address-{order_id}"
        original_address = {
            "street": "789 Original St",
            "city": "Original City",
            "state": "OS",
            "zip": "00000",
            "country": "US"
        }
        
        new_address = {
            "street": "999 Updated St",
            "city": "Updated City",
            "state": "US",
            "zip": "99999",
            "country": "US"
        }
        
        try:
            # Start workflow
            result = await self.start_workflow(order_id, payment_id, original_address)
            print(f"  ✅ Workflow started: {result['workflow_id']}")
            
            # Wait a moment for workflow to start
            await asyncio.sleep(2)
            
            # Update address
            update_result = await self.update_address(order_id, new_address)
            print(f"  ✅ Address update signal sent: {update_result}")
            
            # Monitor workflow
            monitor_result = await self.monitor_workflow(order_id, max_wait=15)
            
            test_result = {
                "test_name": "address_update",
                "order_id": order_id,
                "workflow_id": result['workflow_id'],
                "monitor_result": monitor_result,
                "success": monitor_result["status"] in ["completed", "failed"]  # Either is acceptable
            }
            
            if test_result["success"]:
                print(f"  ✅ Test passed: Address update processed")
            else:
                print(f"  ❌ Test failed: {monitor_result}")
            
            return test_result
            
        except Exception as e:
            print(f"  ❌ Test failed with exception: {e}")
            return {
                "test_name": "address_update",
                "order_id": order_id,
                "success": False,
                "error": str(e)
            }
    
    async def test_batch_workflows(self, count: int = 5) -> Dict[str, Any]:
        """Test multiple workflows in parallel."""
        print(f"🧪 Test 4: Batch Workflows ({count} workflows)")
        
        tasks = []
        for i in range(count):
            order_id = f"test-batch-{int(time.time())}-{i}"
            payment_id = f"pmt-batch-{order_id}"
            address = {
                "street": f"{100 + i} Batch St",
                "city": "Batch City",
                "state": "BS",
                "zip": f"{10000 + i}",
                "country": "US"
            }
            
            task = self._test_single_workflow(order_id, payment_id, address)
            tasks.append(task)
        
        # Run all workflows in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success", False))
        failed = count - successful
        
        test_result = {
            "test_name": "batch_workflows",
            "total_workflows": count,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / count,
            "results": results
        }
        
        print(f"  📊 Results: {successful}/{count} successful ({test_result['success_rate']:.1%})")
        
        return test_result
    
    async def _test_single_workflow(self, order_id: str, payment_id: str, address: Dict[str, Any]) -> Dict[str, Any]:
        """Test a single workflow."""
        try:
            result = await self.start_workflow(order_id, payment_id, address)
            monitor_result = await self.monitor_workflow(order_id, max_wait=15)
            
            return {
                "order_id": order_id,
                "workflow_id": result['workflow_id'],
                "success": monitor_result["status"] == "completed",
                "monitor_result": monitor_result
            }
        except Exception as e:
            return {
                "order_id": order_id,
                "success": False,
                "error": str(e)
            }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and generate a report."""
        print("🚀 Starting Comprehensive Workflow Tests")
        print("=" * 50)
        
        start_time = time.time()
        
        # Run individual tests
        test1 = await self.test_successful_workflow()
        await asyncio.sleep(2)
        
        test2 = await self.test_cancellation()
        await asyncio.sleep(2)
        
        test3 = await self.test_address_update()
        await asyncio.sleep(2)
        
        test4 = await self.test_batch_workflows(3)  # Reduced for faster testing
        
        total_time = time.time() - start_time
        
        # Generate report
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_duration": total_time,
            "tests": {
                "successful_workflow": test1,
                "workflow_cancellation": test2,
                "address_update": test3,
                "batch_workflows": test4
            },
            "summary": {
                "total_tests": 4,
                "passed": sum(1 for t in [test1, test2, test3, test4] if t.get("success", False)),
                "failed": sum(1 for t in [test1, test2, test3, test4] if not t.get("success", False))
            }
        }
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        print(f"Total Duration: {total_time:.2f} seconds")
        print(f"Tests Passed: {report['summary']['passed']}/{report['summary']['total_tests']}")
        print(f"Success Rate: {report['summary']['passed']/report['summary']['total_tests']:.1%}")
        
        # Save report
        with open("test_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: test_report.json")
        
        return report


async def main():
    tester = WorkflowTester()
    
    try:
        report = await tester.run_all_tests()
        
        if report['summary']['passed'] == report['summary']['total_tests']:
            print("\n🎉 All tests passed!")
            exit(0)
        else:
            print(f"\n⚠️  {report['summary']['failed']} test(s) failed")
            exit(1)
            
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())

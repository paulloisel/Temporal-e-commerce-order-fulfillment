#!/usr/bin/env python3
"""
Temporal E-commerce Order Fulfillment CLI

This script provides command-line interface for managing the Temporal deployment:
- Start/stop services
- Trigger workflows
- Send signals
- Inspect workflow state
- View logs and history
"""

import asyncio
import json
import sys
import argparse
import subprocess
import time
from datetime import datetime
from typing import Dict, Any, Optional

import aiohttp
from temporalio.client import Client


class TemporalCLI:
    def __init__(self):
        self.temporal_target = "localhost:7233"
        self.api_base = "http://localhost:8000"
        
    async def connect_temporal(self) -> Client:
        """Connect to Temporal server."""
        try:
            return await Client.connect(self.temporal_target)
        except Exception as e:
            print(f"❌ Failed to connect to Temporal: {e}")
            sys.exit(1)
    
    def connect_api(self) -> aiohttp.ClientSession:
        """Connect to FastAPI server."""
        return aiohttp.ClientSession()
    
    def run_docker_compose(self, command: str) -> bool:
        """Run docker compose command."""
        try:
            result = subprocess.run(
                f"docker compose {command}",
                shell=True,
                capture_output=True,
                text=True,
                cwd="."
            )
            if result.returncode == 0:
                print(f"✅ Docker compose {command} succeeded")
                return True
            else:
                print(f"❌ Docker compose {command} failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Error running docker compose {command}: {e}")
            return False
    
    async def start_services(self):
        """Start all services (Temporal, PostgreSQL, App)."""
        print("🚀 Starting Temporal E-commerce Order Fulfillment services...")
        
        if not self.run_docker_compose("up -d"):
            return False
            
        print("⏳ Waiting for services to be ready...")
        await asyncio.sleep(10)
        
        # Test connections
        try:
            client = await self.connect_temporal()
            print("✅ Temporal server connected")
            
            async with self.connect_api() as session:
                async with session.get(f"{self.api_base}/docs") as response:
                    if response.status == 200:
                        print("✅ FastAPI server connected")
                    else:
                        print(f"❌ FastAPI server returned status {response.status}")
                        return False
        except Exception as e:
            print(f"❌ Service health check failed: {e}")
            return False
            
        print("🎉 All services started successfully!")
        return True
    
    async def stop_services(self):
        """Stop all services."""
        print("🛑 Stopping services...")
        self.run_docker_compose("down")
        print("✅ Services stopped")
    
    async def start_workflow(self, order_id: str, payment_id: str, address: Optional[Dict[str, Any]] = None):
        """Start a new order workflow."""
        if address is None:
            address = {
                "street": "123 Main St",
                "city": "Test City", 
                "state": "TS",
                "zip": "12345",
                "country": "US"
            }
        
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
                    result = await response.json()
                    print(f"✅ Workflow started: {result}")
                    return result
                else:
                    error = await response.text()
                    print(f"❌ Failed to start workflow: {error}")
                    return None
    
    async def get_workflow_status(self, order_id: str):
        """Get workflow status."""
        async with self.connect_api() as session:
            async with session.get(f"{self.api_base}/orders/{order_id}/status") as response:
                if response.status == 200:
                    status = await response.json()
                    print(f"📊 Workflow Status for {order_id}:")
                    print(json.dumps(status, indent=2))
                    return status
                else:
                    error = await response.text()
                    print(f"❌ Failed to get status: {error}")
                    return None
    
    async def cancel_workflow(self, order_id: str):
        """Cancel a workflow."""
        async with self.connect_api() as session:
            async with session.post(f"{self.api_base}/orders/{order_id}/signals/cancel") as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Workflow {order_id} cancelled: {result}")
                    return result
                else:
                    error = await response.text()
                    print(f"❌ Failed to cancel workflow: {error}")
                    return None
    
    async def update_address(self, order_id: str, address: Dict[str, Any]):
        """Update workflow address."""
        payload = {"address": address}
        
        async with self.connect_api() as session:
            async with session.post(
                f"{self.api_base}/orders/{order_id}/signals/update-address",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Address updated for {order_id}: {result}")
                    return result
                else:
                    error = await response.text()
                    print(f"❌ Failed to update address: {error}")
                    return None

    async def approve_order(self, order_id: str):
        """Approve workflow for payment."""
        async with self.connect_api() as session:
            async with session.post(
                f"{self.api_base}/orders/{order_id}/signals/approve",
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Order approved for {order_id}: {result}")
                    return result
                else:
                    error = await response.text()
                    print(f"❌ Failed to approve order: {error}")
                    return None
    
    async def list_workflows(self, limit: int = 20):
        """List recent workflows using Temporal CLI."""
        try:
            result = subprocess.run(
                f"docker compose exec temporal temporal --address temporal:7233 workflow list --limit {limit}",
                shell=True,
                capture_output=True,
                text=True,
                cwd="."
            )
            if result.returncode == 0:
                print("📋 Recent Workflows:")
                print(result.stdout)
                return result.stdout
            else:
                print(f"❌ Failed to list workflows: {result.stderr}")
                return None
        except Exception as e:
            print(f"❌ Error listing workflows: {e}")
            return None
    
    async def describe_workflow(self, workflow_id: str):
        """Describe a specific workflow."""
        try:
            result = subprocess.run(
                f"docker compose exec temporal temporal --address temporal:7233 workflow describe --workflow-id {workflow_id}",
                shell=True,
                capture_output=True,
                text=True,
                cwd="."
            )
            if result.returncode == 0:
                print(f"📄 Workflow Description for {workflow_id}:")
                print(result.stdout)
                return result.stdout
            else:
                print(f"❌ Failed to describe workflow: {result.stderr}")
                return None
        except Exception as e:
            print(f"❌ Error describing workflow: {e}")
            return None
    
    async def show_workflow_history(self, workflow_id: str):
        """Show workflow execution history."""
        try:
            result = subprocess.run(
                f"docker compose exec temporal temporal --address temporal:7233 workflow show --workflow-id {workflow_id}",
                shell=True,
                capture_output=True,
                text=True,
                cwd="."
            )
            if result.returncode == 0:
                print(f"📜 Workflow History for {workflow_id}:")
                print(result.stdout)
                return result.stdout
            else:
                print(f"❌ Failed to show workflow history: {result.stderr}")
                return None
        except Exception as e:
            print(f"❌ Error showing workflow history: {e}")
            return None
    
    async def show_logs(self, service: str = "app", lines: int = 50):
        """Show service logs."""
        try:
            result = subprocess.run(
                f"docker compose logs {service} --tail={lines}",
                shell=True,
                capture_output=True,
                text=True,
                cwd="."
            )
            if result.returncode == 0:
                print(f"📝 {service.title()} Logs (last {lines} lines):")
                print(result.stdout)
                return result.stdout
            else:
                print(f"❌ Failed to show logs: {result.stderr}")
                return None
        except Exception as e:
            print(f"❌ Error showing logs: {e}")
            return None
    
    async def demo_workflow(self):
        """Run a complete workflow demonstration."""
        print("🎬 Running Workflow Demonstration...")
        
        # Start a workflow
        order_id = f"demo-{int(time.time())}"
        payment_id = f"pmt-{order_id}"
        
        print(f"\n1️⃣ Starting workflow: {order_id}")
        result = await self.start_workflow(order_id, payment_id)
        if not result:
            return
        
        # Monitor for a few seconds
        print(f"\n2️⃣ Monitoring workflow for 5 seconds...")
        for i in range(5):
            await asyncio.sleep(1)
            status = await self.get_workflow_status(order_id)
            if status and status.get("step"):
                print(f"   Step: {status['step']}")
        
        # Show final status
        print(f"\n3️⃣ Final status:")
        await self.get_workflow_status(order_id)
        
        # Show workflow in Temporal CLI
        print(f"\n4️⃣ Workflow in Temporal CLI:")
        await self.describe_workflow(f"order-{order_id}")
        
        print(f"\n✅ Demo completed for workflow: {order_id}")


async def main():
    parser = argparse.ArgumentParser(description="Temporal E-commerce Order Fulfillment CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Service management
    subparsers.add_parser("start", help="Start all services")
    subparsers.add_parser("stop", help="Stop all services")
    subparsers.add_parser("restart", help="Restart all services")
    
    # Workflow management
    start_parser = subparsers.add_parser("start-workflow", help="Start a new workflow")
    start_parser.add_argument("order_id", help="Order ID")
    start_parser.add_argument("payment_id", help="Payment ID")
    
    status_parser = subparsers.add_parser("status", help="Get workflow status")
    status_parser.add_argument("order_id", help="Order ID")
    
    cancel_parser = subparsers.add_parser("cancel", help="Cancel a workflow")
    cancel_parser.add_argument("order_id", help="Order ID")
    
    update_parser = subparsers.add_parser("update-address", help="Update workflow address")
    update_parser.add_argument("order_id", help="Order ID")
    update_parser.add_argument("--street", default="456 New St", help="Street address")
    update_parser.add_argument("--city", default="New City", help="City")
    update_parser.add_argument("--state", default="NS", help="State")
    update_parser.add_argument("--zip", default="54321", help="ZIP code")
    update_parser.add_argument("--country", default="US", help="Country")
    
    approve_parser = subparsers.add_parser("approve", help="Approve a workflow for payment")
    approve_parser.add_argument("order_id", help="Order ID")
    
    # Inspection
    list_parser = subparsers.add_parser("list", help="List recent workflows")
    list_parser.add_argument("--limit", type=int, default=20, help="Number of workflows to show")
    
    describe_parser = subparsers.add_parser("describe", help="Describe a workflow")
    describe_parser.add_argument("workflow_id", help="Workflow ID")
    
    history_parser = subparsers.add_parser("history", help="Show workflow history")
    history_parser.add_argument("workflow_id", help="Workflow ID")
    
    logs_parser = subparsers.add_parser("logs", help="Show service logs")
    logs_parser.add_argument("--service", default="app", help="Service name (app, temporal, postgres)")
    logs_parser.add_argument("--lines", type=int, default=50, help="Number of log lines")
    
    # Demo
    subparsers.add_parser("demo", help="Run a complete workflow demonstration")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = TemporalCLI()
    
    try:
        if args.command == "start":
            await cli.start_services()
        elif args.command == "stop":
            await cli.stop_services()
        elif args.command == "restart":
            await cli.stop_services()
            await asyncio.sleep(2)
            await cli.start_services()
        elif args.command == "start-workflow":
            await cli.start_workflow(args.order_id, args.payment_id)
        elif args.command == "status":
            await cli.get_workflow_status(args.order_id)
        elif args.command == "cancel":
            await cli.cancel_workflow(args.order_id)
        elif args.command == "update-address":
            address = {
                "street": args.street,
                "city": args.city,
                "state": args.state,
                "zip": args.zip,
                "country": args.country
            }
            await cli.update_address(args.order_id, address)
        elif args.command == "approve":
            await cli.approve_order(args.order_id)
        elif args.command == "list":
            await cli.list_workflows(args.limit)
        elif args.command == "describe":
            await cli.describe_workflow(args.workflow_id)
        elif args.command == "history":
            await cli.show_workflow_history(args.workflow_id)
        elif args.command == "logs":
            await cli.show_logs(args.service, args.lines)
        elif args.command == "demo":
            await cli.demo_workflow()
        else:
            parser.print_help()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

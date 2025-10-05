#!/usr/bin/env python3
"""
Simple test script to verify the real deployment is working.
"""
import asyncio
import json
import aiohttp
from temporalio.client import Client

async def test_deployment():
    """Test the real deployment."""
    print("🚀 Testing Real Temporal Deployment...")
    
    # Test 1: Check if services are running
    print("\n1. Checking if services are running...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/docs") as response:
                if response.status == 200:
                    print("✅ FastAPI is running")
                else:
                    print(f"❌ FastAPI returned status {response.status}")
    except Exception as e:
        print(f"❌ FastAPI not accessible: {e}")
        return
    
    # Test 2: Check Temporal connection
    print("\n2. Checking Temporal connection...")
    try:
        client = await Client.connect("localhost:7233")
        print("✅ Temporal client connected")
    except Exception as e:
        print(f"❌ Temporal connection failed: {e}")
        return
    
    # Test 3: Start a workflow
    print("\n3. Starting a test workflow...")
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "payment_id": "test-pmt-001",
                "address": {
                    "street": "123 Test St",
                    "city": "Test City",
                    "state": "TS",
                    "zip": "12345",
                    "country": "US"
                }
            }
            async with session.post(
                "http://localhost:8000/orders/test-deployment-001/start",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Workflow started: {result}")
                    workflow_id = result["workflow_id"]
                else:
                    print(f"❌ Failed to start workflow: {response.status}")
                    return
    except Exception as e:
        print(f"❌ Failed to start workflow: {e}")
        return
    
    # Test 4: Check workflow status
    print("\n4. Checking workflow status...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://localhost:8000/orders/test-deployment-001/status") as response:
                if response.status == 200:
                    status = await response.json()
                    print(f"✅ Workflow status: {json.dumps(status, indent=2)}")
                else:
                    print(f"❌ Failed to get status: {response.status}")
    except Exception as e:
        print(f"❌ Failed to get status: {e}")
    
    print("\n🎉 Deployment test completed!")

if __name__ == "__main__":
    asyncio.run(test_deployment())

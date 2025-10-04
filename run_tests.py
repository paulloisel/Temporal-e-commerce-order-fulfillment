#!/usr/bin/env python3
"""
Comprehensive test runner for the Temporal E-commerce Order Fulfillment System.

This script provides different test execution modes:
- unit: Run unit tests only
- integration: Run integration tests only  
- e2e: Run end-to-end tests only
- all: Run all tests
- quick: Run quick smoke tests only

Usage:
    python run_tests.py [mode] [options]

Examples:
    python run_tests.py quick
    python run_tests.py unit -v
    python run_tests.py all --tb=short
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

def setup_environment():
    """Set up the test environment."""
    # Add the project root to Python path
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    
    # Set environment variables for testing
    os.environ.setdefault("DATABASE_URL", "postgresql://app:app@localhost:5432/app")
    os.environ.setdefault("TEMPORAL_TARGET", "localhost:7233")
    os.environ.setdefault("ORDER_TASK_QUEUE", "test-orders-tq")
    os.environ.setdefault("SHIPPING_TASK_QUEUE", "test-shipping-tq")
    os.environ.setdefault("LOG_LEVEL", "INFO")

def run_pytest(test_path, args=None):
    """Run pytest with the given test path and arguments."""
    cmd = ["python", "-m", "pytest"]
    
    if args:
        cmd.extend(args)
    
    cmd.append(str(test_path))
    
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=Path(__file__).parent)

def main():
    parser = argparse.ArgumentParser(description="Run tests for Temporal E-commerce Order Fulfillment System")
    parser.add_argument("mode", nargs="?", default="quick", 
                       choices=["unit", "integration", "e2e", "all", "quick"],
                       help="Test mode to run")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--tb", default="short", help="Traceback format (short, long, auto)")
    parser.add_argument("--maxfail", type=int, help="Stop after N failures")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage")
    parser.add_argument("--html", action="store_true", help="Generate HTML coverage report")
    
    args = parser.parse_args()
    
    # Set up environment
    setup_environment()
    
    # Build pytest arguments
    pytest_args = []
    if args.verbose:
        pytest_args.append("-v")
    if args.tb:
        pytest_args.extend(["--tb", args.tb])
    if args.maxfail:
        pytest_args.extend(["--maxfail", str(args.maxfail)])
    if args.coverage:
        pytest_args.extend(["--cov=app", "--cov-report=term-missing"])
    if args.html:
        pytest_args.extend(["--cov-report=html"])
    
    # Determine test path based on mode
    project_root = Path(__file__).parent
    
    if args.mode == "quick":
        test_path = project_root / "app" / "tests"
        print("🚀 Running quick smoke tests...")
    elif args.mode == "unit":
        test_path = project_root / "tests" / "unit"
        print("🔧 Running unit tests...")
    elif args.mode == "integration":
        test_path = project_root / "tests" / "integration"
        print("🔗 Running integration tests...")
    elif args.mode == "e2e":
        test_path = project_root / "tests" / "e2e"
        print("🎯 Running end-to-end tests...")
    elif args.mode == "all":
        test_path = project_root / "tests"
        print("🧪 Running all tests...")
    
    # Check if test path exists
    if not test_path.exists():
        print(f"❌ Test path does not exist: {test_path}")
        print("Available test paths:")
        for test_dir in project_root.glob("**/test*.py"):
            print(f"  - {test_dir}")
        return 1
    
    # Run tests
    result = run_pytest(test_path, pytest_args)
    
    # Print summary
    if result.returncode == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())

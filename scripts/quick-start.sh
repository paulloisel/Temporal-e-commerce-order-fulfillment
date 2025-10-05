#!/bin/bash
# Quick Start Script for Temporal E-commerce Order Fulfillment

set -e

echo "🚀 Temporal E-commerce Order Fulfillment - Quick Start"
echo "======================================================"

# Check if docker compose is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not available. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://app:app@postgres:5432/app
TEMPORAL_TARGET=temporal:7233
ORDER_TASK_QUEUE=orders-tq
SHIPPING_TASK_QUEUE=shipping-tq
LOG_LEVEL=INFO
EOF
    echo "✅ .env file created"
else
    echo "✅ .env file already exists"
fi

# Start services
echo "🐳 Starting services with Docker Compose..."
docker compose up -d

echo "⏳ Waiting for services to be ready..."
sleep 10

# Test connections
echo "🔍 Testing service connections..."

# Test Temporal connection
if docker compose exec temporal temporal --address temporal:7233 workflow list &> /dev/null; then
    echo "✅ Temporal server is ready"
else
    echo "❌ Temporal server is not ready"
    exit 1
fi

# Test FastAPI connection
if curl -s http://localhost:8000/docs &> /dev/null; then
    echo "✅ FastAPI server is ready"
else
    echo "❌ FastAPI server is not ready"
    exit 1
fi

# Test PostgreSQL connection
if docker compose exec postgres pg_isready -U app &> /dev/null; then
    echo "✅ PostgreSQL database is ready"
else
    echo "❌ PostgreSQL database is not ready"
    exit 1
fi

echo ""
echo "🎉 All services are running successfully!"
echo ""
echo "📋 Available endpoints:"
echo "  • FastAPI Docs: http://localhost:8000/docs"
echo "  • Temporal UI: http://localhost:8233"
echo "  • PostgreSQL: localhost:5432 (user: app, password: app, db: app)"
echo ""
echo "🛠️  CLI Usage:"
echo "  • Start a workflow: python scripts/cli.py start-workflow order-123 pmt-123"
echo "  • Check status: python scripts/cli.py status order-123"
echo "  • List workflows: python scripts/cli.py list"
echo "  • Run demo: python scripts/cli.py demo"
echo "  • View logs: python scripts/cli.py logs"
echo ""
echo "🛑 To stop services: docker compose down"
echo "🔄 To restart: docker compose restart"

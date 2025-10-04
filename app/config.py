import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://app:app@localhost:5432/app")
TEMPORAL_TARGET = os.getenv("TEMPORAL_TARGET", "localhost:7233")
ORDER_TASK_QUEUE = os.getenv("ORDER_TASK_QUEUE", "orders-tq")
SHIPPING_TASK_QUEUE = os.getenv("SHIPPING_TASK_QUEUE", "shipping-tq")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

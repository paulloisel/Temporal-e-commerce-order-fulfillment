FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y build-essential curl && rm -rf /var/lib/apt/lists/*

# Copy and install
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app /app/app

EXPOSE 8000

-- 001_init.sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS orders (
  id TEXT PRIMARY KEY,
  state TEXT NOT NULL,
  address_json JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS payments (
  payment_id TEXT PRIMARY KEY,
  order_id TEXT REFERENCES orders(id),
  status TEXT NOT NULL,
  amount INT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS events (
  id BIGSERIAL PRIMARY KEY,
  order_id TEXT,
  type TEXT NOT NULL,
  payload_json JSONB,
  ts TIMESTAMPTZ DEFAULT now()
);

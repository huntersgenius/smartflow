-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enum types
CREATE TYPE order_status AS ENUM (
    'pending', 'accepted', 'preparing', 'ready', 'served', 'cancelled'
);
CREATE TYPE staff_role AS ENUM ('kitchen', 'admin');

-- Core tables
CREATE TABLE restaurants (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(200) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE branches (
    id            SERIAL PRIMARY KEY,
    restaurant_id INT NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    name          VARCHAR(200) NOT NULL,
    address       TEXT,
    active        BOOLEAN NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE dining_tables (
    id          SERIAL PRIMARY KEY,
    branch_id   INT NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    table_code  VARCHAR(50) NOT NULL UNIQUE,
    label       VARCHAR(50) NOT NULL,
    active      BOOLEAN NOT NULL DEFAULT true,
    qr_image_url TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_dining_tables_code ON dining_tables(table_code) WHERE active = true;

CREATE TABLE guest_sessions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash   CHAR(64) NOT NULL UNIQUE,   -- SHA-256 hex of raw token
    table_id     INT NOT NULL REFERENCES dining_tables(id),
    branch_id    INT NOT NULL REFERENCES branches(id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at   TIMESTAMPTZ NOT NULL
);
CREATE INDEX idx_guest_sessions_expires ON guest_sessions(expires_at);

CREATE TABLE staff_users (
    id           SERIAL PRIMARY KEY,
    branch_id    INT NOT NULL REFERENCES branches(id),
    email        VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,   -- bcrypt hash
    role         staff_role NOT NULL,
    full_name    VARCHAR(200),
    active       BOOLEAN NOT NULL DEFAULT true,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE staff_sessions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash   CHAR(64) NOT NULL UNIQUE,
    user_id      INT NOT NULL REFERENCES staff_users(id),
    branch_id    INT NOT NULL REFERENCES branches(id),
    role         staff_role NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at   TIMESTAMPTZ NOT NULL
);

CREATE TABLE menu_categories (
    id          SERIAL PRIMARY KEY,
    branch_id   INT NOT NULL REFERENCES branches(id),
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    image_url   TEXT,
    sort_order  INT NOT NULL DEFAULT 0,
    active      BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE menu_items (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id  INT NOT NULL REFERENCES menu_categories(id),
    branch_id    INT NOT NULL REFERENCES branches(id),
    name         VARCHAR(200) NOT NULL,
    description  TEXT,
    price        NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    image_url    TEXT,
    thumbnail_url TEXT,
    available    BOOLEAN NOT NULL DEFAULT true,
    sort_order   INT NOT NULL DEFAULT 0,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_menu_items_branch ON menu_items(branch_id) WHERE available = true;

CREATE TABLE orders (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id    INT NOT NULL REFERENCES branches(id),
    table_id     INT NOT NULL REFERENCES dining_tables(id),
    session_id   UUID NOT NULL REFERENCES guest_sessions(id),
    idempotency_key UUID NOT NULL,
    status       order_status NOT NULL DEFAULT 'pending',
    total        NUMERIC(10, 2) NOT NULL CHECK (total >= 0),
    note         TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(session_id, idempotency_key)   -- prevents duplicate orders
);
CREATE INDEX idx_orders_branch_status ON orders(branch_id, status)
    WHERE status NOT IN ('served', 'cancelled');
CREATE INDEX idx_orders_session ON orders(session_id);
CREATE INDEX idx_orders_created ON orders(branch_id, created_at DESC);

CREATE TABLE order_items (
    id            BIGSERIAL PRIMARY KEY,
    order_id      UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    menu_item_id  UUID NOT NULL REFERENCES menu_items(id),
    quantity      SMALLINT NOT NULL CHECK (quantity > 0),
    unit_price    NUMERIC(10, 2) NOT NULL,   -- snapshotted at order time
    notes         TEXT
);
CREATE INDEX idx_order_items_order ON order_items(order_id);

-- Append-only audit log - never UPDATE this table
CREATE TABLE order_status_history (
    id          BIGSERIAL PRIMARY KEY,
    order_id    UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    status      order_status NOT NULL,
    changed_by  VARCHAR(100) NOT NULL,  -- 'guest' | 'staff:42'
    changed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    note        TEXT
);

-- ============================================================================
-- 04_FACT_TABLES.SQL: Fact Tables Modeling (Analytics Schema)
-- ============================================================================
-- Purpose: Creates analytical fact tables with explicit grain, strict foreign
-- key integrity, and zero revenue multiplication.
-- Fact tables maintain distinct grains:
--   - fact_orders: 1 row per order
--   - fact_order_items: 1 row per order item
--   - fact_order_payments: 1 row per payment record
--   - fact_order_reviews: 1 row per review record
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS analytics;

-- 1. Fact Order Items (Grain: 1 row per order line item)
DROP TABLE IF EXISTS analytics.fact_order_items CASCADE;
CREATE TABLE analytics.fact_order_items (
    order_item_key VARCHAR(150) PRIMARY KEY,
    order_id VARCHAR(100) NOT NULL,
    order_item_id INTEGER NOT NULL,
    product_id VARCHAR(100) NOT NULL,
    seller_id VARCHAR(100) NOT NULL,
    shipping_limit_date TIMESTAMP,
    price NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    freight_value NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    line_total NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    CONSTRAINT fk_foi_product FOREIGN KEY (product_id) REFERENCES analytics.dim_product(product_id),
    CONSTRAINT fk_foi_seller FOREIGN KEY (seller_id) REFERENCES analytics.dim_seller(seller_id)
);

INSERT INTO analytics.fact_order_items (
    order_item_key,
    order_id,
    order_item_id,
    product_id,
    seller_id,
    shipping_limit_date,
    price,
    freight_value,
    line_total
)
SELECT 
    (order_id || '-' || order_item_id::TEXT) AS order_item_key,
    order_id,
    order_item_id,
    product_id,
    seller_id,
    shipping_limit_date,
    price,
    freight_value,
    line_total
FROM staging.stg_order_items
WHERE product_id IN (SELECT product_id FROM analytics.dim_product)
  AND seller_id IN (SELECT seller_id FROM analytics.dim_seller);

CREATE INDEX idx_foi_order ON analytics.fact_order_items(order_id);
CREATE INDEX idx_foi_product ON analytics.fact_order_items(product_id);
CREATE INDEX idx_foi_seller ON analytics.fact_order_items(seller_id);

-- 2. Fact Orders (Grain: 1 row per order)
DROP TABLE IF EXISTS analytics.fact_orders CASCADE;
CREATE TABLE analytics.fact_orders (
    order_id VARCHAR(100) PRIMARY KEY,
    customer_id VARCHAR(100) NOT NULL,
    customer_key VARCHAR(100) NOT NULL,
    purchase_date_key DATE,
    delivered_date_key DATE,
    estimated_delivery_date_key DATE,
    order_status VARCHAR(50),
    order_purchase_timestamp TIMESTAMP,
    order_approved_at TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP,
    delivery_days INTEGER,
    is_delivered_on_time BOOLEAN,
    item_count INTEGER NOT NULL DEFAULT 0,
    total_merchandise_value NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    total_freight_value NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    total_order_value NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    CONSTRAINT fk_fo_customer FOREIGN KEY (customer_id) REFERENCES analytics.dim_customer(customer_id)
);

-- Pre-aggregate line items to safely attach financial totals to the order grain without fan-out
WITH item_agg AS (
    SELECT 
        order_id,
        COUNT(order_item_id) AS item_count,
        SUM(price) AS total_merchandise_value,
        SUM(freight_value) AS total_freight_value,
        SUM(line_total) AS total_order_value
    FROM staging.stg_order_items
    GROUP BY order_id
)
INSERT INTO analytics.fact_orders (
    order_id,
    customer_id,
    customer_key,
    purchase_date_key,
    delivered_date_key,
    estimated_delivery_date_key,
    order_status,
    order_purchase_timestamp,
    order_approved_at,
    order_delivered_carrier_date,
    order_delivered_customer_date,
    order_estimated_delivery_date,
    delivery_days,
    is_delivered_on_time,
    item_count,
    total_merchandise_value,
    total_freight_value,
    total_order_value
)
SELECT 
    o.order_id,
    o.customer_id,
    o.customer_id AS customer_key,
    o.order_purchase_timestamp::DATE AS purchase_date_key,
    o.order_delivered_customer_date::DATE AS delivered_date_key,
    o.order_estimated_delivery_date::DATE AS estimated_delivery_date_key,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    o.delivery_days,
    o.is_delivered_on_time,
    COALESCE(i.item_count, 0) AS item_count,
    COALESCE(i.total_merchandise_value, 0.00) AS total_merchandise_value,
    COALESCE(i.total_freight_value, 0.00) AS total_freight_value,
    COALESCE(i.total_order_value, 0.00) AS total_order_value
FROM staging.stg_orders o
LEFT JOIN item_agg i ON o.order_id = i.order_id
WHERE o.customer_id IN (SELECT customer_id FROM analytics.dim_customer);

CREATE INDEX idx_fo_cust ON analytics.fact_orders(customer_id);
CREATE INDEX idx_fo_purch_date ON analytics.fact_orders(purchase_date_key);
CREATE INDEX idx_fo_status ON analytics.fact_orders(order_status);

-- Add foreign key constraint from fact_order_items to fact_orders
ALTER TABLE analytics.fact_order_items 
ADD CONSTRAINT fk_foi_order FOREIGN KEY (order_id) REFERENCES analytics.fact_orders(order_id);

-- 3. Fact Order Payments (Grain: 1 row per payment installment/method)
DROP TABLE IF EXISTS analytics.fact_order_payments CASCADE;
CREATE TABLE analytics.fact_order_payments (
    payment_key VARCHAR(150) PRIMARY KEY,
    order_id VARCHAR(100) NOT NULL,
    payment_sequential INTEGER NOT NULL,
    payment_type VARCHAR(50) NOT NULL,
    payment_installments INTEGER NOT NULL,
    payment_value NUMERIC(10,2) NOT NULL,
    CONSTRAINT fk_fop_order FOREIGN KEY (order_id) REFERENCES analytics.fact_orders(order_id)
);

INSERT INTO analytics.fact_order_payments (
    payment_key,
    order_id,
    payment_sequential,
    payment_type,
    payment_installments,
    payment_value
)
SELECT 
    (order_id || '-' || payment_sequential::TEXT) AS payment_key,
    order_id,
    payment_sequential,
    payment_type,
    payment_installments,
    payment_value
FROM staging.stg_order_payments
WHERE order_id IN (SELECT order_id FROM analytics.fact_orders);

CREATE INDEX idx_fop_order ON analytics.fact_order_payments(order_id);
CREATE INDEX idx_fop_type ON analytics.fact_order_payments(payment_type);

-- 4. Fact Order Reviews (Grain: 1 row per review)
DROP TABLE IF EXISTS analytics.fact_order_reviews CASCADE;
CREATE TABLE analytics.fact_order_reviews (
    review_key VARCHAR(150) PRIMARY KEY,
    review_id VARCHAR(100) NOT NULL,
    order_id VARCHAR(100) NOT NULL,
    review_score INTEGER NOT NULL,
    review_comment_title TEXT,
    review_comment_message TEXT,
    review_creation_date TIMESTAMP,
    review_answer_timestamp TIMESTAMP,
    CONSTRAINT fk_for_order FOREIGN KEY (order_id) REFERENCES analytics.fact_orders(order_id)
);

INSERT INTO analytics.fact_order_reviews (
    review_key,
    review_id,
    order_id,
    review_score,
    review_comment_title,
    review_comment_message,
    review_creation_date,
    review_answer_timestamp
)
SELECT 
    (review_id || '-' || order_id) AS review_key,
    review_id,
    order_id,
    review_score,
    review_comment_title,
    review_comment_message,
    review_creation_date,
    review_answer_timestamp
FROM staging.stg_order_reviews
WHERE order_id IN (SELECT order_id FROM analytics.fact_orders)
ON CONFLICT (review_key) DO NOTHING;

CREATE INDEX idx_for_order ON analytics.fact_order_reviews(order_id);
CREATE INDEX idx_for_score ON analytics.fact_order_reviews(review_score);

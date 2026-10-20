-- ============================================================================
-- 01_RAW_SCHEMA.SQL: Raw Schema Definition for Brazilian E-Commerce (Olist)
-- ============================================================================
-- Purpose: Creates the landing schema and tables to store raw, untransformed
-- source data exactly as provided in the 9 official Olist CSV files.
-- All columns maintain their original naming and text representations to
-- prevent silent truncation, imputation, or data distortion at ingestion.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS raw_olist;

-- Ingestion audit tracking log
CREATE TABLE IF NOT EXISTS raw_olist.ingestion_log (
    log_id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    source_file VARCHAR(255) NOT NULL,
    row_count INTEGER NOT NULL,
    ingestion_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) NOT NULL,
    notes TEXT
);

-- 1. Raw Customers
CREATE TABLE IF NOT EXISTS raw_olist.raw_customers (
    customer_id VARCHAR(100),
    customer_unique_id VARCHAR(100),
    customer_zip_code_prefix VARCHAR(50),
    customer_city VARCHAR(100),
    customer_state VARCHAR(50),
    _loaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    _source_file VARCHAR(255)
);

-- 2. Raw Geolocation
CREATE TABLE IF NOT EXISTS raw_olist.raw_geolocation (
    geolocation_zip_code_prefix VARCHAR(50),
    geolocation_lat VARCHAR(50),
    geolocation_lng VARCHAR(50),
    geolocation_city VARCHAR(100),
    geolocation_state VARCHAR(50),
    _loaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    _source_file VARCHAR(255)
);

-- 3. Raw Order Items
CREATE TABLE IF NOT EXISTS raw_olist.raw_order_items (
    order_id VARCHAR(100),
    order_item_id VARCHAR(50),
    product_id VARCHAR(100),
    seller_id VARCHAR(100),
    shipping_limit_date VARCHAR(100),
    price VARCHAR(50),
    freight_value VARCHAR(50),
    _loaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    _source_file VARCHAR(255)
);

-- 4. Raw Order Payments
CREATE TABLE IF NOT EXISTS raw_olist.raw_order_payments (
    order_id VARCHAR(100),
    payment_sequential VARCHAR(50),
    payment_type VARCHAR(50),
    payment_installments VARCHAR(50),
    payment_value VARCHAR(50),
    _loaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    _source_file VARCHAR(255)
);

-- 5. Raw Order Reviews
CREATE TABLE IF NOT EXISTS raw_olist.raw_order_reviews (
    review_id VARCHAR(100),
    order_id VARCHAR(100),
    review_score VARCHAR(50),
    review_comment_title TEXT,
    review_comment_message TEXT,
    review_creation_date VARCHAR(100),
    review_answer_timestamp VARCHAR(100),
    _loaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    _source_file VARCHAR(255)
);

-- 6. Raw Orders
CREATE TABLE IF NOT EXISTS raw_olist.raw_orders (
    order_id VARCHAR(100),
    customer_id VARCHAR(100),
    order_status VARCHAR(50),
    order_purchase_timestamp VARCHAR(100),
    order_approved_at VARCHAR(100),
    order_delivered_carrier_date VARCHAR(100),
    order_delivered_customer_date VARCHAR(100),
    order_estimated_delivery_date VARCHAR(100),
    _loaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    _source_file VARCHAR(255)
);

-- 7. Raw Products
CREATE TABLE IF NOT EXISTS raw_olist.raw_products (
    product_id VARCHAR(100),
    product_category_name VARCHAR(100),
    product_name_lenght VARCHAR(50),
    product_description_lenght VARCHAR(50),
    product_photos_qty VARCHAR(50),
    product_weight_g VARCHAR(50),
    product_length_cm VARCHAR(50),
    product_height_cm VARCHAR(50),
    product_width_cm VARCHAR(50),
    _loaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    _source_file VARCHAR(255)
);

-- 8. Raw Sellers
CREATE TABLE IF NOT EXISTS raw_olist.raw_sellers (
    seller_id VARCHAR(100),
    seller_zip_code_prefix VARCHAR(50),
    seller_city VARCHAR(100),
    seller_state VARCHAR(50),
    _loaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    _source_file VARCHAR(255)
);

-- 9. Raw Product Category Translation
CREATE TABLE IF NOT EXISTS raw_olist.raw_category_translation (
    product_category_name VARCHAR(100),
    product_category_name_english VARCHAR(100),
    _loaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    _source_file VARCHAR(255)
);

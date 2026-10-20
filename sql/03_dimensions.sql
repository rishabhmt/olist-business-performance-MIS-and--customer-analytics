-- ============================================================================
-- 03_DIMENSIONS.SQL: Dimensional Modeling Layer (Analytics Schema)
-- ============================================================================
-- Purpose: Builds dimension tables for the analytical star schema:
-- dim_customer, dim_product, dim_seller, and dim_date.
-- Includes primary surrogate keys, natural business keys, and indexes.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS analytics;

-- 1. Dim Customer
DROP TABLE IF EXISTS analytics.dim_customer CASCADE;
CREATE TABLE analytics.dim_customer (
    customer_key VARCHAR(100) PRIMARY KEY,
    customer_id VARCHAR(100) NOT NULL UNIQUE,
    customer_unique_id VARCHAR(100) NOT NULL,
    customer_zip_code_prefix VARCHAR(50),
    customer_city VARCHAR(100),
    customer_state VARCHAR(50)
);

INSERT INTO analytics.dim_customer (
    customer_key,
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state
)
SELECT 
    customer_id AS customer_key,
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state
FROM staging.stg_customers;

CREATE INDEX idx_dim_cust_unique ON analytics.dim_customer(customer_unique_id);
CREATE INDEX idx_dim_cust_state ON analytics.dim_customer(customer_state);

-- 2. Dim Product
DROP TABLE IF EXISTS analytics.dim_product CASCADE;
CREATE TABLE analytics.dim_product (
    product_key VARCHAR(100) PRIMARY KEY,
    product_id VARCHAR(100) NOT NULL UNIQUE,
    product_category_name VARCHAR(100),
    product_category_name_english VARCHAR(100),
    product_name_lenght INTEGER,
    product_description_lenght INTEGER,
    product_photos_qty INTEGER,
    product_weight_g NUMERIC(10,2),
    product_length_cm NUMERIC(10,2),
    product_height_cm NUMERIC(10,2),
    product_width_cm NUMERIC(10,2)
);

INSERT INTO analytics.dim_product (
    product_key,
    product_id,
    product_category_name,
    product_category_name_english,
    product_name_lenght,
    product_description_lenght,
    product_photos_qty,
    product_weight_g,
    product_length_cm,
    product_height_cm,
    product_width_cm
)
SELECT 
    product_id AS product_key,
    product_id,
    product_category_name,
    product_category_name_english,
    product_name_lenght,
    product_description_lenght,
    product_photos_qty,
    product_weight_g,
    product_length_cm,
    product_height_cm,
    product_width_cm
FROM staging.stg_products;

CREATE INDEX idx_dim_prod_cat ON analytics.dim_product(product_category_name_english);

-- 3. Dim Seller
DROP TABLE IF EXISTS analytics.dim_seller CASCADE;
CREATE TABLE analytics.dim_seller (
    seller_key VARCHAR(100) PRIMARY KEY,
    seller_id VARCHAR(100) NOT NULL UNIQUE,
    seller_zip_code_prefix VARCHAR(50),
    seller_city VARCHAR(100),
    seller_state VARCHAR(50)
);

INSERT INTO analytics.dim_seller (
    seller_key,
    seller_id,
    seller_zip_code_prefix,
    seller_city,
    seller_state
)
SELECT 
    seller_id AS seller_key,
    seller_id,
    seller_zip_code_prefix,
    seller_city,
    seller_state
FROM staging.stg_sellers;

CREATE INDEX idx_dim_seller_state ON analytics.dim_seller(seller_state);

-- 4. Dim Date (Reporting Calendar Dimension)
DROP TABLE IF EXISTS analytics.dim_date CASCADE;
CREATE TABLE analytics.dim_date (
    date_key DATE PRIMARY KEY,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    month_year VARCHAR(20) NOT NULL,
    day_of_month INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    day_name VARCHAR(20) NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

INSERT INTO analytics.dim_date (
    date_key,
    year,
    quarter,
    month,
    month_name,
    month_year,
    day_of_month,
    day_of_week,
    day_name,
    is_weekend
)
SELECT 
    d::DATE AS date_key,
    EXTRACT(YEAR FROM d)::INTEGER AS year,
    EXTRACT(QUARTER FROM d)::INTEGER AS quarter,
    EXTRACT(MONTH FROM d)::INTEGER AS month,
    TO_CHAR(d, 'Month') AS month_name,
    TO_CHAR(d, 'YYYY-MM') AS month_year,
    EXTRACT(DAY FROM d)::INTEGER AS day_of_month,
    EXTRACT(ISODOW FROM d)::INTEGER AS day_of_week,
    TO_CHAR(d, 'Day') AS day_name,
    CASE WHEN EXTRACT(ISODOW FROM d) IN (6, 7) THEN TRUE ELSE FALSE END AS is_weekend
FROM GENERATE_SERIES('2016-01-01'::DATE, '2019-12-31'::DATE, '1 day'::INTERVAL) d;

CREATE INDEX idx_dim_date_my ON analytics.dim_date(month_year);

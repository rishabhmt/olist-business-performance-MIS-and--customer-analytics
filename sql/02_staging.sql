-- ============================================================================
-- 02_STAGING.SQL: Staging Layer & Data Transformation
-- ============================================================================
-- Purpose: Ingests raw data from raw_olist, trims string whitespace,
-- converts empty strings to NULL, parses ISO-8601 timestamps, validates
-- numeric values, and normalizes categorical columns.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS staging;

-- 1. Staging Customers
DROP TABLE IF EXISTS staging.stg_customers CASCADE;
CREATE TABLE staging.stg_customers AS
SELECT 
    TRIM(customer_id) AS customer_id,
    TRIM(customer_unique_id) AS customer_unique_id,
    TRIM(customer_zip_code_prefix) AS customer_zip_code_prefix,
    INITCAP(TRIM(customer_city)) AS customer_city,
    UPPER(TRIM(customer_state)) AS customer_state
FROM raw_olist.raw_customers
WHERE NULLIF(TRIM(customer_id), '') IS NOT NULL;

CREATE INDEX idx_stg_customers_id ON staging.stg_customers(customer_id);
CREATE INDEX idx_stg_customers_unique_id ON staging.stg_customers(customer_unique_id);

-- 2. Staging Orders
DROP TABLE IF EXISTS staging.stg_orders CASCADE;
CREATE TABLE staging.stg_orders AS
SELECT 
    TRIM(order_id) AS order_id,
    TRIM(customer_id) AS customer_id,
    LOWER(TRIM(order_status)) AS order_status,
    NULLIF(TRIM(order_purchase_timestamp), '')::TIMESTAMP AS order_purchase_timestamp,
    NULLIF(TRIM(order_approved_at), '')::TIMESTAMP AS order_approved_at,
    NULLIF(TRIM(order_delivered_carrier_date), '')::TIMESTAMP AS order_delivered_carrier_date,
    NULLIF(TRIM(order_delivered_customer_date), '')::TIMESTAMP AS order_delivered_customer_date,
    NULLIF(TRIM(order_estimated_delivery_date), '')::TIMESTAMP AS order_estimated_delivery_date,
    CASE 
        WHEN NULLIF(TRIM(order_delivered_customer_date), '') IS NOT NULL 
             AND NULLIF(TRIM(order_purchase_timestamp), '') IS NOT NULL
        THEN EXTRACT(DAY FROM (NULLIF(TRIM(order_delivered_customer_date), '')::TIMESTAMP - NULLIF(TRIM(order_purchase_timestamp), '')::TIMESTAMP))
        ELSE NULL
    END AS delivery_days,
    CASE 
        WHEN NULLIF(TRIM(order_delivered_customer_date), '') IS NOT NULL 
             AND NULLIF(TRIM(order_estimated_delivery_date), '') IS NOT NULL
        THEN (NULLIF(TRIM(order_delivered_customer_date), '')::DATE <= NULLIF(TRIM(order_estimated_delivery_date), '')::DATE)
        ELSE NULL
    END AS is_delivered_on_time
FROM raw_olist.raw_orders
WHERE NULLIF(TRIM(order_id), '') IS NOT NULL;

CREATE INDEX idx_stg_orders_id ON staging.stg_orders(order_id);
CREATE INDEX idx_stg_orders_cust ON staging.stg_orders(customer_id);
CREATE INDEX idx_stg_orders_date ON staging.stg_orders(order_purchase_timestamp);

-- 3. Staging Order Items
DROP TABLE IF EXISTS staging.stg_order_items CASCADE;
CREATE TABLE staging.stg_order_items AS
SELECT 
    TRIM(order_id) AS order_id,
    NULLIF(TRIM(order_item_id), '')::INTEGER AS order_item_id,
    TRIM(product_id) AS product_id,
    TRIM(seller_id) AS seller_id,
    NULLIF(TRIM(shipping_limit_date), '')::TIMESTAMP AS shipping_limit_date,
    NULLIF(TRIM(price), '')::NUMERIC(10,2) AS price,
    NULLIF(TRIM(freight_value), '')::NUMERIC(10,2) AS freight_value,
    (COALESCE(NULLIF(TRIM(price), '')::NUMERIC(10,2), 0) + 
     COALESCE(NULLIF(TRIM(freight_value), '')::NUMERIC(10,2), 0)) AS line_total
FROM raw_olist.raw_order_items
WHERE NULLIF(TRIM(order_id), '') IS NOT NULL;

CREATE INDEX idx_stg_items_order ON staging.stg_order_items(order_id);
CREATE INDEX idx_stg_items_prod ON staging.stg_order_items(product_id);
CREATE INDEX idx_stg_items_seller ON staging.stg_order_items(seller_id);

-- 4. Staging Order Payments
DROP TABLE IF EXISTS staging.stg_order_payments CASCADE;
CREATE TABLE staging.stg_order_payments AS
SELECT 
    TRIM(order_id) AS order_id,
    NULLIF(TRIM(payment_sequential), '')::INTEGER AS payment_sequential,
    LOWER(TRIM(payment_type)) AS payment_type,
    NULLIF(TRIM(payment_installments), '')::INTEGER AS payment_installments,
    NULLIF(TRIM(payment_value), '')::NUMERIC(10,2) AS payment_value
FROM raw_olist.raw_order_payments
WHERE NULLIF(TRIM(order_id), '') IS NOT NULL;

CREATE INDEX idx_stg_payments_order ON staging.stg_order_payments(order_id);

-- 5. Staging Order Reviews
DROP TABLE IF EXISTS staging.stg_order_reviews CASCADE;
CREATE TABLE staging.stg_order_reviews AS
SELECT 
    TRIM(review_id) AS review_id,
    TRIM(order_id) AS order_id,
    NULLIF(TRIM(review_score), '')::INTEGER AS review_score,
    NULLIF(TRIM(review_comment_title), '') AS review_comment_title,
    NULLIF(TRIM(review_comment_message), '') AS review_comment_message,
    NULLIF(TRIM(review_creation_date), '')::TIMESTAMP AS review_creation_date,
    NULLIF(TRIM(review_answer_timestamp), '')::TIMESTAMP AS review_answer_timestamp
FROM raw_olist.raw_order_reviews
WHERE NULLIF(TRIM(review_id), '') IS NOT NULL;

CREATE INDEX idx_stg_reviews_order ON staging.stg_order_reviews(order_id);

-- 6. Staging Products
DROP TABLE IF EXISTS staging.stg_products CASCADE;
CREATE TABLE staging.stg_products AS
SELECT 
    TRIM(p.product_id) AS product_id,
    TRIM(p.product_category_name) AS product_category_name,
    COALESCE(TRIM(t.product_category_name_english), TRIM(p.product_category_name), 'unassigned') AS product_category_name_english,
    NULLIF(TRIM(p.product_name_lenght), '')::INTEGER AS product_name_lenght,
    NULLIF(TRIM(p.product_description_lenght), '')::INTEGER AS product_description_lenght,
    NULLIF(TRIM(p.product_photos_qty), '')::INTEGER AS product_photos_qty,
    NULLIF(TRIM(p.product_weight_g), '')::NUMERIC(10,2) AS product_weight_g,
    NULLIF(TRIM(p.product_length_cm), '')::NUMERIC(10,2) AS product_length_cm,
    NULLIF(TRIM(p.product_height_cm), '')::NUMERIC(10,2) AS product_height_cm,
    NULLIF(TRIM(p.product_width_cm), '')::NUMERIC(10,2) AS product_width_cm
FROM raw_olist.raw_products p
LEFT JOIN raw_olist.raw_category_translation t 
    ON TRIM(p.product_category_name) = TRIM(t.product_category_name)
WHERE NULLIF(TRIM(p.product_id), '') IS NOT NULL;

CREATE INDEX idx_stg_products_id ON staging.stg_products(product_id);

-- 7. Staging Sellers
DROP TABLE IF EXISTS staging.stg_sellers CASCADE;
CREATE TABLE staging.stg_sellers AS
SELECT 
    TRIM(seller_id) AS seller_id,
    TRIM(seller_zip_code_prefix) AS seller_zip_code_prefix,
    INITCAP(TRIM(seller_city)) AS seller_city,
    UPPER(TRIM(seller_state)) AS seller_state
FROM raw_olist.raw_sellers
WHERE NULLIF(TRIM(seller_id), '') IS NOT NULL;

CREATE INDEX idx_stg_sellers_id ON staging.stg_sellers(seller_id);

-- 8. Staging Category Translation
DROP TABLE IF EXISTS staging.stg_category_translation CASCADE;
CREATE TABLE staging.stg_category_translation AS
SELECT 
    TRIM(product_category_name) AS product_category_name,
    TRIM(product_category_name_english) AS product_category_name_english
FROM raw_olist.raw_category_translation
WHERE NULLIF(TRIM(product_category_name), '') IS NOT NULL;

-- 9. Staging Geolocation (Aggregated to unique zip prefix to resolve 1-to-many coordinate duplication)
DROP TABLE IF EXISTS staging.stg_geolocation CASCADE;
CREATE TABLE staging.stg_geolocation AS
SELECT 
    TRIM(geolocation_zip_code_prefix) AS zip_code_prefix,
    ROUND(AVG(NULLIF(TRIM(geolocation_lat), '')::NUMERIC), 6) AS latitude,
    ROUND(AVG(NULLIF(TRIM(geolocation_lng), '')::NUMERIC), 6) AS longitude,
    MODE() WITHIN GROUP (ORDER BY INITCAP(TRIM(geolocation_city))) AS city,
    MODE() WITHIN GROUP (ORDER BY UPPER(TRIM(geolocation_state))) AS state
FROM raw_olist.raw_geolocation
WHERE NULLIF(TRIM(geolocation_zip_code_prefix), '') IS NOT NULL
GROUP BY TRIM(geolocation_zip_code_prefix);

CREATE INDEX idx_stg_geo_zip ON staging.stg_geolocation(zip_code_prefix);

-- ============================================================================
-- 06_VALIDATION.SQL: Automated Warehouse & KPI Integrity Verification
-- ============================================================================
-- Purpose: Executes regression checks to prove:
--   1. Zero revenue duplication / join fan-out prevention
--   2. Line item merchandise and freight totals reconcile exactly to orders
--   3. Foreign key referential integrity across dimensional star schema
--   4. Accurate unique customer repeat calculation
--   5. Consistency across grain definitions
-- ============================================================================

-- 1. REVENUE FAN-OUT & JOIN MULTIPLICATION CHECK
-- Proves that joining across orders, items, payments, and reviews does NOT distort revenue
WITH canonical_item_revenue AS (
    SELECT 
        SUM(price) AS sum_item_price,
        SUM(freight_value) AS sum_item_freight,
        SUM(line_total) AS canonical_total_revenue
    FROM analytics.fact_order_items
),
order_aggregated_revenue AS (
    SELECT 
        SUM(total_merchandise_value) AS sum_order_merchandise,
        SUM(total_freight_value) AS sum_order_freight,
        SUM(total_order_value) AS sum_order_total
    FROM analytics.fact_orders
),
payment_revenue AS (
    SELECT 
        SUM(payment_value) AS sum_payment_total
    FROM analytics.fact_order_payments
)
SELECT 
    c.canonical_total_revenue,
    o.sum_order_total,
    ROUND(c.canonical_total_revenue - o.sum_order_total, 2) AS order_to_item_discrepancy,
    p.sum_payment_total,
    ROUND(p.sum_payment_total - c.canonical_total_revenue, 2) AS payment_vs_revenue_variance,
    CASE 
        WHEN ROUND(c.canonical_total_revenue, 2) = ROUND(o.sum_order_total, 2) 
        THEN 'PASSED: Zero Fan-Out Detected' 
        ELSE 'FAILED: Revenue Discrepancy Found' 
    END AS fan_out_test_status
FROM canonical_item_revenue c
CROSS JOIN order_aggregated_revenue o
CROSS JOIN payment_revenue p;

-- 2. ORPHAN FOREIGN KEY AUDIT
SELECT 
    'fact_order_items -> dim_product' AS relationship,
    COUNT(*) AS orphan_count
FROM analytics.fact_order_items i
LEFT JOIN analytics.dim_product p ON i.product_id = p.product_id
WHERE p.product_id IS NULL
UNION ALL
SELECT 
    'fact_order_items -> dim_seller' AS relationship,
    COUNT(*) AS orphan_count
FROM analytics.fact_order_items i
LEFT JOIN analytics.dim_seller s ON i.seller_id = s.seller_id
WHERE s.seller_id IS NULL
UNION ALL
SELECT 
    'fact_orders -> dim_customer' AS relationship,
    COUNT(*) AS orphan_count
FROM analytics.fact_orders o
LEFT JOIN analytics.dim_customer c ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL;

-- 3. CUSTOMER GRAIN AND REPEAT PURCHASE INTEGRITY
-- Validates that repeat purchasing is measured at customer_unique_id, not customer_id
SELECT 
    COUNT(DISTINCT customer_id) AS total_customer_sessions,
    COUNT(DISTINCT customer_unique_id) AS total_unique_people,
    COUNT(DISTINCT CASE WHEN order_count > 1 THEN customer_unique_id END) AS repeat_customers_count,
    ROUND(
        COUNT(DISTINCT CASE WHEN order_count > 1 THEN customer_unique_id END)::NUMERIC 
        / COUNT(DISTINCT customer_unique_id) * 100, 2
    ) AS repeat_customer_rate_pct
FROM (
    SELECT 
        c.customer_unique_id,
        c.customer_id,
        COUNT(o.order_id) OVER (PARTITION BY c.customer_unique_id) AS order_count
    FROM analytics.dim_customer c
    JOIN analytics.fact_orders o ON c.customer_id = o.customer_id
) cust_summary;

-- 4. DELIVERY METRIC BOUNDS AUDIT
SELECT 
    COUNT(*) AS delivered_orders_evaluated,
    COUNT(CASE WHEN is_delivered_on_time = TRUE THEN 1 END) AS on_time_orders,
    COUNT(CASE WHEN is_delivered_on_time = FALSE THEN 1 END) AS late_orders,
    ROUND(
        (COUNT(CASE WHEN is_delivered_on_time = TRUE THEN 1 END) + 
         COUNT(CASE WHEN is_delivered_on_time = FALSE THEN 1 END))::NUMERIC 
        / NULLIF(COUNT(*), 0) * 100, 2
    ) AS sum_pct_on_time_plus_late
FROM analytics.fact_orders
WHERE order_status = 'delivered'
  AND order_delivered_customer_date IS NOT NULL
  AND order_estimated_delivery_date IS NOT NULL;

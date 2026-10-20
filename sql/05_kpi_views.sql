-- ============================================================================
-- 05_KPI_VIEWS.SQL: Governed Analytical KPI Views
-- ============================================================================
-- Purpose: Provides canonical, standardized business metric definitions across
-- Executive, Monthly, Product Category, Customer RFM, Logistics, and Seller dimensions.
-- All views strictly avoid join fan-out and reference explicit table grains.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS analytics;

-- 1. Executive Headline KPIs
-- Single-row summary answering core executive performance questions
CREATE OR REPLACE VIEW analytics.vw_executive_kpis AS
WITH order_summary AS (
    SELECT 
        COUNT(order_id) AS total_orders,
        COUNT(CASE WHEN order_status = 'delivered' THEN 1 END) AS delivered_orders,
        ROUND(COUNT(CASE WHEN order_status = 'delivered' THEN 1 END)::NUMERIC / NULLIF(COUNT(order_id), 0) * 100, 2) AS delivered_order_rate_pct,
        ROUND(AVG(CASE WHEN order_status = 'delivered' THEN delivery_days END)::NUMERIC, 2) AS avg_delivery_days,
        ROUND(COUNT(CASE WHEN order_status = 'delivered' AND is_delivered_on_time = TRUE THEN 1 END)::NUMERIC 
            / NULLIF(COUNT(CASE WHEN order_status = 'delivered' AND is_delivered_on_time IS NOT NULL THEN 1 END), 0) * 100, 2) AS on_time_delivery_rate_pct
    FROM analytics.fact_orders
),
item_summary AS (
    SELECT 
        SUM(price) AS total_merchandise_revenue,
        SUM(freight_value) AS total_freight_revenue,
        SUM(line_total) AS total_revenue,
        COUNT(order_item_key) AS total_items_sold,
        ROUND(AVG(price), 2) AS avg_item_price,
        ROUND(AVG(freight_value), 2) AS avg_freight_value
    FROM analytics.fact_order_items
),
customer_summary AS (
    SELECT 
        COUNT(DISTINCT c.customer_unique_id) AS total_unique_customers,
        COUNT(DISTINCT c.customer_id) AS total_customer_sessions
    FROM analytics.dim_customer c
    JOIN analytics.fact_orders o ON c.customer_id = o.customer_id
),
payment_summary AS (
    SELECT 
        SUM(payment_value) AS total_payment_value
    FROM analytics.fact_order_payments
),
review_summary AS (
    SELECT 
        ROUND(AVG(review_score)::NUMERIC, 2) AS avg_review_score,
        COUNT(review_id) AS total_reviews_count
    FROM analytics.fact_order_reviews
)
SELECT 
    i.total_revenue,
    i.total_merchandise_revenue,
    i.total_freight_revenue,
    p.total_payment_value,
    o.total_orders,
    o.delivered_orders,
    o.delivered_order_rate_pct,
    ROUND(i.total_revenue / NULLIF(o.total_orders, 0), 2) AS average_order_value,
    c.total_unique_customers,
    r.avg_review_score,
    r.total_reviews_count,
    o.avg_delivery_days,
    o.on_time_delivery_rate_pct,
    i.avg_freight_value,
    i.total_items_sold
FROM order_summary o
CROSS JOIN item_summary i
CROSS JOIN customer_summary c
CROSS JOIN payment_summary p
CROSS JOIN review_summary r;

-- 2. Monthly Sales Performance & MoM Growth
CREATE OR REPLACE VIEW analytics.vw_monthly_sales_performance AS
WITH monthly_metrics AS (
    SELECT 
        TO_CHAR(o.order_purchase_timestamp, 'YYYY-MM') AS month_year,
        DATE_TRUNC('month', o.order_purchase_timestamp)::DATE AS month_date,
        COUNT(DISTINCT o.order_id) AS order_count,
        COUNT(DISTINCT o.customer_id) AS order_sessions,
        SUM(i.line_total) AS monthly_revenue,
        SUM(i.price) AS merchandise_revenue,
        SUM(i.freight_value) AS freight_revenue,
        COUNT(i.order_item_key) AS items_sold,
        ROUND(AVG(CASE WHEN o.order_status = 'delivered' THEN o.delivery_days END)::NUMERIC, 2) AS avg_delivery_days,
        ROUND(COUNT(CASE WHEN o.order_status = 'delivered' AND o.is_delivered_on_time = TRUE THEN 1 END)::NUMERIC
            / NULLIF(COUNT(CASE WHEN o.order_status = 'delivered' AND o.is_delivered_on_time IS NOT NULL THEN 1 END), 0) * 100, 2) AS on_time_rate_pct
    FROM analytics.fact_orders o
    LEFT JOIN analytics.fact_order_items i ON o.order_id = i.order_id
    WHERE o.order_purchase_timestamp IS NOT NULL
    GROUP BY TO_CHAR(o.order_purchase_timestamp, 'YYYY-MM'), DATE_TRUNC('month', o.order_purchase_timestamp)::DATE
)
SELECT 
    month_year,
    month_date,
    order_count,
    ROUND(COALESCE(monthly_revenue, 0.00), 2) AS monthly_revenue,
    ROUND(COALESCE(merchandise_revenue, 0.00), 2) AS merchandise_revenue,
    ROUND(COALESCE(freight_revenue, 0.00), 2) AS freight_revenue,
    items_sold,
    ROUND(COALESCE(monthly_revenue, 0.00) / NULLIF(order_count, 0), 2) AS aov,
    avg_delivery_days,
    on_time_rate_pct,
    LAG(ROUND(COALESCE(monthly_revenue, 0.00), 2), 1) OVER (ORDER BY month_date) AS prev_month_revenue,
    ROUND(
        (monthly_revenue - LAG(monthly_revenue, 1) OVER (ORDER BY month_date)) 
        / NULLIF(LAG(monthly_revenue, 1) OVER (ORDER BY month_date), 0) * 100, 2
    ) AS mom_revenue_growth_pct
FROM monthly_metrics
ORDER BY month_date;

-- 3. Product Category Contribution & Analytics
CREATE OR REPLACE VIEW analytics.vw_category_performance AS
SELECT 
    COALESCE(p.product_category_name_english, 'Unassigned') AS category_name,
    COUNT(DISTINCT i.order_id) AS distinct_orders_count,
    COUNT(i.order_item_key) AS total_items_sold,
    ROUND(SUM(i.line_total), 2) AS total_category_revenue,
    ROUND(SUM(i.price), 2) AS merchandise_revenue,
    ROUND(SUM(i.freight_value), 2) AS freight_revenue,
    ROUND(AVG(i.price), 2) AS avg_item_price,
    ROUND(AVG(i.freight_value), 2) AS avg_item_freight,
    ROUND(SUM(i.line_total) / NULLIF(SUM(SUM(i.line_total)) OVER (), 0) * 100, 2) AS revenue_share_pct
FROM analytics.fact_order_items i
JOIN analytics.dim_product p ON i.product_id = p.product_id
GROUP BY COALESCE(p.product_category_name_english, 'Unassigned')
ORDER BY total_category_revenue DESC;

-- 4. Customer RFM Segmentation & Behavior
CREATE OR REPLACE VIEW analytics.vw_customer_rfm_segments AS
WITH customer_orders AS (
    SELECT 
        c.customer_unique_id,
        MIN(o.order_purchase_timestamp) AS first_order_timestamp,
        MAX(o.order_purchase_timestamp) AS last_order_timestamp,
        COUNT(DISTINCT o.order_id) AS total_orders,
        SUM(o.total_order_value) AS monetary_value
    FROM analytics.dim_customer c
    JOIN analytics.fact_orders o ON c.customer_id = o.customer_id
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY c.customer_unique_id
),
rfm_raw AS (
    SELECT 
        customer_unique_id,
        first_order_timestamp,
        last_order_timestamp,
        total_orders,
        monetary_value,
        -- Reference date benchmark: dataset maximum date (2018-10-17)
        EXTRACT(DAY FROM ('2018-10-17'::TIMESTAMP - last_order_timestamp))::INTEGER AS recency_days,
        total_orders AS frequency,
        ROUND(monetary_value, 2) AS monetary
    FROM customer_orders
),
rfm_scores AS (
    SELECT 
        customer_unique_id,
        recency_days,
        frequency,
        monetary,
        NTILE(4) OVER (ORDER BY recency_days DESC) AS r_score,
        CASE WHEN frequency = 1 THEN 1 ELSE 4 END AS f_score,
        NTILE(4) OVER (ORDER BY monetary ASC) AS m_score
    FROM rfm_raw
)
SELECT 
    customer_unique_id,
    recency_days,
    frequency,
    monetary,
    r_score,
    f_score,
    m_score,
    (r_score::TEXT || f_score::TEXT || m_score::TEXT) AS rfm_cell,
    CASE 
        WHEN frequency > 1 AND r_score >= 3 AND m_score >= 3 THEN 'Champions / VIP'
        WHEN frequency > 1 AND r_score >= 2 THEN 'Loyal Customers'
        WHEN frequency = 1 AND r_score >= 3 AND m_score >= 3 THEN 'High-Value Recent'
        WHEN frequency = 1 AND r_score >= 3 THEN 'New / Recent Active'
        WHEN frequency > 1 AND r_score = 1 THEN 'At Risk Repeaters'
        WHEN frequency = 1 AND r_score <= 2 AND m_score >= 3 THEN 'High-Value Lapsed'
        ELSE 'One-Time Low Engagement'
    END AS customer_segment
FROM rfm_scores;

-- 5. Delivery, Logistics & Customer Satisfaction Performance
CREATE OR REPLACE VIEW analytics.vw_delivery_logistics_performance AS
SELECT 
    c.customer_state,
    COUNT(o.order_id) AS total_orders,
    COUNT(CASE WHEN o.order_status = 'delivered' THEN 1 END) AS delivered_orders,
    ROUND(AVG(CASE WHEN o.order_status = 'delivered' THEN o.delivery_days END)::NUMERIC, 2) AS avg_delivery_days,
    ROUND(COUNT(CASE WHEN o.order_status = 'delivered' AND o.is_delivered_on_time = TRUE THEN 1 END)::NUMERIC
        / NULLIF(COUNT(CASE WHEN o.order_status = 'delivered' AND o.is_delivered_on_time IS NOT NULL THEN 1 END), 0) * 100, 2) AS on_time_delivery_rate_pct,
    ROUND(COUNT(CASE WHEN o.order_status = 'delivered' AND o.is_delivered_on_time = FALSE THEN 1 END)::NUMERIC
        / NULLIF(COUNT(CASE WHEN o.order_status = 'delivered' AND o.is_delivered_on_time IS NOT NULL THEN 1 END), 0) * 100, 2) AS late_delivery_rate_pct,
    ROUND(AVG(r.review_score)::NUMERIC, 2) AS avg_review_score,
    ROUND(SUM(o.total_freight_value) / NULLIF(COUNT(o.order_id), 0), 2) AS avg_freight_per_order
FROM analytics.fact_orders o
JOIN analytics.dim_customer c ON o.customer_id = c.customer_id
LEFT JOIN analytics.fact_order_reviews r ON o.order_id = r.order_id
GROUP BY c.customer_state
ORDER BY total_orders DESC;

-- 6. Seller Performance & Concentration
CREATE OR REPLACE VIEW analytics.vw_seller_performance AS
SELECT 
    s.seller_id,
    s.seller_city,
    s.seller_state,
    COUNT(DISTINCT i.order_id) AS total_orders_fulfilled,
    COUNT(i.order_item_key) AS total_items_sold,
    ROUND(SUM(i.line_total), 2) AS total_revenue_generated,
    ROUND(SUM(i.price), 2) AS merchandise_revenue,
    ROUND(SUM(i.freight_value), 2) AS freight_revenue,
    ROUND(AVG(i.price), 2) AS avg_item_price,
    ROUND(SUM(i.line_total) / NULLIF(SUM(SUM(i.line_total)) OVER (), 0) * 100, 4) AS market_revenue_share_pct
FROM analytics.fact_order_items i
JOIN analytics.dim_seller s ON i.seller_id = s.seller_id
GROUP BY s.seller_id, s.seller_city, s.seller_state
ORDER BY total_revenue_generated DESC;

# AI Governed Analytics: Schema & Business Context

**Target Audience:** AI SQL Generation Agent & Analytics Solution Architect  
**Security Classification:** Strict Zero-Trust Governed Analytics  
**Access Model:** Read-Only SELECT permissions restricted solely to approved `analytics.vw_*` views.

---

## 1. Zero-Trust Security & Governance Policies

1. **Approved Objects Only:**
   - The AI Assistant is **STRICTLY PROHIBITED** from querying raw schemas (`raw_olist.*`), staging tables (`staging.*`), physical fact/dimension tables (`analytics.fact_*`, `analytics.dim_*`), or system catalogs (`pg_catalog.*`, `information_schema.*`).
   - The AI Assistant is authorized to query **ONLY** the 6 governed analytical views defined below.
2. **Single Read-Only SELECT Enforcement:**
   - Every generated query must consist of **exactly one** `SELECT` statement.
   - Multi-statement execution (semicolons `;`), comments (`--`, `/*`), transaction blocks, and all DDL/DML statements (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `EXECUTE`) are automatically rejected by the SQL AST Validator.
3. **Guardrails & Execution Bounds:**
   - Execution timeout: **5,000 milliseconds**.
   - Maximum result rows: **100 rows** (a `LIMIT 100` clause is mandatory; if absent, the validator automatically appends it).
4. **No Metric Re-invention:**
   - Revenue, delivery rates, review scores, and repeat rates must be sourced from the approved view columns. Never attempt ad-hoc joins across items, reviews, or payments that could cause fan-out.

---

## 2. Approved Analytical Views Catalog

### View 1: `analytics.vw_executive_kpis`
Single-row executive snapshot of overall platform health.
- `total_revenue`: Gross e-commerce turnover (merchandise + freight) ($15.84M).
- `total_merchandise_revenue`: Total product item value ($13.59M).
- `total_freight_revenue`: Total shipping charges ($2.25M).
- `total_payment_value`: Gross payments captured across payment instruments ($16.01M).
- `total_orders`: Total distinct orders processed (99,441).
- `delivered_orders`: Total orders fulfilled to doorstep (96,478).
- `delivered_order_rate_pct`: Percentage of orders delivered successfully (97.02%).
- `average_order_value`: Average order gross spend ($159.33).
- `total_unique_customers`: Unique human buyers (96,096).
- `avg_review_score`: Mean customer satisfaction rating (4.09).
- `total_reviews_count`: Total review feedbacks collected (99,224).
- `avg_delivery_days`: Average delivery transit time in days (12.5 days).
- `on_time_delivery_rate_pct`: Percentage of fulfilled orders arriving on or before estimated date (91.89%).
- `avg_freight_value`: Mean shipping cost per item ($19.99).
- `total_items_sold`: Total line items dispatched (112,650).

### View 2: `analytics.vw_monthly_sales_performance`
Granular historical monthly trajectory (25 calendar months from 2016-09 to 2018-10).
- `month_year`: Formatted calendar month (`YYYY-MM`).
- `month_date`: First day of month (`DATE`).
- `order_count`: Distinct orders placed in month.
- `monthly_revenue`: Gross revenue ($) in month.
- `merchandise_revenue`: Product price revenue ($).
- `freight_revenue`: Shipping fee revenue ($).
- `items_sold`: Line items count.
- `aov`: Average order value in month ($).
- `avg_delivery_days`: Mean transit days for orders in month.
- `on_time_rate_pct`: On-time delivery percentage in month.
- `prev_month_revenue`: Prior month gross revenue ($).
- `mom_revenue_growth_pct`: Month-over-month revenue percentage change.

### View 3: `analytics.vw_category_performance`
Ranked product category commercial metrics (73 unique merchandise categories).
- `category_name`: English translated product category name.
- `distinct_orders_count`: Unique orders containing at least one item from category.
- `total_items_sold`: Units sold in category.
- `total_category_revenue`: Gross revenue ($) generated.
- `merchandise_revenue`: Product price total ($).
- `freight_revenue`: Shipping fee total ($).
- `avg_item_price`: Average unit price in category ($).
- `avg_item_freight`: Average freight cost in category ($).
- `revenue_share_pct`: Percentage share of total platform gross revenue.

### View 4: `analytics.vw_customer_rfm_segments`
Customer lifecycle classification across 96,096 unique buyers.
- `customer_unique_id`: Unique persistent human buyer ID.
- `recency_days`: Days elapsed between customer's last order and dataset cutoff.
- `frequency`: Total lifetime orders placed.
- `monetary`: Total lifetime order spend ($).
- `r_score`: Recency score (1 to 4).
- `f_score`: Frequency score (1 or 4).
- `m_score`: Monetary spend score (1 to 4).
- `rfm_cell`: Composite 3-digit score string (e.g. `'444'`).
- `customer_segment`: Governed segment name (`'Champions / VIP'`, `'Loyal Customers'`, `'High-Value Recent'`, `'New / Recent Active'`, `'High-Value Lapsed'`, `'At Risk Repeaters'`, `'One-Time Low Engagement'`).

### View 5: `analytics.vw_delivery_logistics_performance`
Regional logistics efficiency across Brazil's 27 states.
- `customer_state`: 2-letter Brazilian state code (e.g. `'SP'`, `'RJ'`, `'MG'`).
- `total_orders`: Total orders originating from state.
- `delivered_orders`: Total orders fulfilled.
- `avg_delivery_days`: Mean calendar transit days.
- `on_time_delivery_rate_pct`: Percentage of orders arriving on/before deadline.
- `late_delivery_rate_pct`: Percentage of orders arriving after deadline.
- `avg_review_score`: Mean customer satisfaction score in state.
- `avg_freight_per_order`: Average freight cost per order in state ($).

### View 6: `analytics.vw_seller_performance`
Merchant distribution and volume metrics (3,095 sellers).
- `seller_id`: Unique merchant identifier.
- `seller_city`: Merchant city.
- `seller_state`: Merchant state code.
- `total_orders_fulfilled`: Orders processed by merchant.
- `total_items_sold`: Total items dispatched.
- `total_revenue_generated`: Gross revenue earned ($).
- `merchandise_revenue`: Merchandise sales ($).
- `freight_revenue`: Freight revenue ($).
- `avg_item_price`: Average price of items sold ($).
- `market_revenue_share_pct`: Percentage of total platform sales.

"""
Automated Financial and Join Fan-Out Prevention Tests.
Verifies mathematical integrity between line items and orders, proving zero fan-out.
"""

import os
import pytest
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "2003")
DB_NAME = os.getenv("DB_NAME", "olist_dw")

@pytest.fixture(scope="module")
def db_conn():
    engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    with engine.connect() as conn:
        yield conn

def test_zero_revenue_fan_out(db_conn):
    """Proves line-item total matches order pre-aggregated total exactly ($0.00 variance)."""
    query = text("""
        SELECT 
            (SELECT SUM(line_total) FROM analytics.fact_order_items) AS items_total,
            (SELECT SUM(total_order_value) FROM analytics.fact_orders) AS orders_total;
    """)
    res = db_conn.execute(query).mappings().first()
    items_total = float(res['items_total'])
    orders_total = float(res['orders_total'])
    
    assert items_total > 15_000_000.0, "Revenue should exceed $15M"
    assert round(items_total, 2) == round(orders_total, 2), f"Fan-out detected! Items: {items_total}, Orders: {orders_total}"

def test_merchandise_plus_freight_equals_total(db_conn):
    """Proves price + freight = line_total across fact_order_items."""
    query = text("""
        SELECT 
            SUM(price) AS sum_price,
            SUM(freight_value) AS sum_freight,
            SUM(line_total) AS sum_line_total
        FROM analytics.fact_order_items;
    """)
    res = db_conn.execute(query).mappings().first()
    price = float(res['sum_price'])
    freight = float(res['sum_freight'])
    total = float(res['sum_line_total'])
    
    assert round(price + freight, 2) == round(total, 2)

def test_referential_integrity_no_orphans(db_conn):
    """Proves foreign key relationships have zero orphan records."""
    query = text("""
        SELECT 
            (SELECT COUNT(*) FROM analytics.fact_order_items i LEFT JOIN analytics.dim_product p ON i.product_id = p.product_id WHERE p.product_id IS NULL) AS orphan_prods,
            (SELECT COUNT(*) FROM analytics.fact_order_items i LEFT JOIN analytics.dim_seller s ON i.seller_id = s.seller_id WHERE s.seller_id IS NULL) AS orphan_sellers,
            (SELECT COUNT(*) FROM analytics.fact_orders o LEFT JOIN analytics.dim_customer c ON o.customer_id = c.customer_id WHERE c.customer_id IS NULL) AS orphan_custs;
    """)
    res = db_conn.execute(query).mappings().first()
    assert res['orphan_prods'] == 0
    assert res['orphan_sellers'] == 0
    assert res['orphan_custs'] == 0

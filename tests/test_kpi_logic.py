"""
Automated KPI Logic and Analytical View Tests.
Verifies business calculations, customer retention denominator integrity, and date logic.
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

@pytest.fixture(scope="function")
def db_conn():
    engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    with engine.connect() as conn:
        yield conn

def test_executive_kpi_view_results(db_conn):
    res = db_conn.execute(text("SELECT * FROM analytics.vw_executive_kpis;")).mappings().first()
    assert res is not None
    assert float(res['total_revenue']) >= 15_800_000.0
    assert int(res['total_orders']) == 99441
    assert float(res['avg_review_score']) >= 4.0
    assert float(res['on_time_delivery_rate_pct']) >= 90.0

def test_customer_repeat_rate_logic(db_conn):
    """Verifies repeat rate is calculated against unique people, not transaction tokens."""
    query = text("""
        WITH cust_orders AS (
            SELECT 
                c.customer_unique_id,
                COUNT(o.order_id) AS order_count
            FROM analytics.dim_customer c
            JOIN analytics.fact_orders o ON c.customer_id = o.customer_id
            GROUP BY c.customer_unique_id
        )
        SELECT 
            (SELECT COUNT(*) FROM analytics.dim_customer) AS total_customer_sessions,
            COUNT(customer_unique_id) AS total_unique_people,
            COUNT(CASE WHEN order_count > 1 THEN 1 END) AS repeat_customers_count,
            ROUND(COUNT(CASE WHEN order_count > 1 THEN 1 END)::NUMERIC / COUNT(customer_unique_id) * 100, 2) AS repeat_customer_rate_pct
        FROM cust_orders;
    """)
    res = db_conn.execute(query).mappings().first()
    assert res['total_customer_sessions'] == 99441
    assert res['total_unique_people'] == 96096
    assert res['repeat_customers_count'] == 2997
    assert float(res['repeat_customer_rate_pct']) == 3.12

def test_delivery_bounds(db_conn):
    """Verifies on-time rate + late rate equals 100% for delivered orders."""
    query = text("""
        SELECT 
            on_time_delivery_rate_pct,
            late_delivery_rate_pct
        FROM analytics.vw_delivery_logistics_performance;
    """)
    rows = db_conn.execute(query).mappings().fetchall()
    assert len(rows) > 0
    for r in rows:
        on_time = float(r['on_time_delivery_rate_pct'] or 0)
        late = float(r['late_delivery_rate_pct'] or 0)
        assert round(on_time + late, 1) == 100.0, f"Delivery rates do not sum to 100%: {on_time} + {late}"

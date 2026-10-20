"""
Financial and Row-Count Reconciliation Audit Pipeline for Olist E-Commerce.
Performs cross-layer mathematical reconciliation between Raw CSVs, PostgreSQL Staging,
and the Analytical Dimensional Warehouse.
"""

import os
import sys
import logging
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("reconciliation")

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "2003")
DB_NAME = os.getenv("DB_NAME", "olist_dw")

RAW_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

def get_engine():
    connection_url = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(connection_url)

def run_reconciliation():
    logger.info("=== Starting Cross-Layer Reconciliation Audit ===")
    
    # 1. Row counts from CSV
    csv_counts = {}
    files = {
        "orders": "olist_orders_dataset.csv",
        "order_items": "olist_order_items_dataset.csv",
        "payments": "olist_order_payments_dataset.csv",
        "reviews": "olist_order_reviews_dataset.csv",
        "customers": "olist_customers_dataset.csv",
        "products": "olist_products_dataset.csv",
        "sellers": "olist_sellers_dataset.csv"
    }
    for k, v in files.items():
        fpath = RAW_DATA_DIR / v
        if fpath.exists():
            df = pd.read_csv(fpath)
            csv_counts[k] = len(df)
        else:
            csv_counts[k] = None

    # 2. Check Database counts if DB available
    db_results = {}
    try:
        engine = get_engine()
        with engine.connect() as conn:
            # Staging counts
            for t in ["stg_orders", "stg_order_items", "stg_order_payments", "stg_order_reviews", "stg_customers", "stg_products", "stg_sellers"]:
                try:
                    res = conn.execute(text(f"SELECT COUNT(*) FROM staging.{t};")).scalar()
                    clean_key = t.replace("stg_order_", "").replace("stg_", "")
                    db_results[clean_key] = res
                except Exception:
                    db_results[t] = None
                    
            # Financial sums
            try:
                revenue_res = conn.execute(text("""
                    SELECT 
                        SUM(line_total) AS items_total_revenue,
                        SUM(price) AS items_merchandise,
                        SUM(freight_value) AS items_freight
                    FROM analytics.fact_order_items;
                """)).mappings().first()
                
                orders_res = conn.execute(text("""
                    SELECT 
                        SUM(total_order_value) AS orders_total_revenue,
                        COUNT(order_id) AS total_orders_count
                    FROM analytics.fact_orders;
                """)).mappings().first()
                
                pay_res = conn.execute(text("""
                    SELECT SUM(payment_value) AS total_payment_value FROM analytics.fact_order_payments;
                """)).mappings().first()
                
                cust_res = conn.execute(text("""
                    SELECT 
                        COUNT(DISTINCT customer_id) AS session_count,
                        COUNT(DISTINCT customer_unique_id) AS unique_people_count
                    FROM analytics.dim_customer;
                """)).mappings().first()
            except Exception as e:
                logger.warning(f"Could not query analytical tables (may need building first): {e}")
                revenue_res, orders_res, pay_res, cust_res = None, None, None, None
                
    except Exception as e:
        logger.error(f"Database connection error during reconciliation: {e}")
        revenue_res, orders_res, pay_res, cust_res = None, None, None, None

    # Print Reconciliation Table
    logger.info("\n" + "="*80)
    logger.info("RECONCILIATION SUMMARY MATRIX")
    logger.info("="*80)
    for entity, count in csv_counts.items():
        stg_count = db_results.get(entity)
        logger.info(f"Entity: {entity:<15} | Raw CSV: {str(count):<10} | Staging: {str(stg_count):<10}")

    if revenue_res and orders_res:
        items_rev = float(revenue_res['items_total_revenue'] or 0)
        orders_rev = float(orders_res['orders_total_revenue'] or 0)
        pay_total = float(pay_res['total_payment_value'] or 0) if pay_res else 0.0
        discrepancy = round(items_rev - orders_rev, 2)
        
        logger.info("\n" + "-"*80)
        logger.info("FINANCIAL INTEGRITY & ZERO FAN-OUT PROOF")
        logger.info(f"Canonical Line Items Revenue: ${items_rev:,.2f}")
        logger.info(f"Aggregated Fact Orders Revenue: ${orders_rev:,.2f}")
        logger.info(f"Items vs Orders Discrepancy: ${discrepancy:,.2f}")
        logger.info(f"Status: {'PASSED (Zero Fan-Out)' if discrepancy == 0.0 else 'FAILED'}")
        logger.info(f"Total Recorded Payments: ${pay_total:,.2f}")
        logger.info(f"Payment vs Revenue Variance: ${pay_total - items_rev:,.2f} (Attributable to vouchers/installments)")
        logger.info("-"*80)

    if cust_res:
        sessions = cust_res['session_count']
        people = cust_res['unique_people_count']
        logger.info(f"Customer Sessions (customer_id): {sessions:,}")
        logger.info(f"Unique Customers (customer_unique_id): {people:,}")
        logger.info(f"Repeat Customer Base: {sessions - people:,} repeated order events")
        logger.info("-"*80)

if __name__ == "__main__":
    run_reconciliation()

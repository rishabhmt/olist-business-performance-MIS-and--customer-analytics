"""
Data Quality Profiling and Audit Pipeline for Olist E-Commerce.
Performs automated data quality checks across raw/staging tables and generates data_quality_report.csv.
"""

import os
import sys
import logging
from pathlib import Path
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("data_quality")

RAW_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REPORT_OUTPUT_PATH = DATA_DIR / "data_quality_report.csv"

def run_data_quality_audit():
    logger.info("=== Starting Data Quality Audit Pipeline ===")
    
    findings = []
    
    # 1. Check Orders Dataset
    orders_file = RAW_DATA_DIR / "olist_orders_dataset.csv"
    if orders_file.exists():
        df_orders = pd.read_csv(orders_file)
        n_orders = len(df_orders)
        logger.info(f"Auditing orders dataset ({n_orders:,} rows)...")
        
        # Check: Primary key uniqueness
        dup_orders = df_orders['order_id'].duplicated().sum()
        findings.append({
            "check_id": "DQ-ORD-01",
            "table": "orders",
            "column_or_rule": "order_id",
            "issue_detected": "Duplicate primary key (order_id)",
            "affected_records": int(dup_orders),
            "severity": "CRITICAL" if dup_orders > 0 else "INFO",
            "recommended_action": "Deduplicate by keeping latest record if duplicates found" if dup_orders > 0 else "None; PK is strictly unique",
            "validation_status": "PASSED" if dup_orders == 0 else "FAILED"
        })
        
        # Check: Missing customer_id
        null_cust = df_orders['customer_id'].isnull().sum()
        findings.append({
            "check_id": "DQ-ORD-02",
            "table": "orders",
            "column_or_rule": "customer_id",
            "issue_detected": "Missing foreign key customer_id",
            "affected_records": int(null_cust),
            "severity": "CRITICAL" if null_cust > 0 else "INFO",
            "recommended_action": "Investigate transaction logs; quarantine orders without customer",
            "validation_status": "PASSED" if null_cust == 0 else "FAILED"
        })
        
        # Check: Missing delivered_customer_date for 'delivered' status
        delivered_mask = df_orders['order_status'] == 'delivered'
        missing_delivery_date = (delivered_mask & df_orders['order_delivered_customer_date'].isnull()).sum()
        findings.append({
            "check_id": "DQ-ORD-03",
            "table": "orders",
            "column_or_rule": "order_delivered_customer_date",
            "issue_detected": "Delivered orders lacking actual delivery timestamp",
            "affected_records": int(missing_delivery_date),
            "severity": "HIGH" if missing_delivery_date > 0 else "INFO",
            "recommended_action": "Exclude from delivery duration calculations; retain in order count",
            "validation_status": "WARNING" if missing_delivery_date > 0 else "PASSED"
        })
        
        # Check: Inconsistent timestamps (delivered before purchase)
        df_orders['purchase_dt'] = pd.to_datetime(df_orders['order_purchase_timestamp'], errors='coerce')
        df_orders['delivered_dt'] = pd.to_datetime(df_orders['order_delivered_customer_date'], errors='coerce')
        retrograde_delivery = (df_orders['delivered_dt'] < df_orders['purchase_dt']).sum()
        findings.append({
            "check_id": "DQ-ORD-04",
            "table": "orders",
            "column_or_rule": "order_purchase_timestamp vs order_delivered_customer_date",
            "issue_detected": "Delivery date precedes purchase date (temporal inconsistency)",
            "affected_records": int(retrograde_delivery),
            "severity": "CRITICAL" if retrograde_delivery > 0 else "INFO",
            "recommended_action": "Flag as temporal anomaly; set delivery duration to NULL",
            "validation_status": "PASSED" if retrograde_delivery == 0 else "FAILED"
        })
        
        # Check: Unexpected order statuses
        valid_statuses = {'delivered', 'shipped', 'canceled', 'invoiced', 'processing', 'unavailable', 'created', 'approved'}
        unexpected_statuses = (~df_orders['order_status'].isin(valid_statuses)).sum()
        findings.append({
            "check_id": "DQ-ORD-05",
            "table": "orders",
            "column_or_rule": "order_status",
            "issue_detected": "Non-standard categorical order status values",
            "affected_records": int(unexpected_statuses),
            "severity": "MEDIUM" if unexpected_statuses > 0 else "INFO",
            "recommended_action": "Map to standard lifecycle taxonomy",
            "validation_status": "PASSED" if unexpected_statuses == 0 else "WARNING"
        })
    else:
        logger.warning(f"File not found: {orders_file}")

    # 2. Check Order Items Dataset
    items_file = RAW_DATA_DIR / "olist_order_items_dataset.csv"
    if items_file.exists():
        df_items = pd.read_csv(items_file)
        n_items = len(df_items)
        logger.info(f"Auditing order items dataset ({n_items:,} rows)...")
        
        # Check: Composite primary key uniqueness (order_id + order_item_id)
        dup_items = df_items.duplicated(subset=['order_id', 'order_item_id']).sum()
        findings.append({
            "check_id": "DQ-ITM-01",
            "table": "order_items",
            "column_or_rule": "order_id + order_item_id",
            "issue_detected": "Duplicate line item key within order",
            "affected_records": int(dup_items),
            "severity": "CRITICAL" if dup_items > 0 else "INFO",
            "recommended_action": "Verify item sequences; deduplicate identical lines",
            "validation_status": "PASSED" if dup_items == 0 else "FAILED"
        })
        
        # Check: Negative or zero price
        invalid_price = (df_items['price'] <= 0).sum()
        findings.append({
            "check_id": "DQ-ITM-02",
            "table": "order_items",
            "column_or_rule": "price",
            "issue_detected": "Zero or negative item price",
            "affected_records": int(invalid_price),
            "severity": "HIGH" if invalid_price > 0 else "INFO",
            "recommended_action": "Audit for promotional/free giveaway items vs pricing errors",
            "validation_status": "PASSED" if invalid_price == 0 else "WARNING"
        })
        
        # Check: Negative freight value
        negative_freight = (df_items['freight_value'] < 0).sum()
        findings.append({
            "check_id": "DQ-ITM-03",
            "table": "order_items",
            "column_or_rule": "freight_value",
            "issue_detected": "Negative shipping cost",
            "affected_records": int(negative_freight),
            "severity": "CRITICAL" if negative_freight > 0 else "INFO",
            "recommended_action": "Correct negative values to 0.00",
            "validation_status": "PASSED" if negative_freight == 0 else "FAILED"
        })
        
        # Check: Orphan order_id in order_items
        if 'df_orders' in locals():
            orphan_items = (~df_items['order_id'].isin(df_orders['order_id'])).sum()
            findings.append({
                "check_id": "DQ-ITM-04",
                "table": "order_items",
                "column_or_rule": "order_id -> orders.order_id",
                "issue_detected": "Orphan line items referencing non-existent order header",
                "affected_records": int(orphan_items),
                "severity": "CRITICAL" if orphan_items > 0 else "INFO",
                "recommended_action": "Quarantine orphan items; investigate missing parent orders",
                "validation_status": "PASSED" if orphan_items == 0 else "FAILED"
            })

    # 3. Check Order Payments Dataset
    payments_file = RAW_DATA_DIR / "olist_order_payments_dataset.csv"
    if payments_file.exists():
        df_payments = pd.read_csv(payments_file)
        n_pay = len(df_payments)
        logger.info(f"Auditing payments dataset ({n_pay:,} rows)...")
        
        # Check: Zero or negative payment value
        zero_or_neg_pay = (df_payments['payment_value'] <= 0).sum()
        findings.append({
            "check_id": "DQ-PAY-01",
            "table": "order_payments",
            "column_or_rule": "payment_value",
            "issue_detected": "Zero or negative payment transaction amounts",
            "affected_records": int(zero_or_neg_pay),
            "severity": "MEDIUM" if zero_or_neg_pay > 0 else "INFO",
            "recommended_action": "Retain zero-value transactions if full voucher/credit coverage",
            "validation_status": "WARNING" if zero_or_neg_pay > 0 else "PASSED"
        })
        
        # Check: Valid payment installments
        invalid_installments = (df_payments['payment_installments'] < 0).sum()
        findings.append({
            "check_id": "DQ-PAY-02",
            "table": "order_payments",
            "column_or_rule": "payment_installments",
            "issue_detected": "Negative installment counts",
            "affected_records": int(invalid_installments),
            "severity": "CRITICAL" if invalid_installments > 0 else "INFO",
            "recommended_action": "Flag data entry error; set to 1 minimum",
            "validation_status": "PASSED" if invalid_installments == 0 else "FAILED"
        })

    # 4. Check Order Reviews Dataset
    reviews_file = RAW_DATA_DIR / "olist_order_reviews_dataset.csv"
    if reviews_file.exists():
        df_reviews = pd.read_csv(reviews_file)
        n_rev = len(df_reviews)
        logger.info(f"Auditing reviews dataset ({n_rev:,} rows)...")
        
        # Check: Review score in valid range 1-5
        invalid_score = (~df_reviews['review_score'].isin([1, 2, 3, 4, 5])).sum()
        findings.append({
            "check_id": "DQ-REV-01",
            "table": "order_reviews",
            "column_or_rule": "review_score",
            "issue_detected": "Out-of-range customer satisfaction score",
            "affected_records": int(invalid_score),
            "severity": "CRITICAL" if invalid_score > 0 else "INFO",
            "recommended_action": "Cap bounds or investigate rating scale corruption",
            "validation_status": "PASSED" if invalid_score == 0 else "FAILED"
        })
        
        # Check: Duplicate review records for same order and review_id
        dup_rev = df_reviews.duplicated(subset=['review_id', 'order_id']).sum()
        findings.append({
            "check_id": "DQ-REV-02",
            "table": "order_reviews",
            "column_or_rule": "review_id + order_id",
            "issue_detected": "Duplicate review feedback on identical order",
            "affected_records": int(dup_rev),
            "severity": "MEDIUM" if dup_rev > 0 else "INFO",
            "recommended_action": "Retain most recent review response timestamp",
            "validation_status": "WARNING" if dup_rev > 0 else "PASSED"
        })

    # 5. Check Customers Dataset
    cust_file = RAW_DATA_DIR / "olist_customers_dataset.csv"
    if cust_file.exists():
        df_cust = pd.read_csv(cust_file)
        n_cust = len(df_cust)
        logger.info(f"Auditing customers dataset ({n_cust:,} rows)...")
        
        dup_cust_id = df_cust['customer_id'].duplicated().sum()
        findings.append({
            "check_id": "DQ-CST-01",
            "table": "customers",
            "column_or_rule": "customer_id",
            "issue_detected": "Duplicate customer order session token",
            "affected_records": int(dup_cust_id),
            "severity": "CRITICAL" if dup_cust_id > 0 else "INFO",
            "recommended_action": "Ensure customer_id remains unique per transaction",
            "validation_status": "PASSED" if dup_cust_id == 0 else "FAILED"
        })
        
        # Repeat customer detection check (customer_unique_id vs customer_id)
        distinct_sessions = df_cust['customer_id'].nunique()
        distinct_people = df_cust['customer_unique_id'].nunique()
        repeat_buyers = (df_cust['customer_unique_id'].value_counts() > 1).sum()
        findings.append({
            "check_id": "DQ-CST-02",
            "table": "customers",
            "column_or_rule": "customer_unique_id",
            "issue_detected": f"Granularity distinction: {distinct_sessions:,} sessions vs {distinct_people:,} unique buyers ({repeat_buyers:,} repeat buyers)",
            "affected_records": int(distinct_sessions - distinct_people),
            "severity": "INFO",
            "recommended_action": "MUST use customer_unique_id for all retention and RFM metrics",
            "validation_status": "PASSED"
        })

    # 6. Check Products Dataset
    prod_file = RAW_DATA_DIR / "olist_products_dataset.csv"
    if prod_file.exists():
        df_prod = pd.read_csv(prod_file)
        n_prod = len(df_prod)
        logger.info(f"Auditing products dataset ({n_prod:,} rows)...")
        
        null_cat = df_prod['product_category_name'].isnull().sum()
        findings.append({
            "check_id": "DQ-PRD-01",
            "table": "products",
            "column_or_rule": "product_category_name",
            "issue_detected": "Missing Portuguese category name",
            "affected_records": int(null_cat),
            "severity": "LOW" if null_cat > 0 else "INFO",
            "recommended_action": "Impute 'unassigned' category in staging without dropping product",
            "validation_status": "WARNING" if null_cat > 0 else "PASSED"
        })
        
        dup_prod = df_prod['product_id'].duplicated().sum()
        findings.append({
            "check_id": "DQ-PRD-02",
            "table": "products",
            "column_or_rule": "product_id",
            "issue_detected": "Duplicate product identifier",
            "affected_records": int(dup_prod),
            "severity": "CRITICAL" if dup_prod > 0 else "INFO",
            "recommended_action": "Enforce strict uniqueness on dim_product PK",
            "validation_status": "PASSED" if dup_prod == 0 else "FAILED"
        })

    # 7. Check Sellers Dataset
    sell_file = RAW_DATA_DIR / "olist_sellers_dataset.csv"
    if sell_file.exists():
        df_sellers = pd.read_csv(sell_file)
        dup_sellers = df_sellers['seller_id'].duplicated().sum()
        findings.append({
            "check_id": "DQ-SEL-01",
            "table": "sellers",
            "column_or_rule": "seller_id",
            "issue_detected": "Duplicate seller identifier",
            "affected_records": int(dup_sellers),
            "severity": "CRITICAL" if dup_sellers > 0 else "INFO",
            "recommended_action": "Ensure seller_id is unique across seller directory",
            "validation_status": "PASSED" if dup_sellers == 0 else "FAILED"
        })

    # 8. Check Geolocation Dataset
    geo_file = RAW_DATA_DIR / "olist_geolocation_dataset.csv"
    if geo_file.exists():
        # Large file, sample or read zip codes
        df_geo = pd.read_csv(geo_file, usecols=['geolocation_zip_code_prefix'])
        n_geo = len(df_geo)
        unique_zips = df_geo['geolocation_zip_code_prefix'].nunique()
        findings.append({
            "check_id": "DQ-GEO-01",
            "table": "geolocation",
            "column_or_rule": "geolocation_zip_code_prefix",
            "issue_detected": f"High cardinality duplication: {n_geo:,} total records for {unique_zips:,} unique zip code prefixes",
            "affected_records": int(n_geo - unique_zips),
            "severity": "MEDIUM",
            "recommended_action": "Aggregate spatial coordinates to average lat/long per zip code prefix before dimensional modeling",
            "validation_status": "WARNING"
        })

    # Save output report
    report_df = pd.DataFrame(findings)
    report_df.to_csv(REPORT_OUTPUT_PATH, index=False)
    logger.info(f"Data quality audit completed. Saved report with {len(report_df)} checks to {REPORT_OUTPUT_PATH}")
    return report_df

if __name__ == "__main__":
    run_data_quality_audit()

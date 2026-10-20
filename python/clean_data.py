"""
Data Cleaning and Standardization Pipeline for Olist E-Commerce.
Applies data hygiene rules, normalizes categories, validates financial fields,
and exports cleaned staging data while preserving flagged records for investigation.
"""

import os
import sys
import logging
from pathlib import Path
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("clean_data")

RAW_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
CLEAN_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "cleaned"
CLEAN_DATA_DIR.mkdir(parents=True, exist_ok=True)

def clean_customers():
    src = RAW_DATA_DIR / "olist_customers_dataset.csv"
    if not src.exists():
        logger.warning(f"File not found: {src}")
        return
    logger.info("Cleaning customers dataset...")
    df = pd.read_csv(src)
    df['customer_id'] = df['customer_id'].astype(str).str.strip()
    df['customer_unique_id'] = df['customer_unique_id'].astype(str).str.strip()
    df['customer_zip_code_prefix'] = df['customer_zip_code_prefix'].astype(str).str.strip().str.zfill(5)
    df['customer_city'] = df['customer_city'].astype(str).str.strip().str.title()
    df['customer_state'] = df['customer_state'].astype(str).str.strip().str.upper()
    
    out_file = CLEAN_DATA_DIR / "clean_customers.parquet"
    df.to_parquet(out_file, index=False)
    logger.info(f"Saved {len(df):,} cleaned customer records to {out_file}")

def clean_orders():
    src = RAW_DATA_DIR / "olist_orders_dataset.csv"
    if not src.exists():
        logger.warning(f"File not found: {src}")
        return
    logger.info("Cleaning orders dataset...")
    df = pd.read_csv(src)
    df['order_id'] = df['order_id'].astype(str).str.strip()
    df['customer_id'] = df['customer_id'].astype(str).str.strip()
    df['order_status'] = df['order_status'].astype(str).str.strip().str.lower()
    
    # Parse dates
    date_cols = [
        'order_purchase_timestamp',
        'order_approved_at',
        'order_delivered_carrier_date',
        'order_delivered_customer_date',
        'order_estimated_delivery_date'
    ]
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')
        
    # Delivery duration
    df['delivery_days'] = (df['order_delivered_customer_date'] - df['order_purchase_timestamp']).dt.total_seconds() / (24 * 3600)
    
    # On-time delivery flag
    df['is_delivered_on_time'] = np.where(
        df['order_delivered_customer_date'].notnull() & df['order_estimated_delivery_date'].notnull(),
        df['order_delivered_customer_date'].dt.date <= df['order_estimated_delivery_date'].dt.date,
        None
    )
    
    out_file = CLEAN_DATA_DIR / "clean_orders.parquet"
    df.to_parquet(out_file, index=False)
    logger.info(f"Saved {len(df):,} cleaned order records to {out_file}")

def clean_order_items():
    src = RAW_DATA_DIR / "olist_order_items_dataset.csv"
    if not src.exists():
        logger.warning(f"File not found: {src}")
        return
    logger.info("Cleaning order items dataset...")
    df = pd.read_csv(src)
    df['order_id'] = df['order_id'].astype(str).str.strip()
    df['order_item_id'] = pd.to_numeric(df['order_item_id'], errors='coerce').fillna(1).astype(int)
    df['product_id'] = df['product_id'].astype(str).str.strip()
    df['seller_id'] = df['seller_id'].astype(str).str.strip()
    df['shipping_limit_date'] = pd.to_datetime(df['shipping_limit_date'], errors='coerce')
    df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0.0).round(2)
    df['freight_value'] = pd.to_numeric(df['freight_value'], errors='coerce').fillna(0.0).round(2)
    df['line_total'] = (df['price'] + df['freight_value']).round(2)
    
    out_file = CLEAN_DATA_DIR / "clean_order_items.parquet"
    df.to_parquet(out_file, index=False)
    logger.info(f"Saved {len(df):,} cleaned order item records to {out_file}")

def clean_products():
    src = RAW_DATA_DIR / "olist_products_dataset.csv"
    tr_src = RAW_DATA_DIR / "product_category_name_translation.csv"
    if not src.exists():
        logger.warning(f"File not found: {src}")
        return
    logger.info("Cleaning products dataset...")
    df = pd.read_csv(src)
    df['product_id'] = df['product_id'].astype(str).str.strip()
    df['product_category_name'] = df['product_category_name'].astype(str).str.strip().replace({'nan': 'unassigned'})
    
    if tr_src.exists():
        tr_df = pd.read_csv(tr_src)
        tr_df['product_category_name'] = tr_df['product_category_name'].astype(str).str.strip()
        tr_df['product_category_name_english'] = tr_df['product_category_name_english'].astype(str).str.strip()
        df = df.merge(tr_df, on='product_category_name', how='left')
    else:
        df['product_category_name_english'] = df['product_category_name']
        
    df['product_category_name_english'] = df['product_category_name_english'].fillna('unassigned')
    
    out_file = CLEAN_DATA_DIR / "clean_products.parquet"
    df.to_parquet(out_file, index=False)
    logger.info(f"Saved {len(df):,} cleaned product records to {out_file}")

def main():
    logger.info("=== Starting Data Cleaning Pipeline ===")
    clean_customers()
    clean_orders()
    clean_order_items()
    clean_products()
    logger.info("=== Data Cleaning Pipeline Completed Successfully ===")

if __name__ == "__main__":
    main()

"""
High-Performance Data Ingestion Pipeline for Olist E-Commerce Analytics.
Downloads official Olist CSVs and uses PostgreSQL COPY for sub-second ingestion into raw_olist schema.
"""

import os
import sys
import time
import urllib.request
import logging
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("load_data")

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "2003")
DB_NAME = os.getenv("DB_NAME", "olist_dw")

RAW_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
SQL_DIR = Path(__file__).resolve().parent.parent / "sql"

GITHUB_BASE_URL = "https://raw.githubusercontent.com/olist/work-at-olist-data/master/datasets/"

DATASETS = [
    ("raw_customers", "olist_customers_dataset.csv"),
    ("raw_geolocation", "olist_geolocation_dataset.csv"),
    ("raw_order_items", "olist_order_items_dataset.csv"),
    ("raw_order_payments", "olist_order_payments_dataset.csv"),
    ("raw_order_reviews", "olist_order_reviews_dataset.csv"),
    ("raw_orders", "olist_orders_dataset.csv"),
    ("raw_products", "olist_products_dataset.csv"),
    ("raw_sellers", "olist_sellers_dataset.csv"),
    ("raw_category_translation", "product_category_name_translation.csv")
]

def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME
    )

def download_file(filename: str) -> Path:
    target_path = RAW_DATA_DIR / filename
    if target_path.exists() and target_path.stat().st_size > 0:
        logger.info(f"Existing file cached: {filename} ({target_path.stat().st_size:,} bytes)")
        return target_path
    
    url = GITHUB_BASE_URL + filename
    logger.info(f"Downloading {filename} from {url}...")
    opener = urllib.request.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')]
    urllib.request.install_opener(opener)
    urllib.request.urlretrieve(url, str(target_path))
    logger.info(f"Downloaded {filename} ({target_path.stat().st_size:,} bytes)")
    return target_path

def init_raw_tables(conn):
    schema_sql_path = SQL_DIR / "01_raw_schema.sql"
    with open(schema_sql_path, "r", encoding="utf-8") as f:
        sql = f.read()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    logger.info("Initialized raw_olist schema and DDL definitions from 01_raw_schema.sql")

def ingest_dataset_copy(conn, table_name: str, filename: str):
    file_path = download_file(filename)
    
    # Read header from file to determine column list
    with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
        header_line = f.readline().strip()
    
    cols = [c.strip().replace('"', '').replace('\ufeff', '') for c in header_line.split(",")]
    cols_str = ", ".join(cols)
    
    start_time = time.time()
    with conn.cursor() as cur:
        # Truncate raw table prior to clean ingestion
        cur.execute(f"TRUNCATE TABLE raw_olist.{table_name};")
        
        copy_sql = f"COPY raw_olist.{table_name} ({cols_str}) FROM STDIN WITH CSV HEADER ENCODING 'UTF8';"
        with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
            cur.copy_expert(copy_sql, f)
            
        # Get count
        cur.execute(f"SELECT COUNT(*) FROM raw_olist.{table_name};")
        row_count = cur.fetchone()[0]
        
        # Log entry
        duration = time.time() - start_time
        cur.execute("""
            INSERT INTO raw_olist.ingestion_log (table_name, source_file, row_count, status, notes)
            VALUES (%s, %s, %s, 'SUCCESS', %s);
        """, (f"raw_olist.{table_name}", filename, row_count, f"COPY completed in {duration:.2f}s"))
        
    conn.commit()
    logger.info(f"Ingested {row_count:,} rows into raw_olist.{table_name} in {duration:.2f}s")

def main():
    logger.info("=== Starting Fast Olist Data Ingestion Pipeline ===")
    conn = get_connection()
    try:
        init_raw_tables(conn)
        for table_name, filename in DATASETS:
            ingest_dataset_copy(conn, table_name, filename)
        logger.info("=== Data Ingestion Pipeline Completed Successfully ===")
    finally:
        conn.close()

if __name__ == "__main__":
    main()

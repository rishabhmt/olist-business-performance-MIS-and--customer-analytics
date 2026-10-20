# Olist Dataset & Ingestion Directory

## Source Attribution & Licensing
- **Dataset:** Brazilian E-Commerce Public Dataset by Olist
- **Publisher:** Olist & Kaggle
- **License:** CC BY-NC-SA 4.0 (Open Data for research, analysis and portfolio showcase)
- **Time Period:** 2016-09-04 to 2018-10-17
- **Source Repository:** `https://github.com/olist/work-at-olist-data/tree/master/datasets`

## Directory Structure:
- `data/raw/`: Local staging cache for the 9 raw CSV files (excluded from Git).
- `data/data_quality_report.csv`: Automated data quality assessment report containing column-level checks, null counts, duplicate records, foreign key integrity, and business rule validations.

## Ingestion Instructions:
To download and ingest the dataset into the PostgreSQL `raw_olist` schema, run:
```bash
python python/load_data.py
```
This script handles downloading directly from the official Olist repository, validates checksums and row counts, and ingests all records into PostgreSQL with full audit tracking.

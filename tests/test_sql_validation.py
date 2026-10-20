"""
Automated Security and Integrity Tests for AI SQL AST Validator.
Verifies zero-trust guardrails, injection prevention, and read-only enforcement.
"""

import pytest
from ai_analytics.sql_validator import validate_and_sanitize_sql

def test_valid_executive_kpi_query():
    sql = "SELECT total_revenue, total_orders FROM analytics.vw_executive_kpis;"
    is_valid, sanitized, err = validate_and_sanitize_sql(sql)
    assert is_valid is True
    assert "LIMIT 100" in sanitized
    assert err == ""

def test_valid_monthly_trend_query():
    sql = "SELECT month_year, monthly_revenue FROM analytics.vw_monthly_sales_performance WHERE month_year LIKE '2018%';"
    is_valid, sanitized, err = validate_and_sanitize_sql(sql)
    assert is_valid is True
    assert "LIMIT 100" in sanitized

def test_valid_category_query_with_existing_limit():
    sql = "SELECT category_name, total_category_revenue FROM analytics.vw_category_performance LIMIT 10;"
    is_valid, sanitized, err = validate_and_sanitize_sql(sql)
    assert is_valid is True
    assert "LIMIT 10" in sanitized

def test_excessive_limit_capped_to_max():
    sql = "SELECT category_name FROM analytics.vw_category_performance LIMIT 500;"
    is_valid, sanitized, err = validate_and_sanitize_sql(sql)
    assert is_valid is True
    assert "LIMIT 100" in sanitized

def test_reject_drop_table():
    sql = "DROP TABLE orders;"
    is_valid, sanitized, err = validate_and_sanitize_sql(sql)
    assert is_valid is False
    assert "Prohibited" in err or "prohibited" in err

def test_reject_delete_records():
    sql = "DELETE FROM customers WHERE 1=1;"
    is_valid, sanitized, err = validate_and_sanitize_sql(sql)
    assert is_valid is False
    assert "DELETE" in err or "prohibited" in err

def test_reject_multi_statement_stacked_injection():
    sql = "SELECT * FROM analytics.vw_executive_kpis; DROP TABLE orders;"
    is_valid, sanitized, err = validate_and_sanitize_sql(sql)
    assert is_valid is False
    assert "Multi-statement" in err

def test_reject_sql_comment_injection():
    sql = "SELECT * FROM analytics.vw_executive_kpis -- bypass filter"
    is_valid, sanitized, err = validate_and_sanitize_sql(sql)
    assert is_valid is False
    assert "comment" in err.lower()

def test_reject_system_catalog_access():
    sql = "SELECT * FROM pg_catalog.pg_tables;"
    is_valid, sanitized, err = validate_and_sanitize_sql(sql)
    assert is_valid is False
    assert "restricted catalog" in err.lower()

def test_reject_raw_schema_access():
    sql = "SELECT * FROM raw_olist.raw_orders;"
    is_valid, sanitized, err = validate_and_sanitize_sql(sql)
    assert is_valid is False
    assert "restricted catalog/schema 'raw_olist'" in err.lower()

def test_reject_unapproved_physical_table():
    sql = "SELECT * FROM analytics.fact_orders;"
    is_valid, sanitized, err = validate_and_sanitize_sql(sql)
    assert is_valid is False
    assert "does not reference any authorized view" in err.lower()

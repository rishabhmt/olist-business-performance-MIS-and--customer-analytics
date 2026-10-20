"""
AI Governed Analytics: SQL AST Validator and Safe Execution Engine.
Enforces zero-trust database security by parsing SQL Abstract Syntax Trees,
rejecting DDL/DML/multi-statements, validating approved views, and enforcing query limits.
"""

import os
import re
import logging
from typing import Dict, Any, List, Tuple
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where, Comparison
from sqlparse.tokens import Keyword, DML, DDL, Comment, Punctuation
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sql_validator")

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_READONLY_USER", "postgres")
DB_PASSWORD = os.getenv("DB_READONLY_PASSWORD", "2003")
DB_NAME = os.getenv("DB_NAME", "olist_dw")

ALLOWED_VIEWS = {
    "analytics.vw_executive_kpis",
    "analytics.vw_monthly_sales_performance",
    "analytics.vw_category_performance",
    "analytics.vw_customer_rfm_segments",
    "analytics.vw_delivery_logistics_performance",
    "analytics.vw_seller_performance",
    "vw_executive_kpis",
    "vw_monthly_sales_performance",
    "vw_category_performance",
    "vw_customer_rfm_segments",
    "vw_delivery_logistics_performance",
    "vw_seller_performance"
}

PROHIBITED_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", 
    "GRANT", "REVOKE", "EXECUTE", "EXEC", "CALL", "COPY", "INTO", 
    "PG_SLEEP", "SHUTDOWN", "SET", "RESET", "VACUUM", "ANALYZE"
}

MAX_ROW_LIMIT = 100
QUERY_TIMEOUT_MS = 5000

class SQLValidationError(Exception):
    pass

def extract_table_names(tokens) -> List[str]:
    """Recursively extracts referenced table or view identifiers from AST tokens."""
    tables = []
    from_seen = False
    
    for token in tokens:
        if token.is_group:
            tables.extend(extract_table_names(token.tokens))
        elif token.ttype is Keyword and token.value.upper() in ("FROM", "JOIN", "INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "CROSS JOIN"):
            from_seen = True
        elif from_seen:
            if isinstance(token, Identifier):
                tables.append(token.get_real_name() or token.value)
                from_seen = False
            elif isinstance(token, IdentifierList):
                for id_token in token.get_identifiers():
                    tables.append(id_token.get_real_name() or id_token.value)
                from_seen = False
            elif token.ttype is Keyword:
                from_seen = False
    return tables

def validate_and_sanitize_sql(sql: str) -> Tuple[bool, str, str]:
    """
    Validates a SQL query string through strict AST analysis.
    Returns: (is_valid, sanitized_sql_or_empty, error_message_or_empty)
    """
    if not sql or not sql.strip():
        return False, "", "Query string is empty."

    # Reject inline comments which are often used for comment injection
    if "--" in sql or "/*" in sql:
        return False, "", "SQL comments are prohibited for security."

    # Parse using sqlparse
    try:
        statements = sqlparse.parse(sql.strip())
    except Exception as e:
        return False, "", f"SQL Parser Syntax Error: {e}"

    if len(statements) == 0:
        return False, "", "No valid SQL statements found."

    # Enforce exactly ONE statement (prevent stacked query injection: SELECT ...; DROP TABLE ...)
    if len(statements) > 1:
        return False, "", f"Multi-statement queries prohibited. Found {len(statements)} statements."

    stmt = statements[0]

    # Validate Statement Type: MUST be SELECT
    stmt_type = stmt.get_type()
    if stmt_type != "SELECT":
        return False, "", f"Operation '{stmt_type}' is prohibited. Only read-only 'SELECT' statements are authorized."

    # Flatten tokens and check against prohibited DDL/DML keywords
    tokens_flat = [t for t in stmt.flatten()]
    for token in tokens_flat:
        val_upper = token.value.upper()
        if val_upper in PROHIBITED_KEYWORDS:
            return False, "", f"Prohibited keyword '{val_upper}' detected."
        if token.ttype in (DDL, DML) and val_upper != "SELECT":
            return False, "", f"Prohibited operation '{val_upper}' detected."
        if token.ttype in Comment:
            return False, "", "SQL comment tokens are prohibited."

    # Check referenced objects/tables
    sql_text_lower = sql.lower()
    
    # Check for forbidden catalog or schema access
    forbidden_catalogs = ["pg_catalog", "information_schema", "pg_tables", "pg_class", "pg_user", "raw_olist", "staging"]
    for cat in forbidden_catalogs:
        if cat in sql_text_lower:
            return False, "", f"Access to restricted catalog/schema '{cat}' is prohibited."

    # Ensure at least one approved view is referenced
    has_approved_view = any(view.lower() in sql_text_lower for view in ALLOWED_VIEWS)
    if not has_approved_view:
        return False, "", f"Query does not reference any authorized view. Allowed: {sorted(list(ALLOWED_VIEWS))}"

    # Enforce or inject LIMIT clause
    clean_sql = sql.strip().rstrip(";")
    limit_match = re.search(r'\bLIMIT\s+(\d+)\b', clean_sql, re.IGNORECASE)
    if limit_match:
        limit_val = int(limit_match.group(1))
        if limit_val > MAX_ROW_LIMIT:
            # Replace with maximum allowed limit
            clean_sql = re.sub(r'\bLIMIT\s+\d+\b', f"LIMIT {MAX_ROW_LIMIT}", clean_sql, flags=re.IGNORECASE)
    else:
        clean_sql += f" LIMIT {MAX_ROW_LIMIT}"

    return True, clean_sql, ""

def execute_governed_query(sql: str) -> Dict[str, Any]:
    """
    Validates and executes a governed SQL query with timeout and read-only constraints.
    """
    is_valid, sanitized_sql, error_msg = validate_and_sanitize_sql(sql)
    if not is_valid:
        logger.warning(f"Validation rejected query: {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "row_count": 0,
            "columns": [],
            "rows": []
        }

    try:
        connection_url = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        engine = create_engine(connection_url)
        
        with engine.connect() as conn:
            # Set query timeout and read-only transaction mode
            conn.execute(text(f"SET statement_timeout = '{QUERY_TIMEOUT_MS}ms';"))
            conn.execute(text("SET default_transaction_read_only = TRUE;"))
            
            result = conn.execute(text(sanitized_sql))
            columns = list(result.keys())
            rows = [dict(row._mapping) for row in result.fetchall()]
            
            logger.info(f"Query executed successfully: returned {len(rows)} rows.")
            return {
                "success": True,
                "sanitized_sql": sanitized_sql,
                "row_count": len(rows),
                "columns": columns,
                "rows": rows,
                "error": None
            }
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "row_count": 0,
            "columns": [],
            "rows": []
        }

if __name__ == "__main__":
    # Test safe valid query
    test_safe = "SELECT total_revenue, total_orders, average_order_value FROM analytics.vw_executive_kpis;"
    valid, s_sql, err = validate_and_sanitize_sql(test_safe)
    print("Test Safe Query:", "VALID" if valid else f"INVALID: {err}", "->", s_sql)

    # Test dangerous attack: drop table
    test_attack = "SELECT * FROM analytics.vw_executive_kpis; DROP TABLE orders;"
    valid, s_sql, err = validate_and_sanitize_sql(test_attack)
    print("Test Stacked Attack:", "VALID" if valid else f"BLOCKED: {err}")

    # Test prohibited catalog
    test_catalog = "SELECT * FROM pg_catalog.pg_tables;"
    valid, s_sql, err = validate_and_sanitize_sql(test_catalog)
    print("Test System Catalog:", "VALID" if valid else f"BLOCKED: {err}")

"""
Automated Deliverable and Quality Asset Tests.
Verifies the existence, schema, and completeness of generated MIS workbooks,
data quality reports, screenshots, and evaluation artifacts.
"""

from pathlib import Path
import openpyxl
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def test_data_quality_report_exists_and_valid():
    dq_path = PROJECT_ROOT / "data" / "data_quality_report.csv"
    assert dq_path.exists(), "data_quality_report.csv is missing"
    
    df = pd.read_csv(dq_path)
    required_cols = [
        "check_id", "table", "column_or_rule", "issue_detected",
        "affected_records", "severity", "recommended_action", "validation_status"
    ]
    for col in required_cols:
        assert col in df.columns, f"Missing column in DQ report: {col}"
    assert len(df) >= 15, "Expected at least 15 comprehensive DQ checks"

def test_excel_mis_workbook_sheets():
    excel_path = PROJECT_ROOT / "excel_mis" / "management_reporting.xlsx"
    assert excel_path.exists(), "management_reporting.xlsx is missing"
    
    wb = openpyxl.load_workbook(excel_path, read_only=True)
    required_sheets = [
        "Management_Summary",
        "Monthly_MIS",
        "Product_Category_Analysis",
        "Customer_Analysis",
        "Delivery_Exceptions",
        "KPI_Calculations",
        "Data_Quality_Reconciliation"
    ]
    for sheet in required_sheets:
        assert sheet in wb.sheetnames, f"Missing required sheet: {sheet}"

def test_genuine_dashboard_screenshots_exist():
    images_dir = PROJECT_ROOT / "docs" / "images"
    assert images_dir.exists(), "docs/images directory is missing"
    
    expected_images = [
        "dashboard-overview.png",
        "dashboard-sales.png",
        "dashboard-customers.png",
        "dashboard-delivery.png",
        "dashboard-recommendations.png"
    ]
    for img in expected_images:
        img_path = images_dir / img
        assert img_path.exists(), f"Missing dashboard screenshot: {img}"
        assert img_path.stat().st_size > 50_000, f"Screenshot file too small: {img}"

def test_ai_evaluation_questions_count():
    eval_path = PROJECT_ROOT / "ai_analytics" / "evaluation_questions.csv"
    assert eval_path.exists(), "evaluation_questions.csv is missing"
    
    df = pd.read_csv(eval_path)
    assert len(df) >= 30, f"Expected at least 30 evaluation questions, found {len(df)}"

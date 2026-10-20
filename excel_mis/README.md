# Excel MIS Management Reporting Workbook

**File:** `excel_mis/management_reporting.xlsx`  
**Audience:** Executive Leadership, C-Suite, Operations Directors, Commercial Leads  
**Purpose:** Delivers structured, refreshable, auditable management information system (MIS) reporting reconciled directly against canonical PostgreSQL analytical views.

---

## 1. Sheet Architecture & Navigation

The workbook is structured into 7 dedicated sheets:

| Sheet Name | Content & Purpose | Core Formulas & Features |
|---|---|---|
| **`Management_Summary`** | Executive headline dashboard, 5 core KPI cards, strategic business commentary, trailing 12-month summary table. | `=KPI_Calculations!B4`, structured KPI cards, formatting. |
| **`Monthly_MIS`** | Full historical month-by-month trajectory (2016-09 through 2018-10), order volume, gross revenue, merchandise vs freight split, AOV, MoM growth %. | `=IFERROR((C5-C4)/C4, 0)`, `=C5/B5`, number formats. |
| **`Product_Category_Analysis`** | Top 20 merchandise categories by gross turnover, item sales volume, share of revenue %, average price and shipping charges. | `=D5/SUM($D$5:$D$24)`, subtotal audit rows. |
| **`Customer_Analysis`** | Granularity audit of customer sessions vs unique human buyers, one-time vs repeat buyers, repeat customer rate, and full RFM segmentation breakdown. | `=B7/B5`, frequency segmentation distribution. |
| **`Delivery_Exceptions`** | State-level logistics performance across Brazil's 27 federative units, transit days, on-time rates, freight per order, logistics risk indicators. | `=1-E5`, threshold status formatting (OPTIMAL / MONITOR / WARNING / CRITICAL). |
| **`KPI_Calculations`** | Canonical metric reference dictionary mapping every business KPI to its exact mathematical formula, PostgreSQL view query, and Power BI DAX formula. | Master audit dictionary table. |
| **`Data_Quality_Reconciliation`** | Cross-layer reconciliation matrix comparing Source CSV row counts and financial totals against Staging, Data Warehouse Facts, and Excel MIS metrics. | `=D5-B5` discrepancy tracking, zero fan-out validation. |

---

## 2. Refresh & Maintenance Instructions

### Data Flow:
```
PostgreSQL (analytics.vw_*) 
       │
       ▼
Excel MIS Report (management_reporting.xlsx)
```

1. **Automatic Database Connection / Power Query:**
   - In Excel, navigate to **Data** → **Get Data** → **From Database** → **From PostgreSQL Database**.
   - Server: `localhost:5432` | Database: `olist_dw`.
   - Select SQL view: `analytics.vw_executive_kpis`, `analytics.vw_monthly_sales_performance`, `analytics.vw_category_performance`.
2. **Formula Audit:**
   - All headline KPI cards on `Management_Summary` dynamically link to `KPI_Calculations` cells.
   - Updating `KPI_Calculations` instantly cascades to the summary cards and reconciliation matrices.
3. **Verification:**
   - Verify `Data_Quality_Reconciliation` Sheet column `F` shows `$0.00` discrepancy between the Data Warehouse and Excel MIS layer.

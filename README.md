# Python Billing Report Debugging & Vectorization

Debugging and performance optimization of `billing_report.py` using **pandas**, processing subscription and payment CSV datasets (~90k rows) to generate billing metrics as of `2026-11-15` without altering the expected report structure.

## Key Improvements
- **Resolved 12 logic, syntax, date-boundary, and formatting issues**, including:
  - Pinning the reference date (`AS_OF`) to `2026-11-15` instead of using the current execution date.
  - Fixing active subscription date boundaries (`start_date <= as_of` and `end_date.isna() | (end_date >= as_of)`).
  - Replacing the mutable default dictionary (`totals={}`) with `totals=None` inside `mrr_by_plan` and fixing the `monthly_price` column name typo.
  - Preserving negative refund signs in `monthly_revenue`, fixing `%Y-%m` month formatting, covering all 6 calendar months, and casting values to `float`.
  - Using true division (`/`) with a zero-base guard for churn percentage and sorting plan MRR numerically in descending order.
  - Fixing orphan payment detection against known customer IDs rather than an inner merge with a plan `NaN` check.
- **Vectorized customer aggregation** (`groupby("customer_id")["amount"].sum().nlargest(n)`), cutting runtime from **~30s down to ~0.7s**.
- Marked all changes with `# FIXED:` comments in `billing_report.py`.

## Risk & Edge-Case Notes
- Active subscriptions are counted per row (renewals or multiple rows for the same customer count individually).
- The `status` column is not used; scheduled future cancellations remain active until their `end_date`.

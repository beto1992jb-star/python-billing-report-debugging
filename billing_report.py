"""
Subscription billing report.

Reads subscriptions.csv and payments.csv and prints, as of a fixed date:
  - active subscriptions and MRR (monthly recurring revenue)
  - MRR at the start of the reporting window and the % change
  - net revenue per month (payments minus refunds) for the last 6 months
  - churn since the start of the window
  - MRR by plan
  - top 5 customers by net payments
  - payments from customers that have no subscription
"""
import pandas as pd

SUBS_FILE = "subscriptions.csv"
PAYMENTS_FILE = "payments.csv"
AS_OF = pd.Timestamp("2026-11-15")  # FIXED: pinned report reference date to 2026-11-15 instead of today()
WINDOW_START = pd.Timestamp("2026-06-01")
MONTHS_BACK = 6


def load_subscriptions(path):
    """Load subscriptions with parsed dates."""
    return pd.read_csv(path, parse_dates=["start_date", "end_date"])


def load_payments(path):
    """Load payments with parsed dates. Refunds are negative amounts."""
    return pd.read_csv(path, parse_dates=["paid_date"])


def active_subscriptions(df, as_of):
    """Subscriptions active on a date: started on or before it, and with
    no end date or an end date on or after it."""
    started = df["start_date"] <= as_of  # FIXED: included subscriptions starting on or before as_of
    not_ended = df["end_date"].isna() | (df["end_date"] >= as_of)  # FIXED: kept open-ended (NaT) and end_date >= as_of subscriptions
    return df[started & not_ended]


def mrr_by_plan(active, totals=None):
    """Sum of monthly_price for each plan."""
    if totals is None:  # FIXED: avoided shared mutable default dict across calls
        totals = {}
    for plan, value in active.groupby("plan")["monthly_price"].sum().items():  # FIXED: corrected column typo from monthly_prize to monthly_price
        totals[plan] = totals.get(plan, 0) + value
    return totals


def monthly_revenue(payments, months_back):
    """Net revenue (payments minus refunds) for the last N calendar months,
    including the current one. Months without payments show 0."""
    payments = payments.copy()
    # FIXED: preserved signed amounts so refunds (negative values) are subtracted rather than abs()'d
    payments["month"] = payments["paid_date"].dt.strftime("%Y-%m")  # FIXED: used %m (month) instead of %M (minute)
    by_month = payments.groupby("month")["amount"].sum()
    result = {}
    for i in range(months_back - 1, -1, -1):  # FIXED: covered all months_back calendar months up to AS_OF, including current month
        month = (AS_OF - pd.DateOffset(months=i)).strftime("%Y-%m")
        result[month] = float(by_month.get(month, 0.0))
    return dict(sorted(result.items()))


def churn(subs):
    """Subscriptions active at the window start that have ended by AS_OF."""
    base = active_subscriptions(subs, WINDOW_START)
    churned = base[base["end_date"].notna() & (base["end_date"] <= AS_OF)]
    return len(churned), len(base)


def top_customers(payments, n=5):
    """The n customers with the highest net payments."""
    # FIXED: vectorized groupby aggregation instead of repeated full-DataFrame filtering per customer
    return payments.groupby("customer_id")["amount"].sum().nlargest(n)


def orphan_payments(payments, subs):
    """Number of payments whose customer has no subscription."""
    valid_customers = set(subs["customer_id"].dropna())  # FIXED: matched payments against known customer_ids instead of inner join + isna()
    return int((~payments["customer_id"].isin(valid_customers)).sum())


def main():
    subs = load_subscriptions(SUBS_FILE)
    payments = load_payments(PAYMENTS_FILE)

    active_now = active_subscriptions(subs, AS_OF)
    active_start = active_subscriptions(subs, WINDOW_START)

    by_plan_now = mrr_by_plan(active_now)
    by_plan_start = mrr_by_plan(active_start)
    mrr_now = sum(by_plan_now.values())
    mrr_start = sum(by_plan_start.values())
    change = (mrr_now - mrr_start) / mrr_start * 100

    churned, base = churn(subs)
    churn_pct = (churned / base * 100) if base else 0.0  # FIXED: used true division (/) instead of floor division (//)

    print(f"=== BILLING REPORT (as of {AS_OF:%Y-%m-%d}) ===")
    print(f"Active subscriptions: {len(active_now)}")
    print(f"MRR: {mrr_now:,.2f}")
    print(f"MRR at {WINDOW_START:%Y-%m-%d}: {mrr_start:,.2f} (change: {change:+.1f}%)")

    print("\nNet revenue by month:")
    for month, value in monthly_revenue(payments, MONTHS_BACK).items():
        print(f"  {month}: {value:,.2f}")

    print(f"\nChurn since {WINDOW_START:%Y-%m-%d}: {churned} of {base} ({churn_pct:.1f}%)")

    print("\nMRR by plan:")
    for plan, value in sorted(by_plan_now.items(), key=lambda item: item[1], reverse=True):  # FIXED: sorted numerically by MRR value rather than formatted string
        print(f"  {plan}: {value:,.2f}")

    print("\nTop 5 customers by net payments:")
    for customer, value in top_customers(payments).items():
        print(f"  {customer}: {value:,.2f}")

    print(f"\nOrphan payments (no subscription): {orphan_payments(payments, subs)}")


if __name__ == "__main__":
    main()
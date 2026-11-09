"""Assess coverage of goal earmarks and scheduled bills using CASH accounts."""

import csv
import json
from collections import Counter
from datetime import timedelta
from pathlib import Path

from calculate_net_worth import CASH_COLUMNS, cents, money, require
from generate_asset_prices import AS_OF_DATE
from generate_holdings import ACCOUNT_COLUMNS, read_table
from generate_goals import COLUMNS as GOAL_COLUMNS
from generate_goals import generate_goals, validate_goals
from generate_scheduled_payments import COLUMNS as PAYMENT_COLUMNS
from generate_scheduled_payments import (
    HORIZON_DAYS,
    SNAPSHOT_DATE,
    WINDOW_END,
    generate_payments,
    validate_payments,
)


WINDOW_START = (
    SNAPSHOT_DATE + timedelta(days=1)
).isoformat()

MONEY_FIELDS = [
    "eligible_cash",
    "goal_allocations",
    "scheduled_payments_30d",
    "cash_after_goals",
    "cash_after_commitments",
    "funding_shortfall",
]

COLUMNS = [
    "user_id",
    "funding_account_id",
    "as_of_date",
    "window_start",
    "window_end",
    "currency",
    *MONEY_FIELDS,
    "coverage_status",
    "data_origin",
]


def matching_records(actual, expected, columns):
    return Counter(
        tuple(r[c] for c in columns) for r in actual
    ) == Counter(
        tuple(r[c] for c in columns) for r in expected
    )


def aggregate(rows, field):
    amounts = Counter()

    for row in rows:
        amounts[row["funding_account_id"]] += cents(row[field])

    return amounts


def total(rows, field):
    return sum(
        cents(
            r[field],
            allow_negative=(field == "cash_after_commitments"),
        )
        for r in rows
    )


def calculate_coverage(cash_accounts, balances, goals, payments):
    # Aggregate detail tables separately to avoid multiplying rows.
    goal_totals = aggregate(goals, "allocated_amount")
    payment_totals = aggregate(payments, "amount")

    results = []

    for aid, account in sorted(cash_accounts.items()):
        after_goals = balances[aid] - goal_totals[aid]
        remaining = after_goals - payment_totals[aid]

        results.append({
            "user_id": account["user_id"],
            "funding_account_id": aid,
            "as_of_date": AS_OF_DATE,
            "window_start": WINDOW_START,
            "window_end": WINDOW_END.isoformat(),
            "currency": account["currency"],
            "eligible_cash": money(balances[aid]),
            "goal_allocations": money(goal_totals[aid]),
            "scheduled_payments_30d": money(payment_totals[aid]),
            "cash_after_goals": money(after_goals),
            "cash_after_commitments": money(remaining),
            "funding_shortfall": money(max(0, -remaining)),
            "coverage_status": (
                "SHORTFALL" if remaining < 0 else "COVERED"
            ),
            "data_origin": "synthetic_extension",
        })

    return results


def main():
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data" / "processed"

    output_path = data_dir / "cash_coverage_snapshots.csv"
    report_path = root / "docs" / "cash_coverage_validation.json"

    users = read_table(
        root / "data" / "interim" / "users.csv",
        ["user_id", "user_name", "archetype"],
    )
    accounts = read_table(
        data_dir / "accounts.csv",
        ACCOUNT_COLUMNS,
    )
    cash = read_table(
        data_dir / "cash_balance_snapshots.csv",
        CASH_COLUMNS,
    )
    goals = read_table(
        data_dir / "goal_snapshots.csv",
        GOAL_COLUMNS,
    )
    payments = read_table(
        data_dir / "scheduled_payments.csv",
        PAYMENT_COLUMNS,
    )

    user_ids = {r["user_id"] for r in users}
    account_ids = {r["account_id"] for r in accounts}

    require(len(user_ids) == len(users), "Duplicate user IDs.")

    require(
        len(account_ids) == len(accounts)
        and Counter(
            (r["user_id"], r["account_type"])
            for r in accounts
        )
        == Counter(
            (uid, kind)
            for uid in user_ids
            for kind in ("CASH", "INVESTMENT")
        )
        and all(
            r["account_id"]
            == f"acct_{r['user_id']}_{r['account_type'].lower()}"
            and r["currency"] == "USD"
            and r["data_origin"] == "synthetic_extension"
            for r in accounts
        ),
        "Account identities or ownership do not match the current users.",
    )

    require(
        Counter(
            (r["account_id"], r["as_of_date"])
            for r in cash
        )
        == Counter(
            (aid, AS_OF_DATE) for aid in account_ids
        )
        and all(
            r["currency"] == "USD"
            and r["data_origin"] == "synthetic_extension"
            for r in cash
        ),
        "Missing, duplicate, or invalid cash snapshots.",
    )

    balances = {
        r["account_id"]: cents(r["cash_balance"])
        for r in cash
    }
    cash_accounts = {
        r["account_id"]: r
        for r in accounts
        if r["account_type"] == "CASH"
    }

    require(
        all(validate_goals(goals, cash_accounts, balances).values()),
        "Goal validation failed.",
    )
    require(
        all(validate_payments(payments, cash_accounts).values()),
        "Payment validation failed.",
    )

    # Recreate expected records in memory to detect stale inputs.
    require(
        matching_records(
            goals,
            generate_goals(cash_accounts, balances),
            GOAL_COLUMNS,
        ),
        "Stale goals. Rerun src/generate_goals.py using the current cash balances.",
    )
    require(
        matching_records(
            payments,
            generate_payments(cash_accounts),
            PAYMENT_COLUMNS,
        ),
        "Stale payments. Rerun src/generate_scheduled_payments.py.",
    )

    snapshots = calculate_coverage(
        cash_accounts, balances, goals, payments
    )

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(snapshots)

    saved = read_table(output_path, COLUMNS)

    goal_totals = aggregate(goals, "allocated_amount")
    payment_totals = aggregate(payments, "amount")

    keys = [
        (
            r["funding_account_id"],
            r["as_of_date"],
            r["window_end"],
            r["currency"],
        )
        for r in saved
    ]

    remaining = [
        cents(r["cash_after_commitments"], True)
        for r in saved
    ]

    expected_total = (
        sum(balances[aid] for aid in cash_accounts)
        - total(goals, "allocated_amount")
        - total(payments, "amount")
    )

    checks = {
        "row_count_correct":
            len(saved) == len(users),

        "account_date_window_currency_keys_unique":
            len(keys) == len(set(keys)),

        "all_cash_accounts_included":
            {r["funding_account_id"] for r in saved}
            == set(cash_accounts),

        "all_users_included":
            {r["user_id"] for r in saved} == user_ids,

        "ownership_correct": all(
            r["funding_account_id"] in cash_accounts
            and r["user_id"]
            == cash_accounts[r["funding_account_id"]]["user_id"]
            for r in saved
        ),

        "date_window_and_currency_correct": all(
            r["as_of_date"] == AS_OF_DATE
            and r["window_start"] == WINDOW_START
            and r["window_end"] == WINDOW_END.isoformat()
            and r["currency"] == "USD"
            for r in saved
        ),

        "per_account_components_match_inputs": all(
            r["funding_account_id"] in cash_accounts
            and cents(r["eligible_cash"])
            == balances[r["funding_account_id"]]
            and cents(r["goal_allocations"])
            == goal_totals[r["funding_account_id"]]
            and cents(r["scheduled_payments_30d"])
            == payment_totals[r["funding_account_id"]]
            for r in saved
        ),

        "cash_after_goals_formula_correct": all(
            cents(r["cash_after_goals"])
            == cents(r["eligible_cash"])
            - cents(r["goal_allocations"])
            for r in saved
        ),

        "cash_after_commitments_formula_correct": all(
            value
            == cents(r["cash_after_goals"])
            - cents(r["scheduled_payments_30d"])
            for r, value in zip(saved, remaining)
        ),

        "shortfall_formula_correct": all(
            cents(r["funding_shortfall"]) == max(0, -value)
            for r, value in zip(saved, remaining)
        ),

        "coverage_status_correct": all(
            r["coverage_status"]
            == ("SHORTFALL" if value < 0 else "COVERED")
            for r, value in zip(saved, remaining)
        ),

        "component_totals_reconcile": (
            total(saved, "eligible_cash")
            == sum(balances[aid] for aid in cash_accounts)
            and total(saved, "goal_allocations")
            == total(goals, "allocated_amount")
            and total(saved, "scheduled_payments_30d")
            == total(payments, "amount")
        ),

        "signed_remaining_total_reconciles":
            sum(remaining) == expected_total,

        "synthetic_origin_recorded": all(
            r["data_origin"] == "synthetic_extension"
            for r in saved
        ),

        "csv_matches_calculated_records":
            saved == snapshots,
    }

    report = {
        "scope": "CASH-account coverage while preserving goal allocations and paying listed future bills",
        "calculation_version": "cash_coverage_v1",
        "as_of_date": AS_OF_DATE,
        "window_start": WINDOW_START,
        "window_end": WINDOW_END.isoformat(),
        "horizon_days": HORIZON_DAYS,
        "currency_note": "USD is a demonstration assumption",
        "formula": "Eligible CASH balance - goal allocations - scheduled payments in the 30-day window",
        "shortfall_rule": "Calculate max(0, -remaining) per user before summing; do not offset other users' deficits",
        "eligibility_rule": "CASH accounts only; investment-account cash and holdings excluded",
        "limitations": "No future income, goal releases, or unlisted expenses; not a complete cash forecast",
        "accounting_note": "Planning calculation only; underlying balances and net worth are not changed",
        "users_checked": len(users),
        "snapshots_checked": len(saved),
        "users_with_shortfall": sum(
            value < 0 for value in remaining
        ),
        "users_covered": sum(
            value >= 0 for value in remaining
        ),
        "totals_usd": {
            field: money(total(saved, field))
            for field in MONEY_FIELDS
        },
        "checks": checks,
        "all_checks_passed": all(checks.values()),
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)

    with report_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
        file.write("\n")

    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'}: {name}")

    require(
        report["all_checks_passed"],
        "Cash-coverage validation failed. Review the report.",
    )

    print(f"\nSaved {len(saved):,} cash-coverage snapshots.")
    print(f"All {len(checks)} cash-coverage checks passed.")
    print(
        "Users with a modeled shortfall:",
        report["users_with_shortfall"],
    )
    print(
        "Total modeled shortfall (USD):",
        report["totals_usd"]["funding_shortfall"],
    )
    print("CSV:", output_path)
    print("Report:", report_path)


if __name__ == "__main__":
    main()
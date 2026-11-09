"""Calculate opening investment values from the existing dated snapshots."""

import csv
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

from calculate_net_worth import CASH_COLUMNS, cents, money, require
from generate_assets import COLUMNS as ASSET_COLUMNS, validate_assets
from generate_asset_prices import AS_OF_DATE, PRICE_COLUMNS, validate_prices
from generate_holdings import (
    ACCOUNT_COLUMNS, HOLDING_COLUMNS, read_table, validate_holdings,
)
from value_holdings import VALUE_COLUMNS, holding_key


MONEY_FIELDS = [
    "opening_cash", "opening_holdings_value", "opening_portfolio_value",
]
COLUMNS = [
    "user_id", "account_id", "as_of_date", "currency",
    *MONEY_FIELDS, "data_origin",
]


def total(rows, field):
    return sum(cents(row[field]) for row in rows)


def main():
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data" / "processed"
    output_path = data_dir / "portfolio_opening_balances.csv"
    report_path = root / "docs" / "portfolio_opening_validation.json"

    users = read_table(
        root / "data" / "interim" / "users.csv",
        ["user_id", "user_name", "archetype"],
    )
    accounts = read_table(data_dir / "accounts.csv", ACCOUNT_COLUMNS)
    cash = read_table(data_dir / "cash_balance_snapshots.csv", CASH_COLUMNS)
    assets = read_table(data_dir / "assets.csv", ASSET_COLUMNS)
    prices = read_table(data_dir / "asset_prices.csv", PRICE_COLUMNS)
    holdings = read_table(data_dir / "holding_snapshots.csv", HOLDING_COLUMNS)
    values = read_table(data_dir / "holding_valuations.csv", VALUE_COLUMNS)

    # Confirm account ownership before selecting the investment accounts.
    user_ids = {row["user_id"] for row in users}
    require(len(user_ids) == len(users), "Duplicate user IDs.")
    account_lookup = {row["account_id"]: row for row in accounts}
    expected_pairs = Counter(
        (uid, kind) for uid in user_ids for kind in ("CASH", "INVESTMENT")
    )
    require(
        len(account_lookup) == len(accounts)
        and Counter((r["user_id"], r["account_type"]) for r in accounts)
        == expected_pairs
        and all(
            r["account_id"] == f"acct_{r['user_id']}_{r['account_type'].lower()}"
            and r["currency"] == "USD"
            and r["data_origin"] == "synthetic_extension"
            for r in accounts
        ),
        "Account identities or ownership do not match the current users.",
    )
    investments = {
        aid: row for aid, row in account_lookup.items()
        if row["account_type"] == "INVESTMENT"
    }

    # Validate the complete cash table, then select investment-account cash.
    require(
        Counter((r["account_id"], r["as_of_date"]) for r in cash)
        == Counter((aid, AS_OF_DATE) for aid in account_lookup),
        "Missing, duplicate, or wrongly dated cash snapshots.",
    )
    require(
        all(
            r["currency"] == "USD"
            and r["data_origin"] == "synthetic_extension"
            for r in cash
        ),
        "Invalid cash currency or origin.",
    )
    all_cash = {r["account_id"]: cents(r["cash_balance"]) for r in cash}
    investment_cash = {aid: all_cash[aid] for aid in investments}

    # Revalidate holdings and prices instead of trusting an old report.
    require(all(validate_assets(assets).values()), "Asset validation failed.")
    assets_by_id = {r["asset_id"]: r for r in assets}
    require(
        all(validate_prices(prices, assets_by_id).values()),
        "Price validation failed.",
    )
    price_lookup = {
        (r["asset_id"], r["price_date"], r["quote_currency"]): r
        for r in prices
    }
    require(
        all(validate_holdings(
            holdings, investments, assets_by_id, set(price_lookup)
        ).values()),
        "Holding validation failed.",
    )
    require(
        Counter(holding_key(r) for r in values)
        == Counter(holding_key(r) for r in holdings),
        "Valuations are missing, duplicated, or linked to different holdings.",
    )

    # Independently recompute values from whole units and integer price cents.
    expected_by_holding = {}
    holdings_by_account = dict.fromkeys(investments, 0)
    holding_lookup = {holding_key(r): r for r in holdings}
    for row in holdings:
        price = price_lookup[(row["asset_id"], row["as_of_date"], "USD")]
        value = int(Decimal(row["quantity"])) * cents(price["price"])
        expected_by_holding[holding_key(row)] = value
        holdings_by_account[row["account_id"]] += value

    for row in values:
        key = holding_key(row)
        price = price_lookup[(row["asset_id"], row["as_of_date"], "USD")]
        require(
            row["currency"] == "USD"
            and row["data_origin"] == "synthetic_extension"
            and row["quantity"] == holding_lookup[key]["quantity"]
            and cents(row["unit_price"]) == cents(price["price"])
            and cents(row["holding_value"]) == expected_by_holding[key],
            "Stale or incorrect valuations. Rerun src/value_holdings.py.",
        )

    # One row per investment account; aggregate holdings before adding cash.
    snapshots = []
    for aid in sorted(investments):
        snapshots.append({
            "user_id": investments[aid]["user_id"],
            "account_id": aid,
            "as_of_date": AS_OF_DATE,
            "currency": "USD",
            "opening_cash": money(investment_cash[aid]),
            "opening_holdings_value": money(holdings_by_account[aid]),
            "opening_portfolio_value": money(
                investment_cash[aid] + holdings_by_account[aid]
            ),
            "data_origin": "synthetic_extension",
        })

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(snapshots)
    saved = read_table(output_path, COLUMNS)
    cash_total = sum(investment_cash.values())
    holdings_total = total(values, "holding_value")
    checks = {
        "one_row_per_investment_account": (
            Counter(r["account_id"] for r in saved)
            == Counter(investments.keys())
        ),
        "all_users_included": {r["user_id"] for r in saved} == user_ids,
        "owners_match_accounts": all(
            r["user_id"] == investments[r["account_id"]]["user_id"]
            for r in saved
        ),
        "opening_date_and_currency_correct": all(
            r["as_of_date"] == AS_OF_DATE and r["currency"] == "USD"
            for r in saved
        ),
        "per_account_cash_matches_input": all(
            cents(r["opening_cash"]) == investment_cash[r["account_id"]]
            for r in saved
        ),
        "per_account_holdings_values_reconcile": all(
            cents(r["opening_holdings_value"])
            == holdings_by_account[r["account_id"]]
            for r in saved
        ),
        "portfolio_value_formula_correct": all(
            cents(r["opening_portfolio_value"])
            == cents(r["opening_cash"]) + cents(r["opening_holdings_value"])
            for r in saved
        ),
        "opening_cash_total_reconciles": total(saved, "opening_cash") == cash_total,
        "opening_holdings_total_reconciles": (
            total(saved, "opening_holdings_value") == holdings_total
        ),
        "opening_portfolio_total_reconciles": (
            total(saved, "opening_portfolio_value") == cash_total + holdings_total
        ),
        "synthetic_origin_recorded": all(
            r["data_origin"] == "synthetic_extension" for r in saved
        ),
        "csv_matches_calculated_records": saved == snapshots,
    }
    report = {
        "scope": "Opening investment-account values from existing synthetic snapshots",
        "calculation_version": "portfolio_opening_v1",
        "as_of_date": AS_OF_DATE,
        "currency": "USD",
        "formula": "Investment-account cash + same-date holdings value",
        "cash_rule": "Include only cash in INVESTMENT accounts, once per account",
        "valuation_control": "Verify every holding using whole units and integer price cents",
        "limitations": "Opening values are not contributions, cost basis, profit, or returns",
        "users_checked": len(users),
        "investment_accounts_checked": len(investments),
        "holdings_checked": len(holdings),
        "snapshots_checked": len(saved),
        "totals_usd": {field: money(total(saved, field)) for field in MONEY_FIELDS},
        "checks": checks,
        "all_checks_passed": all(checks.values()),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
        file.write("\n")

    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'}: {name}")
    require(report["all_checks_passed"], "Opening validation failed. Review the report.")
    print(f"\nSaved {len(saved):,} portfolio opening balances for {AS_OF_DATE}.")
    print(f"All {len(checks)} portfolio-opening checks passed.")
    print("Combined opening portfolio value (USD):",
          report["totals_usd"]["opening_portfolio_value"])
    print("CSV:", output_path)
    print("Report:", report_path)


if __name__ == "__main__":
    main()
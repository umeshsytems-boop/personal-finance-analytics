"""Combine validated financial snapshots into one modeled net worth per user."""

import csv
import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

from generate_assets import COLUMNS as ASSET_COLUMNS, validate_assets
from generate_asset_prices import AS_OF_DATE, PRICE_COLUMNS, validate_prices
from generate_holdings import ACCOUNT_COLUMNS, HOLDING_COLUMNS, read_table, validate_holdings
from generate_liabilities import AS_OF_DATE as LIABILITY_DATE
from generate_liabilities import COLUMNS as LIABILITY_COLUMNS
from generate_liabilities import generate_liabilities, validate_liabilities
from value_holdings import VALUE_COLUMNS, holding_key


CASH_COLUMNS = ["account_id", "as_of_date", "currency", "cash_balance", "data_origin"]
MONEY_FIELDS = ["total_cash", "total_investments", "total_assets", "total_liabilities", "net_worth"]
COLUMNS = ["user_id", "as_of_date", "currency", *MONEY_FIELDS, "data_origin"]


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def cents(value, allow_negative=False):
    try:
        amount = Decimal(value)
        if (
            amount.is_finite()
            and amount == amount.quantize(Decimal("0.01"))
            and (allow_negative or amount >= 0)
        ):
            return int(amount * 100)
    except (InvalidOperation, ValueError, TypeError):
        pass
    raise SystemExit(f"Invalid monetary value: {value!r}")


def money(amount_in_cents):
    return f"{Decimal(amount_in_cents) / 100:.2f}"


def total(rows, column):
    return sum(cents(r[column], allow_negative=(column == "net_worth")) for r in rows)


def main():
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data" / "processed"
    output_path = data_dir / "net_worth_snapshots.csv"
    report_path = root / "docs" / "net_worth_validation.json"

    users = read_table(root / "data" / "interim" / "users.csv", ["user_id", "user_name", "archetype"])
    accounts = read_table(data_dir / "accounts.csv", ACCOUNT_COLUMNS)
    cash = read_table(data_dir / "cash_balance_snapshots.csv", CASH_COLUMNS)
    assets = read_table(data_dir / "assets.csv", ASSET_COLUMNS)
    prices = read_table(data_dir / "asset_prices.csv", PRICE_COLUMNS)
    holdings = read_table(data_dir / "holding_snapshots.csv", HOLDING_COLUMNS)
    values = read_table(data_dir / "holding_valuations.csv", VALUE_COLUMNS)

    # Debt snapshots can legitimately contain only a header.
    with (data_dir / "liability_snapshots.csv").open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        liabilities = list(reader)
        require(reader.fieldnames == LIABILITY_COLUMNS, "Unexpected liability columns.")

    user_ids = {r["user_id"] for r in users}
    require(len(user_ids) == len(users), "Duplicate user IDs.")
    account_lookup = {r["account_id"]: r for r in accounts}
    expected_pairs = {(uid, kind): 1 for uid in user_ids for kind in ("CASH", "INVESTMENT")}
    require(
        len(account_lookup) == len(accounts)
        and Counter((r["user_id"], r["account_type"]) for r in accounts) == Counter(expected_pairs)
        and all(
            r["account_id"] == f"acct_{r['user_id']}_{r['account_type'].lower()}"
            and r["currency"] == "USD" and r["data_origin"] == "synthetic_extension"
            for r in accounts
        ),
        "Account identities or ownership do not match the current users.",
    )

    # Require one cash snapshot per account, including investment-account cash.
    require(
        Counter((r["account_id"], r["as_of_date"]) for r in cash)
        == Counter((aid, AS_OF_DATE) for aid in account_lookup),
        "Missing, duplicate, or wrongly dated cash snapshots.",
    )
    require(all(r["currency"] == "USD" and r["data_origin"] == "synthetic_extension" for r in cash),
            "Invalid cash currency or origin.")

    require(all(validate_assets(assets).values()), "Asset validation failed.")
    assets_by_id = {r["asset_id"]: r for r in assets}
    require(all(validate_prices(prices, assets_by_id).values()), "Price validation failed.")
    investments = {aid: r for aid, r in account_lookup.items() if r["account_type"] == "INVESTMENT"}
    price_lookup = {(r["asset_id"], r["price_date"], r["quote_currency"]): r for r in prices}
    require(all(validate_holdings(holdings, investments, assets_by_id, set(price_lookup)).values()),
            "Holding validation failed.")
    require(Counter(holding_key(r) for r in values) == Counter(holding_key(r) for r in holdings),
            "Valuations are missing, duplicated, or linked to different holdings.")
    holding_lookup = {holding_key(r): r for r in holdings}
    for row in values:
        holding = holding_lookup[holding_key(row)]
        price = price_lookup[(row["asset_id"], row["as_of_date"], "USD")]["price"]
        require(
            row["currency"] == "USD" and row["data_origin"] == "synthetic_extension"
            and row["quantity"] == holding["quantity"]
            and cents(row["unit_price"]) == cents(price)
            and cents(row["holding_value"]) == int(Decimal(holding["quantity"])) * cents(price),
            "Stale or incorrect valuations. Rerun src/value_holdings.py.",
        )

    require(AS_OF_DATE == LIABILITY_DATE, "Snapshot dates differ between generators.")
    require(all(validate_liabilities(liabilities, user_ids).values()), "Liability validation failed.")
    expected_debts = generate_liabilities(user_ids)
    require(
        Counter(tuple(r[c] for c in LIABILITY_COLUMNS) for r in liabilities)
        == Counter(tuple(r[c] for c in LIABILITY_COLUMNS) for r in expected_debts),
        "Incomplete or stale simulated debts. Rerun src/generate_liabilities.py.",
    )

    # Aggregate each component separately to avoid multiplying rows in joins.
    cash_by_user = dict.fromkeys(user_ids, 0)
    investments_by_user = dict.fromkeys(user_ids, 0)
    debt_by_user = dict.fromkeys(user_ids, 0)
    for row in cash:
        cash_by_user[account_lookup[row["account_id"]]["user_id"]] += cents(row["cash_balance"])
    for row in values:
        investments_by_user[account_lookup[row["account_id"]]["user_id"]] += cents(row["holding_value"])
    for row in liabilities:
        debt_by_user[row["user_id"]] += cents(row["outstanding_balance"])

    snapshots = []
    for uid in sorted(user_ids):
        assets_total = cash_by_user[uid] + investments_by_user[uid]
        snapshots.append({
            "user_id": uid,
            "as_of_date": AS_OF_DATE,
            "currency": "USD",
            "total_cash": money(cash_by_user[uid]),
            "total_investments": money(investments_by_user[uid]),
            "total_assets": money(assets_total),
            "total_liabilities": money(debt_by_user[uid]),
            "net_worth": money(assets_total - debt_by_user[uid]),
            "data_origin": "synthetic_extension",
        })

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(snapshots)
    saved = read_table(output_path, COLUMNS)
    keys = [(r["user_id"], r["as_of_date"], r["currency"]) for r in saved]
    zero_debt_users = user_ids - {r["user_id"] for r in liabilities}
    expected_net_total = total(cash, "cash_balance") + total(values, "holding_value") - total(liabilities, "outstanding_balance")
    checks = {
        "user_count_correct": len(saved) == len(users),
        "user_date_currency_keys_unique": len(keys) == len(set(keys)),
        "all_users_included": {r["user_id"] for r in saved} == user_ids,
        "date_and_currency_correct": all(r["as_of_date"] == AS_OF_DATE and r["currency"] == "USD" for r in saved),
        "asset_formula_correct": all(cents(r["total_assets"]) == cents(r["total_cash"]) + cents(r["total_investments"]) for r in saved),
        "net_worth_formula_correct": all(cents(r["net_worth"], True) == cents(r["total_assets"]) - cents(r["total_liabilities"]) for r in saved),
        "cash_total_reconciles": total(saved, "total_cash") == total(cash, "cash_balance"),
        "investment_total_reconciles": total(saved, "total_investments") == total(values, "holding_value"),
        "liability_total_reconciles": total(saved, "total_liabilities") == total(liabilities, "outstanding_balance"),
        "net_worth_total_reconciles": total(saved, "net_worth") == expected_net_total,
        "zero_debt_users_preserved": {r["user_id"] for r in saved if cents(r["total_liabilities"]) == 0} == zero_debt_users,
        "synthetic_origin_recorded": all(r["data_origin"] == "synthetic_extension" for r in saved),
        "csv_matches_generated_records": saved == snapshots,
    }
    report = {
        "scope": "Per-user modeled net worth from simulated financial assets and debts",
        "calculation_version": "net_worth_v1",
        "as_of_date": AS_OF_DATE,
        "currency": "USD",
        "formula": "Total cash + investment holdings value - total liabilities",
        "cash_rule": "Include cash in CASH and INVESTMENT accounts exactly once",
        "debt_coverage_rule": "Verify the complete synthetic debt snapshot before assigning zero debt",
        "limitations": "One simulated date; excludes unmodeled assets and debts; not investment performance",
        "users_checked": len(users),
        "snapshots_checked": len(saved),
        "users_with_zero_modeled_debt": len(zero_debt_users),
        "users_with_negative_net_worth": sum(cents(r["net_worth"], True) < 0 for r in saved),
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
    require(report["all_checks_passed"], "Net-worth validation failed. Review the report.")
    print(f"\nSaved {len(saved):,} net-worth snapshots for {AS_OF_DATE}.")
    print(f"All {len(checks)} net-worth checks passed.")
    print("Combined modeled net worth (USD):", report["totals_usd"]["net_worth"])
    print("Users with negative modeled net worth:", report["users_with_negative_net_worth"])
    print("CSV:", output_path)
    print("Report:", report_path)


if __name__ == "__main__":
    main()
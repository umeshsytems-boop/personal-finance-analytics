"""Value simulated holdings using prices for the same asset, date, and currency."""

import csv
import json
from collections import Counter
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from generate_assets import COLUMNS as ASSET_COLUMNS, validate_assets
from generate_asset_prices import AS_OF_DATE, PRICE_COLUMNS, validate_prices
from generate_holdings import (
    ACCOUNT_COLUMNS, HOLDING_COLUMNS, read_table, validate_holdings,
)


CENT = Decimal("0.01")
VALUE_COLUMNS = [
    "account_id", "asset_id", "as_of_date", "currency",
    "quantity", "unit_price", "holding_value", "data_origin",
]


def holding_key(row):
    return row["account_id"], row["asset_id"], row["as_of_date"]


def calculate_value(quantity, price):
    return (Decimal(quantity) * Decimal(price)).quantize(CENT, rounding=ROUND_HALF_UP)


def value_in_cents(value):
    try:
        amount = Decimal(value)
        if amount.is_finite() and amount > 0 and amount == amount.quantize(CENT):
            return int(amount * 100)
    except (InvalidOperation, ValueError, TypeError):
        pass
    return None


def main():
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data" / "processed"
    output_path = data_dir / "holding_valuations.csv"
    report_path = root / "docs" / "valuation_report.json"

    accounts = read_table(data_dir / "accounts.csv", ACCOUNT_COLUMNS)
    assets = read_table(data_dir / "assets.csv", ASSET_COLUMNS)
    prices = read_table(data_dir / "asset_prices.csv", PRICE_COLUMNS)
    holdings = read_table(data_dir / "holding_snapshots.csv", HOLDING_COLUMNS)

    account_ids = [r["account_id"] for r in accounts]
    if len(account_ids) != len(set(account_ids)) or any(
        r["account_type"] not in {"CASH", "INVESTMENT"}
        or r["currency"] != "USD"
        or r["data_origin"] != "synthetic_extension"
        for r in accounts
    ):
        raise SystemExit("Account validation failed. No outputs were written.")
    if not all(validate_assets(assets).values()):
        raise SystemExit("Asset validation failed. No outputs were written.")
    assets_by_id = {r["asset_id"]: r for r in assets}
    if not all(validate_prices(prices, assets_by_id).values()):
        raise SystemExit("Price validation failed. No outputs were written.")

    investments = {
        r["account_id"]: r for r in accounts if r["account_type"] == "INVESTMENT"
    }
    price_lookup = {
        (r["asset_id"], r["price_date"], r["quote_currency"]): r for r in prices
    }
    if not all(validate_holdings(holdings, investments, assets_by_id, set(price_lookup)).values()):
        raise SystemExit("Holding validation failed. No outputs were written.")

    valuations = []
    expected_cents = {}
    for holding in sorted(holdings, key=holding_key):
        currency = investments[holding["account_id"]]["currency"]
        price_key = (holding["asset_id"], holding["as_of_date"], currency)
        price = price_lookup[price_key]["price"]
        quantity = holding["quantity"]
        valuations.append({
            "account_id": holding["account_id"],
            "asset_id": holding["asset_id"],
            "as_of_date": holding["as_of_date"],
            "currency": currency,
            "quantity": quantity,
            "unit_price": f"{Decimal(price):.2f}",
            "holding_value": f"{calculate_value(quantity, price):.2f}",
            "data_origin": "synthetic_extension",
        })
        # Independent control for this model's whole units and cent-based prices.
        expected_cents[holding_key(holding)] = (
            int(Decimal(quantity)) * int(Decimal(price) * 100)
        )

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=VALUE_COLUMNS)
        writer.writeheader()
        writer.writerows(valuations)

    saved = read_table(output_path, VALUE_COLUMNS)
    saved_keys = [holding_key(row) for row in saved]
    saved_cents = [value_in_cents(row["holding_value"]) for row in saved]
    amounts_valid = all(cents is not None for cents in saved_cents)
    expected_total_cents = sum(expected_cents.values())
    actual_total_cents = sum(saved_cents) if amounts_valid else None
    checks = {
        "valuation_count_matches_holdings": len(saved) == len(holdings),
        "holding_keys_preserved": Counter(saved_keys) == Counter(holding_key(r) for r in holdings),
        "valuation_keys_unique": len(saved_keys) == len(set(saved_keys)),
        "individual_values_reconcile_in_cents": all(
            key in expected_cents and cents == expected_cents[key]
            for key, cents in zip(saved_keys, saved_cents)
        ),
        "total_value_reconciles_in_cents": actual_total_cents == expected_total_cents,
        "usd_currency_applied": all(r["currency"] == "USD" for r in saved),
        "synthetic_origin_recorded": all(r["data_origin"] == "synthetic_extension" for r in saved),
        "csv_matches_generated_records": saved == valuations,
    }
    report = {
        "scope": "Valuation of simulated holdings; excludes cash and liabilities",
        "calculation_version": "holding_values_v1",
        "as_of_date": AS_OF_DATE,
        "valuation_rule": "Quantity multiplied by the same-date, same-currency unit price",
        "rounding_rule": "ROUND_HALF_UP to two decimal places per holding",
        "control_rule": "Whole units multiplied by integer price cents",
        "limitations": "Snapshot values do not measure cost basis, profit, or investment return",
        "holdings_checked": len(holdings),
        "valuations_checked": len(saved),
        "currency": "USD",
        "total_holding_value": (
            f"{Decimal(actual_total_cents) / 100:.2f}" if amounts_valid else None
        ),
        "expected_total_value": f"{Decimal(expected_total_cents) / 100:.2f}",
        "checks": checks,
        "all_checks_passed": all(checks.values()),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
        file.write("\n")

    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'}: {name}")
    if not report["all_checks_passed"]:
        raise SystemExit("Valuation validation failed. Review the report.")
    print(f"\nValued {len(saved):,} holdings for {AS_OF_DATE}.")
    print(f"All {len(checks)} valuation checks passed.")
    print("Total simulated holding value (USD):", report["total_holding_value"])
    print("CSV:", output_path)
    print("Report:", report_path)


if __name__ == "__main__":
    main()
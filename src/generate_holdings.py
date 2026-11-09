"""Create simulated holdings linked to investment accounts and dated prices."""

import csv
import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from random import Random

from generate_assets import COLUMNS as ASSET_COLUMNS
from generate_assets import clean_text, validate_assets
from generate_asset_prices import AS_OF_DATE, PRICE_COLUMNS, validate_prices


BASE_SEED = 42
HOLDINGS_PER_ACCOUNT = 3
ACCOUNT_COLUMNS = [
    "account_id", "user_id", "account_name",
    "account_type", "currency", "data_origin",
]
HOLDING_COLUMNS = [
    "account_id", "asset_id", "as_of_date", "quantity", "data_origin",
]


def read_table(path, columns):
    if not path.is_file():
        raise SystemExit(f"Missing {path.name}. Complete the earlier generation steps.")
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        if reader.fieldnames != columns:
            raise SystemExit(f"Unexpected columns in {path.name}.")
    if not rows or any(
        set(row) != set(columns)
        or not all(clean_text(row[column]) for column in columns)
        for row in rows
    ):
        raise SystemExit(f"Empty table or invalid fields in {path.name}.")
    return rows


def valid_quantity(value):
    try:
        quantity = Decimal(value)
        return (
            quantity.is_finite()
            and 1 <= quantity <= 100
            and quantity == quantity.to_integral_value()
        )
    except (InvalidOperation, ValueError, TypeError):
        return False


def validate_holdings(rows, investments, assets_by_id, price_keys):
    counts = Counter(row["account_id"] for row in rows)
    keys = [(r["account_id"], r["asset_id"], r["as_of_date"]) for r in rows]
    return {
        "holding_count_correct": len(rows) == len(investments) * HOLDINGS_PER_ACCOUNT,
        "account_asset_date_keys_unique": len(keys) == len(set(keys)),
        "investment_accounts_covered_exactly": set(counts) == set(investments),
        "three_holdings_per_account": all(
            counts[account_id] == HOLDINGS_PER_ACCOUNT for account_id in investments
        ),
        "assets_exist": all(r["asset_id"] in assets_by_id for r in rows),
        "snapshot_dates_correct": all(r["as_of_date"] == AS_OF_DATE for r in rows),
        "quantities_follow_generation_rules": all(
            valid_quantity(r["quantity"]) for r in rows
        ),
        "same_date_currency_prices_exist": all(
            (r["asset_id"], r["as_of_date"],
             investments.get(r["account_id"], {}).get("currency")) in price_keys
            for r in rows
        ),
        "synthetic_origin_recorded": all(
            r["data_origin"] == "synthetic_extension" for r in rows
        ),
    }


def main():
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data" / "processed"
    output_path = data_dir / "holding_snapshots.csv"
    report_path = root / "docs" / "holding_validation.json"

    accounts = read_table(data_dir / "accounts.csv", ACCOUNT_COLUMNS)
    assets = read_table(data_dir / "assets.csv", ASSET_COLUMNS)
    prices = read_table(data_dir / "asset_prices.csv", PRICE_COLUMNS)

    account_ids = [r["account_id"] for r in accounts]
    if len(account_ids) != len(set(account_ids)) or any(
        r["account_type"] not in {"CASH", "INVESTMENT"}
        or r["currency"] != "USD"
        or r["data_origin"] != "synthetic_extension"
        for r in accounts
    ):
        raise SystemExit("Invalid account registry. No outputs were written.")

    if not all(validate_assets(assets).values()):
        raise SystemExit("Asset validation failed. No outputs were written.")
    assets_by_id = {r["asset_id"]: r for r in assets}
    if not all(validate_prices(prices, assets_by_id).values()):
        raise SystemExit("Price validation failed. No outputs were written.")

    investments = {
        r["account_id"]: r for r in accounts if r["account_type"] == "INVESTMENT"
    }
    if not investments:
        raise SystemExit("No investment accounts found.")
    price_keys = {
        (r["asset_id"], r["price_date"], r["quote_currency"]) for r in prices
    }

    holdings = []
    for account_id in sorted(investments):
        rng = Random(f"holdings_v1|{BASE_SEED}|{account_id}|{AS_OF_DATE}")
        selected_assets = rng.sample(sorted(assets_by_id), HOLDINGS_PER_ACCOUNT)
        for asset_id in sorted(selected_assets):
            holdings.append({
                "account_id": account_id,
                "asset_id": asset_id,
                "as_of_date": AS_OF_DATE,
                "quantity": str(rng.randint(1, 100)),
                "data_origin": "synthetic_extension",
            })

    if not all(validate_holdings(holdings, investments, assets_by_id, price_keys).values()):
        raise SystemExit("Generated holdings failed validation. No outputs were written.")

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=HOLDING_COLUMNS)
        writer.writeheader()
        writer.writerows(holdings)

    saved = read_table(output_path, HOLDING_COLUMNS)
    checks = validate_holdings(saved, investments, assets_by_id, price_keys)
    checks["csv_matches_generated_records"] = saved == holdings
    report = {
        "scope": "Simulated end-of-day holdings linked to accounts, assets, and prices",
        "generator_version": "holdings_v1",
        "as_of_date": AS_OF_DATE,
        "base_seed": BASE_SEED,
        "seed_rule": "Version, base seed, account_id, and snapshot date per account",
        "selection_rule": "Three distinct assets per investment account",
        "quantity_rule": "1 to 100 whole units per holding, including demo crypto",
        "limitations": "Assumed positions; not reconstructed from trades or source transactions",
        "cash_note": "Cash snapshots remain separate and unchanged",
        "ownership_note": "User ownership relies on the previously validated account registry",
        "investment_accounts_checked": len(investments),
        "holdings_checked": len(saved),
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
        raise SystemExit("Holding validation failed. Review the report.")
    print(f"\nSaved {len(saved):,} holdings for {len(investments):,} investment accounts.")
    print(f"All {len(checks)} holding checks passed.")
    print("CSV:", output_path)
    print("Report:", report_path)


if __name__ == "__main__":
    main()
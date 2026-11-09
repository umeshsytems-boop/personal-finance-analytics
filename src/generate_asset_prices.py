"""Create one dated, simulated unit price for each fictional asset."""

import csv
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from generate_assets import COLUMNS as ASSET_COLUMNS
from generate_assets import clean_text, validate_assets


AS_OF_DATE = "2024-12-28"
PRICE_COLUMNS = [
    "asset_id", "price_date", "quote_currency", "price", "data_origin",
]

# Arbitrary USD demonstration prices per unit; these are not market quotes.
# Fixed values make reruns reproducible without a random seed.
PRICES_USD = {
    "demo_stock_01": "125.50",
    "demo_stock_02": "82.25",
    "demo_etf_01": "100.00",
    "demo_etf_02": "95.75",
    "demo_crypto_01": "250.00",
    "demo_crypto_02": "12.50",
}


def valid_price(value):
    try:
        price = Decimal(value)
        return (
            price.is_finite()
            and price > 0
            and price == price.quantize(Decimal("0.01"))
        )
    except (InvalidOperation, ValueError, TypeError):
        return False


def validate_prices(rows, assets_by_id):
    asset_ids = [row.get("asset_id") for row in rows]
    keys = [
        (row.get("asset_id"), row.get("price_date"), row.get("quote_currency"))
        for row in rows
    ]
    return {
        "schema_and_required_fields_valid": bool(rows) and all(
            set(row) == set(PRICE_COLUMNS)
            and all(clean_text(row[column]) for column in PRICE_COLUMNS)
            for row in rows
        ),
        "price_count_correct": len(rows) == len(assets_by_id),
        "asset_date_currency_keys_unique": len(keys) == len(set(keys)),
        "all_assets_covered": set(asset_ids) == set(assets_by_id),
        "price_dates_correct": all(
            row.get("price_date") == AS_OF_DATE for row in rows
        ),
        "currencies_match_assets": all(
            row.get("quote_currency")
            == assets_by_id.get(row.get("asset_id"), {}).get("quote_currency")
            for row in rows
        ),
        "prices_positive_with_cent_precision": all(
            valid_price(row.get("price")) for row in rows
        ),
        "synthetic_origin_recorded": all(
            row.get("data_origin") == "synthetic_extension" for row in rows
        ),
    }


def main():
    project_root = Path(__file__).resolve().parents[1]
    input_path = project_root / "data" / "processed" / "assets.csv"
    output_path = project_root / "data" / "processed" / "asset_prices.csv"
    report_path = project_root / "docs" / "asset_price_validation.json"

    if not input_path.is_file():
        raise SystemExit("Missing assets.csv. Run src/generate_assets.py first.")

    with input_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        input_columns = reader.fieldnames
        assets = list(reader)

    if input_columns != ASSET_COLUMNS or not all(validate_assets(assets).values()):
        raise SystemExit("Asset catalog validation failed. No outputs were written.")

    assets_by_id = {row["asset_id"]: row for row in assets}
    if set(assets_by_id) != set(PRICES_USD):
        raise SystemExit("Asset IDs do not match the demonstration price definitions.")

    prices = []
    for asset_id in sorted(assets_by_id):
        prices.append({
            "asset_id": asset_id,
            "price_date": AS_OF_DATE,
            "quote_currency": assets_by_id[asset_id]["quote_currency"],
            "price": PRICES_USD[asset_id],
            "data_origin": "synthetic_extension",
        })

    if not all(validate_prices(prices, assets_by_id).values()):
        raise SystemExit("Invalid price definitions. No outputs were written.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=PRICE_COLUMNS)
        writer.writeheader()
        writer.writerows(prices)

    with output_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        saved_columns = reader.fieldnames
        saved = list(reader)

    checks = validate_prices(saved, assets_by_id)
    checks["csv_matches_generated_records"] = (
        saved_columns == PRICE_COLUMNS and saved == prices
    )
    report = {
        "scope": "Simulated end-of-day unit prices for fictional assets",
        "generator_version": "asset_prices_v1",
        "as_of_date": AS_OF_DATE,
        "generation_rule": "Fixed arbitrary USD prices per asset; no randomness",
        "prices_usd": PRICES_USD,
        "limitations": "Not historical market quotes; one date cannot measure returns",
        "assets_checked": len(assets),
        "prices_checked": len(saved),
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
        raise SystemExit("Price validation failed. Review the report.")
    print(f"\nSaved {len(saved)} simulated prices for {AS_OF_DATE}.")
    print(f"All {len(checks)} price checks passed.")
    print("CSV:", output_path)
    print("Report:", report_path)


if __name__ == "__main__":
    main()
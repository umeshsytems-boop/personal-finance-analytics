"""Create a fictional asset catalog for the personal-finance demonstration."""

import csv
import json
from collections import Counter
from pathlib import Path


COLUMNS = [
    "asset_id", "symbol", "asset_name", "asset_type",
    "asset_class", "quote_currency", "data_origin",
]

# These names and symbols are fictional, not actual market listings.
# Fixed IDs keep each asset's identity stable if its display name changes.
ASSET_DEFINITIONS = [
    ("demo_stock_01", "DEMO_TECH", "Demo Technology Company", "STOCK", "EQUITY"),
    ("demo_stock_02", "DEMO_HEALTH", "Demo Healthcare Company", "STOCK", "EQUITY"),
    ("demo_etf_01", "DEMO_EQETF", "Demo Equity ETF", "ETF", "EQUITY"),
    ("demo_etf_02", "DEMO_BONDETF", "Demo Bond ETF", "ETF", "FIXED_INCOME"),
    ("demo_crypto_01", "DEMO_COIN_A", "Demo Coin Alpha", "CRYPTO", "CRYPTO"),
    ("demo_crypto_02", "DEMO_COIN_B", "Demo Coin Beta", "CRYPTO", "CRYPTO"),
]

EXPECTED_TYPE_COUNTS = {"STOCK": 2, "ETF": 2, "CRYPTO": 2}

ALLOWED_CLASSES = {
    "STOCK": {"EQUITY"},
    "ETF": {"EQUITY", "FIXED_INCOME"},
    "CRYPTO": {"CRYPTO"},
}


def clean_text(value):
    return (
        isinstance(value, str)
        and bool(value.strip())
        and value == value.strip()
    )


def validate_assets(rows):
    asset_ids = [row.get("asset_id") for row in rows]
    symbols = [row.get("symbol") for row in rows]

    return {
        "schema_and_required_fields_valid": bool(rows) and all(
            set(row) == set(COLUMNS)
            and all(clean_text(row[column]) for column in COLUMNS)
            for row in rows
        ),
        "expected_asset_type_counts": (
            dict(Counter(row.get("asset_type") for row in rows))
            == EXPECTED_TYPE_COUNTS
        ),
        "asset_ids_unique": len(asset_ids) == len(set(asset_ids)),
        "symbols_unique_in_demo_catalog": len(symbols) == len(set(symbols)),
        "asset_type_class_pairs_valid": all(
            row.get("asset_class")
            in ALLOWED_CLASSES.get(row.get("asset_type"), set())
            for row in rows
        ),
        "usd_quote_assumption_applied": all(
            row.get("quote_currency") == "USD" for row in rows
        ),
        "synthetic_assets_labeled": all(
            row.get("data_origin") == "synthetic_extension"
            and clean_text(row.get("asset_id"))
            and row["asset_id"].startswith("demo_")
            and clean_text(row.get("symbol"))
            and row["symbol"].startswith("DEMO_")
            for row in rows
        ),
    }


def main():
    project_root = Path(__file__).resolve().parents[1]
    output_path = project_root / "data" / "processed" / "assets.csv"
    report_path = project_root / "docs" / "asset_validation.json"

    assets = []

    for asset_id, symbol, name, kind, asset_class in ASSET_DEFINITIONS:
        assets.append({
            "asset_id": asset_id,
            "symbol": symbol,
            "asset_name": name,
            "asset_type": kind,
            "asset_class": asset_class,
            "quote_currency": "USD",  # Demonstration assumption.
            "data_origin": "synthetic_extension",
        })

    if not all(validate_assets(assets).values()):
        raise SystemExit(
            "Invalid asset definitions. No output files were written."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(assets)

    # Read the exported CSV back to check what was actually saved.
    with output_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        saved_columns = reader.fieldnames
        saved = list(reader)

    checks = validate_assets(saved)
    checks["csv_matches_generated_records"] = (
        saved_columns == COLUMNS and saved == assets
    )

    report = {
        "scope": (
            "Fictional asset reference catalog; "
            "excludes prices and user holdings"
        ),
        "generator_version": "assets_v1",
        "generation_rule": (
            "Six explicitly defined demo assets; fixed IDs; no randomness"
        ),
        "currency_note": (
            "USD is the assumed quote currency for future simulated prices"
        ),
        "classification_note": (
            "Asset type describes the instrument; "
            "asset class describes its modeled exposure"
        ),
        "symbols_note": (
            "DEMO_ symbols are fictional display labels; "
            "join tables using asset_id"
        ),
        "assets_checked": len(saved),
        "asset_type_counts": dict(
            Counter(row["asset_type"] for row in saved)
        ),
        "asset_class_counts": dict(
            Counter(row["asset_class"] for row in saved)
        ),
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
        raise SystemExit("Asset validation failed. Review the report.")

    print(f"\nSaved {len(saved)} fictional assets: 2 STOCK, 2 ETF, 2 CRYPTO.")
    print(f"All {len(checks)} asset checks passed.")
    print("CSV:", output_path)
    print("Report:", report_path)


if __name__ == "__main__":
    main()
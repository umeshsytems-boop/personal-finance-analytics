"""Generate reproducible daily prices for the fictional asset catalog."""

import csv
import json
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from random import Random

from generate_assets import COLUMNS as ASSET_COLUMNS
from generate_assets import clean_text, validate_assets
from generate_asset_prices import (
    AS_OF_DATE, PRICE_COLUMNS, valid_price, validate_prices,
)
from generate_holdings import read_table


BASE_SEED = 42
VERSION = "asset_price_history_v1"
HORIZON_DAYS = 30
CENT = Decimal("0.01")
OPENING_DATE = date.fromisoformat(AS_OF_DATE)
DATES = [
    (OPENING_DATE + timedelta(days=day)).isoformat()
    for day in range(HORIZON_DAYS + 1)
]
END_DATE = DATES[-1]

# Arbitrary demonstration limits, not estimates of market volatility.
# One basis point equals 0.01 percent.
MAX_MOVE_BPS = {"EQUITY": 150, "FIXED_INCOME": 30, "CRYPTO": 400}


def records(rows):
    return Counter(
        tuple(row.get(column) for column in PRICE_COLUMNS)
        for row in rows
    )


def generate_history(assets_by_id, opening_by_id):
    history = []
    for asset_id in sorted(assets_by_id):
        asset = assets_by_id[asset_id]
        price = Decimal(opening_by_id[asset_id]["price"])
        limit = MAX_MOVE_BPS[asset["asset_class"]]

        for day_number, price_date in enumerate(DATES):
            # Keep the opening price. Simulate changes from the following day.
            if day_number > 0:
                rng = Random(
                    f"{VERSION}|{BASE_SEED}|{asset_id}|{price_date}"
                )
                move_bps = rng.randint(-limit, limit)
                multiplier = Decimal(10000 + move_bps) / Decimal(10000)
                price = max(
                    CENT,
                    (price * multiplier).quantize(
                        CENT, rounding=ROUND_HALF_UP
                    ),
                )

            history.append({
                "asset_id": asset_id,
                "price_date": price_date,
                "quote_currency": asset["quote_currency"],
                "price": f"{price:.2f}",
                "data_origin": "synthetic_extension",
            })

    return history


def validate_history(rows, assets_by_id, opening_by_id):
    keys = [
        (r.get("asset_id"), r.get("price_date"), r.get("quote_currency"))
        for r in rows
    ]
    expected_keys = [
        (aid, day, asset["quote_currency"])
        for aid, asset in assets_by_id.items()
        for day in DATES
    ]
    expected_opening = [
        {**row, "price": f"{Decimal(row['price']):.2f}"}
        for row in opening_by_id.values()
    ]
    actual_opening = [
        r for r in rows if r.get("price_date") == AS_OF_DATE
    ]

    return {
        "schema_and_required_fields_valid": bool(rows) and all(
            set(r) == set(PRICE_COLUMNS)
            and all(
                clean_text(r.get(column))
                for column in PRICE_COLUMNS
            )
            for r in rows
        ),
        "row_count_correct": len(rows) == len(expected_keys),
        "asset_date_currency_keys_unique": len(keys) == len(set(keys)),
        "complete_asset_date_currency_grid": (
            Counter(keys) == Counter(expected_keys)
        ),
        "opening_prices_match_snapshot": (
            records(actual_opening) == records(expected_opening)
        ),
        "prices_positive_with_cent_precision": all(
            valid_price(r.get("price")) for r in rows
        ),
        "prices_follow_generation_rules": (
            records(rows)
            == records(generate_history(assets_by_id, opening_by_id))
        ),
        "synthetic_origin_recorded": all(
            r.get("data_origin") == "synthetic_extension"
            for r in rows
        ),
    }


def main():
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data" / "processed"
    output_path = data_dir / "asset_price_history.csv"
    report_path = root / "docs" / "price_history_validation.json"

    assets = read_table(data_dir / "assets.csv", ASSET_COLUMNS)
    opening = read_table(data_dir / "asset_prices.csv", PRICE_COLUMNS)

    if not all(validate_assets(assets).values()):
        raise SystemExit(
            "Asset validation failed. No outputs were written."
        )

    assets_by_id = {r["asset_id"]: r for r in assets}

    if not all(validate_prices(opening, assets_by_id).values()):
        raise SystemExit(
            "Opening price validation failed. No outputs were written."
        )

    if any(r["asset_class"] not in MAX_MOVE_BPS for r in assets):
        raise SystemExit(
            "A simulation rule is missing for an asset class."
        )

    opening_by_id = {r["asset_id"]: r for r in opening}
    history = generate_history(assets_by_id, opening_by_id)

    if not all(
        validate_history(history, assets_by_id, opening_by_id).values()
    ):
        raise SystemExit(
            "Generated price history failed validation. "
            "No outputs were written."
        )

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=PRICE_COLUMNS)
        writer.writeheader()
        writer.writerows(history)

    saved = read_table(output_path, PRICE_COLUMNS)
    checks = validate_history(saved, assets_by_id, opening_by_id)
    checks["csv_matches_generated_records"] = saved == history

    report = {
        "scope": (
            "Daily simulated unit prices anchored to the "
            "existing opening snapshot"
        ),
        "generator_version": VERSION,
        "base_seed": BASE_SEED,
        "seed_rule": (
            "Version, base seed, asset_id, and price_date "
            "for each daily draw"
        ),
        "opening_date": AS_OF_DATE,
        "last_price_date": END_DATE,
        "simulation_days": HORIZON_DAYS,
        "dates_per_asset": len(DATES),
        "assets_checked": len(assets),
        "prices_checked": len(saved),
        "currency": "USD",
        "max_daily_draw_bps_by_asset_class": MAX_MOVE_BPS,
        "generation_rule": (
            "Previous price multiplied by (1 + draw_bps / 10000)"
        ),
        "draw_rule": (
            "Uniform integer draw between the negative "
            "and positive class limit"
        ),
        "rounding_rule": (
            "ROUND_HALF_UP to cents each day; minimum price USD 0.01"
        ),
        "limits_note": (
            "Draw limits apply before rounding; "
            "they are arbitrary demo assumptions"
        ),
        "calendar_rule": (
            "Every calendar day, including weekends and holidays"
        ),
        "limitations": (
            "Fictional prices, not market quotes or forecasts; "
            "excludes dividends and fees"
        ),
        "opening_prices_usd": {
            aid: f"{Decimal(opening_by_id[aid]['price']):.2f}"
            for aid in sorted(opening_by_id)
        },
        "ending_prices_usd": {
            r["asset_id"]: r["price"]
            for r in saved
            if r["price_date"] == END_DATE
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

    if not report["all_checks_passed"]:
        raise SystemExit(
            "Price-history validation failed. Review the report."
        )

    print(
        f"\nSaved {len(saved):,} daily prices "
        f"for {len(assets)} fictional assets."
    )
    print(
        f"Date range: {AS_OF_DATE} through {END_DATE} "
        f"({len(DATES)} dates)."
    )
    print(f"All {len(checks)} price-history checks passed.")
    print("CSV:", output_path)
    print("Report:", report_path)


if __name__ == "__main__":
    main()
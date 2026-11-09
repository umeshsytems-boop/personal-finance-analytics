"""Create simulated debt snapshots linked to the existing users."""

import csv
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from random import Random


AS_OF_DATE = "2024-12-28"
BASE_SEED = 42
VERSION = "liabilities_v1"

# Arbitrary demonstration ranges in cents, not observed debt balances.
RANGES = {
    "CREDIT_CARD": (20_000, 800_000),
    "PERSONAL_LOAN": (100_000, 3_000_000),
}

COLUMNS = [
    "liability_id", "user_id", "liability_type", "as_of_date",
    "currency", "outstanding_balance", "data_origin",
]


def valid_balance(row):
    try:
        amount = Decimal(row["outstanding_balance"])
        low, high = RANGES[row["liability_type"]]
        return (
            amount.is_finite()
            and amount == amount.quantize(Decimal("0.01"))
            and low <= amount * 100 <= high
        )
    except (InvalidOperation, ValueError, TypeError, KeyError):
        return False


def validate_liabilities(rows, user_ids):
    keys = [(r.get("liability_id"), r.get("as_of_date")) for r in rows]
    owner_types = [(r.get("user_id"), r.get("liability_type")) for r in rows]
    return {
        "schema_and_required_fields_valid": all(
            set(r) == set(COLUMNS) and all(
                isinstance(r[c], str) and bool(r[c].strip()) and r[c] == r[c].strip()
                for c in COLUMNS
            ) for r in rows
        ),
        "liability_date_keys_unique": len(keys) == len(set(keys)),
        "one_debt_per_user_type": len(owner_types) == len(set(owner_types)),
        "owners_exist": all(r.get("user_id") in user_ids for r in rows),
        "types_and_ids_follow_rules": all(
            r.get("liability_type") in RANGES
            and r.get("liability_id") == f"liab_{r.get('user_id')}_{r['liability_type'].lower()}"
            for r in rows
        ),
        "snapshot_dates_correct": all(r.get("as_of_date") == AS_OF_DATE for r in rows),
        "balances_follow_generation_rules": all(valid_balance(r) for r in rows),
        "usd_currency_applied": all(r.get("currency") == "USD" for r in rows),
        "synthetic_origin_recorded": all(
            r.get("data_origin") == "synthetic_extension" for r in rows
        ),
    }


def generate_liabilities(user_ids):
    rows = []
    for user_id in sorted(user_ids):
        rng = Random(f"{VERSION}|{BASE_SEED}|{user_id}|{AS_OF_DATE}")
        selected_types = rng.sample(sorted(RANGES), rng.randint(0, 2))
        for kind in sorted(selected_types):
            low, high = RANGES[kind]
            cents = rng.randint(low, high)
            rows.append({
                "liability_id": f"liab_{user_id}_{kind.lower()}",
                "user_id": user_id,
                "liability_type": kind,
                "as_of_date": AS_OF_DATE,
                "currency": "USD",
                "outstanding_balance": f"{Decimal(cents) / 100:.2f}",
                "data_origin": "synthetic_extension",
            })
    return rows


def main():
    root = Path(__file__).resolve().parents[1]
    users_path = root / "data" / "interim" / "users.csv"
    output_path = root / "data" / "processed" / "liability_snapshots.csv"
    report_path = root / "docs" / "liability_validation.json"

    if not users_path.is_file():
        raise SystemExit("Missing users.csv. Run src/extract_users.py first.")
    with users_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        users = list(reader)
        if reader.fieldnames != ["user_id", "user_name", "archetype"]:
            raise SystemExit("Unexpected users.csv columns.")
    if not users or any(None in r or None in r.values() for r in users):
        raise SystemExit("Empty users table or missing/extra fields.")

    user_ids = [r["user_id"] for r in users]
    if len(user_ids) != len(set(user_ids)) or any(
        not uid.strip() or uid != uid.strip() for uid in user_ids
    ):
        raise SystemExit("User IDs must be unique, nonblank, and have no surrounding spaces.")
    user_ids = set(user_ids)

    liabilities = generate_liabilities(user_ids)
    if not all(validate_liabilities(liabilities, user_ids).values()):
        raise SystemExit("Generated liabilities failed validation. No outputs were written.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(liabilities)

    # An empty debt table is valid if every user was assigned zero debts.
    with output_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        saved_columns = reader.fieldnames
        saved = list(reader)

    checks = validate_liabilities(saved, user_ids)
    checks["csv_matches_generated_records"] = saved_columns == COLUMNS and saved == liabilities
    borrowers = {r.get("user_id") for r in saved}
    total = (
        sum((Decimal(r["outstanding_balance"]) for r in saved), Decimal("0"))
        if checks["balances_follow_generation_rules"] else None
    )

    report = {
        "scope": "Simulated end-of-day debt balances linked to existing users",
        "generator_version": VERSION,
        "as_of_date": AS_OF_DATE,
        "base_seed": BASE_SEED,
        "seed_rule": "Version, base seed, user_id, and snapshot date per user",
        "selection_rule": "Zero, one, or two distinct debt types per user",
        "ranges_in_cents": RANGES,
        "currency_note": "USD is a demonstration assumption",
        "coverage_note": "All input users processed; no rows means zero modeled debt",
        "limitations": "Balances are simulated, not inferred from or reconciled to transactions",
        "users_processed": len(user_ids),
        "users_with_liabilities": len(borrowers),
        "users_with_no_modeled_debt": len(user_ids - borrowers),
        "liabilities_checked": len(saved),
        "total_outstanding_balance": f"{total:.2f}" if total is not None else None,
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
        raise SystemExit("Liability validation failed. Review the report.")

    print(f"\nProcessed {len(user_ids):,} users.")
    print(f"Saved {len(saved):,} liabilities for {len(borrowers):,} users.")
    print(f"Users with zero modeled debt: {len(user_ids - borrowers):,}")
    print(f"All {len(checks)} liability checks passed.")
    print("CSV:", output_path)
    print("Report:", report_path)


if __name__ == "__main__":
    main()
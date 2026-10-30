import csv
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from random import Random


AS_OF_DATE = "2024-12-28"
SEED = 42
# Arbitrary demonstration ranges in cents, including both endpoints.
RANGES = {"CASH": (50_000, 2_500_000), "INVESTMENT": (0, 300_000)}


def read_table(path, columns):
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        if reader.fieldnames != columns:
            raise SystemExit(f"Unexpected columns in {path.name}.")
    if any(None in row or None in row.values() for row in rows):
        raise SystemExit(f"Missing or extra fields in {path.name}.")
    return rows


def valid_balance(row, account_lookup):
    try:
        amount = Decimal(row["cash_balance"])
        kind = account_lookup[row["account_id"]]["account_type"]
        low, high = RANGES[kind]
        return (
            amount.is_finite()
            and amount == amount.quantize(Decimal("0.01"))
            and low <= amount * 100 <= high
        )
    except (InvalidOperation, ValueError, TypeError, KeyError):
        return False


def validate_snapshots(rows, account_lookup):
    keys = [(row["account_id"], row["as_of_date"]) for row in rows]
    return {
        "snapshot_count_correct": len(rows) == len(account_lookup),
        "account_date_keys_unique": len(keys) == len(set(keys)),
        "all_accounts_covered": {r["account_id"] for r in rows} == set(account_lookup),
        "snapshot_dates_correct": all(r["as_of_date"] == AS_OF_DATE for r in rows),
        "currencies_match_accounts": all(
            r["currency"] == account_lookup.get(r["account_id"], {}).get("currency")
            for r in rows
        ),
        "balances_follow_generation_rules": all(valid_balance(r, account_lookup) for r in rows),
        "synthetic_origin_recorded": all(r["data_origin"] == "synthetic_extension" for r in rows),
    }


project_root = Path(__file__).resolve().parents[1]
accounts_path = project_root / "data" / "processed" / "accounts.csv"
output_path = project_root / "data" / "processed" / "cash_balance_snapshots.csv"
report_path = project_root / "docs" / "cash_balance_validation.json"
account_columns = [
    "account_id", "user_id", "account_name",
    "account_type", "currency", "data_origin",
]
accounts = read_table(accounts_path, account_columns)
account_ids = [r["account_id"] for r in accounts]
if not accounts or any(not aid.strip() or aid != aid.strip() for aid in account_ids):
    raise SystemExit("Account IDs must be present and have no surrounding spaces.")
if len(account_ids) != len(set(account_ids)):
    raise SystemExit("Duplicate account IDs found. Fix the account registry first.")
if any(
    r["account_type"] not in RANGES
    or r["currency"] != "USD"
    or r["data_origin"] != "synthetic_extension"
    for r in accounts
):
    raise SystemExit("Expected synthetic CASH/INVESTMENT accounts in assumed USD.")
account_lookup = {row["account_id"]: row for row in accounts}

columns = ["account_id", "as_of_date", "currency", "cash_balance", "data_origin"]
snapshots = []
for account in sorted(accounts, key=lambda row: row["account_id"]):
    account_id = account["account_id"]
    rng = Random(f"cash_balances_v1|{SEED}|{account_id}|{AS_OF_DATE}")
    low, high = RANGES[account["account_type"]]
    cents = rng.randint(low, high)
    snapshots.append({
        "account_id": account_id,
        "as_of_date": AS_OF_DATE,
        "currency": account["currency"],
        "cash_balance": f"{Decimal(cents) / 100:.2f}",
        "data_origin": "synthetic_extension",
    })

output_path.parent.mkdir(parents=True, exist_ok=True)
with output_path.open("w", encoding="utf-8", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=columns)
    writer.writeheader()
    writer.writerows(snapshots)

saved = read_table(output_path, columns)
checks = validate_snapshots(saved, account_lookup)
checks["csv_matches_generated_records"] = saved == snapshots
report = {
    "scope": "Synthetic end-of-day cash snapshots; not reconciled to source transactions",
    "generator_version": "cash_balances_v1",
    "as_of_date": AS_OF_DATE,
    "base_seed": SEED,
    "seed_rule": "Version, base seed, account_id, and as_of_date combined per account",
    "ranges_in_cents": RANGES,
    "currency_note": "USD is a demonstration assumption",
    "investment_cash_note": "Uninvested cash only; excludes holding values",
    "accounts_checked": len(accounts),
    "snapshots_checked": len(saved),
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
    raise SystemExit("Cash-balance validation failed. Review the report.")
print(f"\nSaved {len(saved):,} cash-balance snapshots for {AS_OF_DATE}.")
print(f"All {len(checks)} cash-balance checks passed.")
print("CSV:", output_path)
print("Report:", report_path)

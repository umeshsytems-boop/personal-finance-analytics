import csv
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]


def read_csv(path):
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


# Use the counts recorded when we profiled the original JSON.
def valid_date(value, earliest, latest):
    try:
        parsed = date.fromisoformat(value)
        return parsed.isoformat() == value and earliest <= parsed <= latest
    except (TypeError, ValueError):
        return False


def valid_amount(value):
    try:
        amount = Decimal(value)
        return amount.is_finite() and amount >= 0
    except (InvalidOperation, TypeError, ValueError):
        return False

profile_path = project_root / "docs" / "source_profile.json"
with profile_path.open("r", encoding="utf-8") as profile_file:
    source_profile = json.load(profile_file)

users = read_csv(project_root / "data" / "interim" / "users.csv")
transactions = read_csv(project_root / "data" / "interim" / "transactions.csv")

user_ids = [row["user_id"] for row in users]
transaction_ids = [row["transaction_id"] for row in transactions]
transaction_user_ids = [row["user_id"] for row in transactions]

checks = {
    "user_count_matches_profile": len(users) == source_profile["users_counted"],
    "transaction_count_matches_profile": (
        len(transactions) == source_profile["transactions_counted"]
    ),
    "user_ids_present": all(value and value.strip() for value in user_ids),
    "user_ids_unique": len(user_ids) == len(set(user_ids)),
    "transaction_ids_present": all(
        value and value.strip() for value in transaction_ids
    ),
    "transaction_ids_unique": len(transaction_ids) == len(set(transaction_ids)),
    "transaction_user_ids_present": all(
        value and value.strip() for value in transaction_user_ids
    ),
    "transaction_users_exist": set(transaction_user_ids).issubset(set(user_ids)),
}

earliest = date.fromisoformat(source_profile["earliest_date"])
latest = date.fromisoformat(source_profile["latest_date"])

checks.update({
    "transaction_dates_valid": all(
        valid_date(row["transaction_date"], earliest, latest)
        for row in transactions
    ),
    "transaction_amounts_valid": all(
        valid_amount(row["amount"]) for row in transactions
    ),
    "transaction_types_valid": all(
        row["transaction_type"] in {"CREDIT", "DEBIT"}
        for row in transactions
    ),
})

report = {
    "scope": "CSV counts, IDs, transaction dates, amounts, and types",
    "users_checked": len(users),
    "transactions_checked": len(transactions),
    "checks": checks,
    "all_checks_passed": all(checks.values()),
}

report_path = project_root / "docs" / "table_validation.json"
report_path.parent.mkdir(parents=True, exist_ok=True)

with report_path.open("w", encoding="utf-8") as report_file:
    json.dump(report, report_file, indent=2)
    report_file.write("\n")

print("Users checked:", len(users))
print("Transactions checked:", len(transactions))

for name, passed in checks.items():
    status = "PASS" if passed else "FAIL"
    print(f"{status} | {name}")

print("Report saved to:", report_path)

if not report["all_checks_passed"]:
    raise SystemExit("Validation failed. Review the FAIL lines above.")

print(f"All {len(checks)} configured checks passed.")
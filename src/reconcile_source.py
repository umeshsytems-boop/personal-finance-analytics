import csv
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]


def csv_record(values):
    return tuple("" if value is None else str(value) for value in values)


def read_csv_records(path, columns):
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.reader(csv_file, strict=True)
        header = next(reader, None)
        records = Counter(tuple(row) for row in reader)
    structure_ok = header == columns and all(
        len(row) == len(columns) for row in records
    )
    return records, structure_ok


user_columns = ["user_id", "user_name", "archetype"]
transaction_columns = [
    "transaction_id", "user_id", "transaction_date",
    "description", "merchant_name", "amount",
    "source_balance", "transaction_type", "category", "subcategory",
]

source_path = project_root / "data" / "raw" / "artha" / "artha_users_v2.json"
with source_path.open("r", encoding="utf-8") as source_file:
    source = json.load(source_file, parse_float=Decimal)

# Build expected records directly from the original JSON.
expected_users = Counter()
expected_transactions = Counter()

for archetype, users in source["archetypes"].items():
    for user in users:
        expected_users[csv_record([
            user["user_id"], user["name"], archetype,
        ])] += 1

        for transaction in user["transactions"]:
            expected_transactions[csv_record([
                transaction["transaction_id"],
                user["user_id"],
                transaction["date"],
                transaction["description"],
                transaction["merchant_name"],
                transaction["amount"],
                transaction["balance"],
                transaction["transaction_type"],
                transaction["category"],
                transaction["subcategory"],
            ])] += 1

actual_users, users_structure_ok = read_csv_records(
    project_root / "data" / "interim" / "users.csv", user_columns
)
actual_transactions, transactions_structure_ok = read_csv_records(
    project_root / "data" / "interim" / "transactions.csv", transaction_columns
)

checks = {
    "users_csv_structure": users_structure_ok,
    "transactions_csv_structure": transactions_structure_ok,
    "users_match_source": expected_users == actual_users,
    "transactions_match_source": expected_transactions == actual_transactions,
}

report = {
    "scope": "Exported fields compared with the original JSON",
    "source_users": expected_users.total(),
    "csv_users": actual_users.total(),
    "source_transactions": expected_transactions.total(),
    "csv_transactions": actual_transactions.total(),
    "unmatched_source_users": (expected_users - actual_users).total(),
    "unmatched_csv_users": (actual_users - expected_users).total(),
    "unmatched_source_transactions": (
        expected_transactions - actual_transactions
    ).total(),
    "unmatched_csv_transactions": (
        actual_transactions - expected_transactions
    ).total(),
    "checks": checks,
    "all_checks_passed": all(checks.values()),
}

report_path = project_root / "docs" / "source_reconciliation.json"
report_path.parent.mkdir(parents=True, exist_ok=True)
with report_path.open("w", encoding="utf-8") as report_file:
    json.dump(report, report_file, indent=2)
    report_file.write("\n")

for name, passed in checks.items():
    status = "PASS" if passed else "FAIL"
    print(f"{status} | {name}")

print("Report saved to:", report_path)
if not report["all_checks_passed"]:
    raise SystemExit("Reconciliation failed. Review the saved report.")

print("All 4 reconciliation checks passed.")
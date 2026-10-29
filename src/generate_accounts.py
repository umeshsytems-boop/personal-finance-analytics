import csv
import json
from collections import Counter
from pathlib import Path


project_root = Path(__file__).resolve().parents[1]
users_path = project_root / "data" / "interim" / "users.csv"
output_path = project_root / "data" / "processed" / "accounts.csv"
report_path = project_root / "docs" / "account_validation.json"

# Read the existing user table without changing it.
with users_path.open("r", encoding="utf-8", newline="") as file:
    reader = csv.DictReader(file)
    user_columns = reader.fieldnames
    users = list(reader)

if user_columns != ["user_id", "user_name", "archetype"]:
    raise SystemExit("Unexpected users.csv columns. Check the user export.")
if any(None in row or None in row.values() for row in users):
    raise SystemExit("A user row has missing or extra fields.")

user_ids = [row["user_id"] for row in users]
if not user_ids or any(not uid.strip() or uid != uid.strip() for uid in user_ids):
    raise SystemExit("User IDs must be present and have no surrounding spaces.")
if len(user_ids) != len(set(user_ids)):
    raise SystemExit("Duplicate user IDs found. No accounts were generated.")

# Demonstration rule: one CASH and one INVESTMENT account per user.
# This is deterministic; no random seed is needed for this table.
account_types = ("CASH", "INVESTMENT")
columns = [
    "account_id", "user_id", "account_name",
    "account_type", "currency", "data_origin",
]
accounts = []
for user_id in sorted(user_ids):
    for account_type in account_types:
        accounts.append({
            "account_id": f"acct_{user_id}_{account_type.lower()}",
            "user_id": user_id,
            "account_name": f"Demo {account_type.lower()} account",
            "account_type": account_type,
            "currency": "USD",  # Explicit demonstration assumption.
            "data_origin": "synthetic_extension",
        })

output_path.parent.mkdir(parents=True, exist_ok=True)
with output_path.open("w", encoding="utf-8", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=columns)
    writer.writeheader()
    writer.writerows(accounts)

# Validate the saved CSV, including its ownership relationships.
with output_path.open("r", encoding="utf-8", newline="") as file:
    reader = csv.DictReader(file)
    saved_columns = reader.fieldnames
    saved_accounts = list(reader)

account_ids = [row["account_id"] for row in saved_accounts]
owner_types = Counter(
    (row["user_id"], row["account_type"]) for row in saved_accounts
)
expected_pairs = {(uid, kind) for uid in user_ids for kind in account_types}
checks = {
    "csv_matches_generated_records": saved_columns == columns and saved_accounts == accounts,
    "account_count_correct": len(saved_accounts) == len(user_ids) * len(account_types),
    "account_ids_present_and_unique": all(account_ids) and len(account_ids) == len(set(account_ids)),
    "account_owners_exist": {row["user_id"] for row in saved_accounts}.issubset(set(user_ids)),
    "one_account_of_each_type_per_user": set(owner_types) == expected_pairs and all(n == 1 for n in owner_types.values()),
    "currency_assumption_applied": all(row["currency"] == "USD" for row in saved_accounts),
    "synthetic_origin_recorded": all(row["data_origin"] == "synthetic_extension" for row in saved_accounts),
}
report = {
    "scope": "Synthetic account registry and links to exported users",
    "generator_version": "accounts_v1",
    "generation_rule": "One CASH and one INVESTMENT account per user; IDs derived from user_id and type",
    "currency_note": "USD is a demonstration assumption, not a source-provided currency",
    "users_checked": len(user_ids),
    "accounts_checked": len(saved_accounts),
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
    raise SystemExit("Account validation failed. Review the report before continuing.")

print(f"\nSaved {len(saved_accounts):,} accounts for {len(user_ids):,} users.")
print(f"All {len(checks)} account checks passed.")
print("CSV:", output_path)
print("Report:", report_path)
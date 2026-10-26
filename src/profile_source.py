import json
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
data_path = project_root / "data" / "raw" / "artha" / "artha_users_v2.json"

with data_path.open("r", encoding="utf-8") as source_file:
    data = json.load(source_file)

# Collect identifiers and dates from every group and every user.
user_ids = []
transaction_ids = []
transaction_dates = []

for users in data["archetypes"].values():
    for user in users:
        user_ids.append(user["user_id"])

        for transaction in user["transactions"]:
            transaction_ids.append(transaction["transaction_id"])
            transaction_dates.append(transaction["date"])

# A set keeps only unique values, so the difference counts extra copies.
report = {
    "users_counted": len(user_ids),
    "users_reported_by_source": data["total_users"],
    "transactions_counted": len(transaction_ids),
    "duplicate_user_ids": len(user_ids) - len(set(user_ids)),
    "duplicate_transaction_ids": len(transaction_ids) - len(set(transaction_ids)),
    "earliest_date": min(transaction_dates, default=None),
    "latest_date": max(transaction_dates, default=None),
}

# Save a small report separately from the unchanged raw data.
report_path = project_root / "docs" / "source_profile.json"
report_path.parent.mkdir(parents=True, exist_ok=True)

with report_path.open("w", encoding="utf-8") as report_file:
    json.dump(report, report_file, indent=2)
    report_file.write("\n")

print(json.dumps(report, indent=2))
print("\nSaved report to:", report_path)
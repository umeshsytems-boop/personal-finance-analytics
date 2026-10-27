import csv
import json
from decimal import Decimal
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
source_path = project_root / "data" / "raw" / "artha" / "artha_users_v2.json"
output_path = project_root / "data" / "interim" / "transactions.csv"

# Read decimal numbers without converting them to binary floats.
with source_path.open("r", encoding="utf-8") as source_file:
    data = json.load(source_file, parse_float=Decimal)

# Carry the parent user's ID into every transaction row.
rows = []

for users in data["archetypes"].values():
    for user in users:
        for transaction in user["transactions"]:
            rows.append({
                "transaction_id": transaction["transaction_id"],
                "user_id": user["user_id"],
                "transaction_date": transaction["date"],
                "description": transaction["description"],
                "merchant_name": transaction["merchant_name"],
                "amount": transaction["amount"],
                "source_balance": transaction["balance"],
                "transaction_type": transaction["transaction_type"],
                "category": transaction["category"],
                "subcategory": transaction["subcategory"],
            })

fieldnames = [
    "transaction_id", "user_id", "transaction_date",
    "description", "merchant_name", "amount",
    "source_balance", "transaction_type", "category", "subcategory",
]

output_path.parent.mkdir(parents=True, exist_ok=True)

with output_path.open("w", encoding="utf-8", newline="") as output_file:
    writer = csv.DictWriter(output_file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print("Transactions exported:", len(rows))
print("Users represented:", len({row["user_id"] for row in rows}))
print("Saved to:", output_path)
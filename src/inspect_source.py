import json
from pathlib import Path

# Find the project folder from this script's location.
project_root = Path(__file__).resolve().parents[1]
data_path = project_root / "data" / "raw" / "artha" / "artha_users_v2.json"

# Read the original JSON file without changing it.
with data_path.open("r", encoding="utf-8") as source_file:
    data = json.load(source_file)

# Select one group and its first fictional user.
group_name = "overspender"
users = data["archetypes"][group_name]
first_user = users[0]
transactions = first_user["transactions"]

print("Users listed in file:", data["total_users"])
print("Selected group:", group_name)
print("User:", first_user["name"])
print("User ID:", first_user["user_id"])
print("Transactions for this user:", len(transactions))

print("\nFirst 3 transactions:")
for transaction in transactions[:3]:
    print(
        transaction["date"],
        transaction["transaction_type"],
        f'{transaction["amount"]:,.2f}',
        transaction["category"],
        sep=" | ",
    )
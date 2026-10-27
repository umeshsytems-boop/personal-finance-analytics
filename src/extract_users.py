import csv
import json
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
source_path = project_root / "data" / "raw" / "artha" / "artha_users_v2.json"
output_path = project_root / "data" / "interim" / "users.csv"

# Read the original JSON.
with source_path.open("r", encoding="utf-8") as source_file:
    data = json.load(source_file)

# Create one row for each fictional user.
rows = []

for archetype, users in data["archetypes"].items():
    for user in users:
        rows.append({
            "user_id": user["user_id"],
            "user_name": user["name"],
            "archetype": archetype,
        })

# Save the extracted table separately from the original data.
output_path.parent.mkdir(parents=True, exist_ok=True)

with output_path.open("w", encoding="utf-8", newline="") as output_file:
    writer = csv.DictWriter(
        output_file,
        fieldnames=["user_id", "user_name", "archetype"],
    )
    writer.writeheader()
    writer.writerows(rows)

print("Users exported:", len(rows))
print("Saved to:", output_path)
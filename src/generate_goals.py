"""Earmark existing simulated cash for two savings goals per user."""

import csv
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from random import Random

from calculate_net_worth import CASH_COLUMNS, cents, money, require
from generate_asset_prices import AS_OF_DATE
from generate_holdings import ACCOUNT_COLUMNS, read_table


BASE_SEED = 42
VERSION = "goals_v1"

RULES = {
    "EMERGENCY_FUND": {
        "name": "Emergency fund",
        "target_min_usd": 3000,
        "target_max_usd": 15000,
        "cash_percent": 30,
        "days_until_target": 365,
    },
    "TRAVEL": {
        "name": "Travel",
        "target_min_usd": 1000,
        "target_max_usd": 6000,
        "cash_percent": 20,
        "days_until_target": 180,
    },
}

COLUMNS = [
    "goal_id",
    "user_id",
    "funding_account_id",
    "goal_type",
    "goal_name",
    "as_of_date",
    "target_date",
    "currency",
    "target_amount",
    "allocated_amount",
    "data_origin",
]


def target_date(kind):
    return (
        date.fromisoformat(AS_OF_DATE)
        + timedelta(days=RULES[kind]["days_until_target"])
    ).isoformat()


def generate_goals(cash_accounts, balances):
    goals = []

    for aid, account in sorted(cash_accounts.items()):
        uid = account["user_id"]

        for kind, rule in sorted(RULES.items()):
            rng = Random(
                f"{VERSION}|{BASE_SEED}|{uid}|{AS_OF_DATE}|{kind}"
            )

            target = rng.randint(
                rule["target_min_usd"],
                rule["target_max_usd"],
            ) * 100

            # Round the allocation down to whole cents.
            allocation = min(
                target,
                balances[aid] * rule["cash_percent"] // 100,
            )

            goals.append({
                "goal_id": f"goal_{uid}_{kind.lower()}",
                "user_id": uid,
                "funding_account_id": aid,
                "goal_type": kind,
                "goal_name": rule["name"],
                "as_of_date": AS_OF_DATE,
                "target_date": target_date(kind),
                "currency": account["currency"],
                "target_amount": money(target),
                "allocated_amount": money(allocation),
                "data_origin": "synthetic_extension",
            })

    return goals


def validate_goals(rows, cash_accounts, balances):
    require(
        all(
            set(r) == set(COLUMNS)
            and all(
                isinstance(r[c], str)
                and r[c]
                and r[c] == r[c].strip()
                for c in COLUMNS
            )
            for r in rows
        ),
        "Invalid goal columns or blank fields.",
    )

    targets = [cents(r["target_amount"]) for r in rows]
    allocations = [cents(r["allocated_amount"]) for r in rows]
    keys = [(r["goal_id"], r["as_of_date"]) for r in rows]

    allocated_by_account = Counter()
    for row, amount in zip(rows, allocations):
        allocated_by_account[row["funding_account_id"]] += amount

    checks = {
        "goal_count_correct":
            len(rows) == len(cash_accounts) * len(RULES),

        "goal_date_keys_unique":
            len(keys) == len(set(keys)),

        "each_cash_account_has_both_goals":
            Counter(
                (r["funding_account_id"], r["goal_type"])
                for r in rows
            )
            == Counter(
                (aid, kind)
                for aid in cash_accounts
                for kind in RULES
            ),

        "ownership_matches_users": all(
            r["funding_account_id"] in cash_accounts
            and r["user_id"]
            == cash_accounts[r["funding_account_id"]]["user_id"]
            for r in rows
        ),

        "goal_labels_and_ids_valid": all(
            r["goal_type"] in RULES
            and r["goal_id"]
            == f"goal_{r['user_id']}_{r['goal_type'].lower()}"
            and r["goal_name"] == RULES[r["goal_type"]]["name"]
            for r in rows
        ),

        "snapshot_dates_correct": all(
            r["as_of_date"] == AS_OF_DATE for r in rows
        ),

        "target_dates_follow_rules": all(
            r["goal_type"] in RULES
            and r["target_date"] == target_date(r["goal_type"])
            for r in rows
        ),

        "currencies_match_accounts": all(
            r["funding_account_id"] in cash_accounts
            and r["currency"]
            == cash_accounts[r["funding_account_id"]]["currency"]
            for r in rows
        ),

        "targets_follow_demo_ranges": all(
            r["goal_type"] in RULES
            and amount % 100 == 0
            and RULES[r["goal_type"]]["target_min_usd"] * 100
            <= amount
            <= RULES[r["goal_type"]]["target_max_usd"] * 100
            for r, amount in zip(rows, targets)
        ),

        "allocations_within_targets": all(
            allocated <= target
            for allocated, target in zip(allocations, targets)
        ),

        "individual_allocation_caps_respected": all(
            r["funding_account_id"] in cash_accounts
            and r["goal_type"] in RULES
            and amount
            <= balances[r["funding_account_id"]]
            * RULES[r["goal_type"]]["cash_percent"] // 100
            for r, amount in zip(rows, allocations)
        ),

        "combined_allocation_caps_respected": all(
            aid in cash_accounts
            and amount <= balances[aid] // 2
            for aid, amount in allocated_by_account.items()
        ),

        "synthetic_origin_recorded": all(
            r["data_origin"] == "synthetic_extension"
            for r in rows
        ),
    }

    return checks


def main():
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data" / "processed"
    output_path = data_dir / "goal_snapshots.csv"
    report_path = root / "docs" / "goal_validation.json"

    users = read_table(
        root / "data" / "interim" / "users.csv",
        ["user_id", "user_name", "archetype"],
    )
    accounts = read_table(
        data_dir / "accounts.csv",
        ACCOUNT_COLUMNS,
    )
    cash = read_table(
        data_dir / "cash_balance_snapshots.csv",
        CASH_COLUMNS,
    )

    user_ids = {r["user_id"] for r in users}
    account_ids = {r["account_id"] for r in accounts}

    require(len(user_ids) == len(users), "Duplicate user IDs.")

    require(
        len(account_ids) == len(accounts)
        and Counter(
            (r["user_id"], r["account_type"])
            for r in accounts
        )
        == Counter(
            (uid, kind)
            for uid in user_ids
            for kind in ("CASH", "INVESTMENT")
        )
        and all(
            r["account_id"]
            == f"acct_{r['user_id']}_{r['account_type'].lower()}"
            and r["currency"] == "USD"
            and r["data_origin"] == "synthetic_extension"
            for r in accounts
        ),
        "Account identities or ownership do not match the current users.",
    )

    require(
        Counter(
            (r["account_id"], r["as_of_date"])
            for r in cash
        )
        == Counter(
            (aid, AS_OF_DATE) for aid in account_ids
        )
        and all(
            r["currency"] == "USD"
            and r["data_origin"] == "synthetic_extension"
            for r in cash
        ),
        "Missing, duplicate, or invalid cash snapshots.",
    )

    balances = {
        r["account_id"]: cents(r["cash_balance"])
        for r in cash
    }
    cash_accounts = {
        r["account_id"]: r
        for r in accounts
        if r["account_type"] == "CASH"
    }

    goals = generate_goals(cash_accounts, balances)

    require(
        all(validate_goals(goals, cash_accounts, balances).values()),
        "Generated goals failed validation. No outputs were written.",
    )

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(goals)

    saved = read_table(output_path, COLUMNS)
    checks = validate_goals(saved, cash_accounts, balances)
    checks["csv_matches_generated_records"] = saved == goals

    eligible_cash = sum(
        balances[aid] for aid in cash_accounts
    )
    allocated = sum(
        cents(r["allocated_amount"]) for r in saved
    )

    report = {
        "scope": "Synthetic savings goals earmarked from existing CASH-account balances",
        "generator_version": VERSION,
        "as_of_date": AS_OF_DATE,
        "currency_note": "USD is a demonstration assumption",
        "base_seed": BASE_SEED,
        "seed_rule": "Version, seed, user ID, snapshot date, and goal type",
        "goal_rules": RULES,
        "allocation_rule": "Up to 30% for emergency fund and 20% for travel, each capped at its target",
        "accounting_note": "Allocations remain part of existing cash; no new assets or cash movements",
        "limitations": "Arbitrary demo rules; remaining cash may still be needed for other obligations",
        "users_checked": len(users),
        "funding_accounts_checked": len(cash_accounts),
        "goals_checked": len(saved),
        "eligible_cash_usd": money(eligible_cash),
        "allocated_to_goals_usd": money(allocated),
        "cash_not_allocated_to_goals_usd": money(
            eligible_cash - allocated
        ),
        "checks": checks,
        "all_checks_passed": all(checks.values()),
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
        file.write("\n")

    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'}: {name}")

    require(
        report["all_checks_passed"],
        "Goal validation failed. Review the report.",
    )

    print(f"\nSaved {len(saved):,} goals for {len(users):,} users.")
    print(f"All {len(checks)} goal checks passed.")
    print("Allocated to goals (USD):", report["allocated_to_goals_usd"])
    print("CSV:", output_path)
    print("Report:", report_path)


if __name__ == "__main__":
    main()
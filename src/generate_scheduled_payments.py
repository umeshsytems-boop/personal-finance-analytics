"""Create simulated future bill occurrences without moving any cash."""

import csv
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from random import Random

from calculate_net_worth import cents, money, require
from generate_asset_prices import AS_OF_DATE
from generate_holdings import ACCOUNT_COLUMNS, read_table


BASE_SEED = 42
VERSION = "scheduled_payments_v1"
HORIZON_DAYS = 30

SNAPSHOT_DATE = date.fromisoformat(AS_OF_DATE)
WINDOW_END = SNAPSHOT_DATE + timedelta(days=HORIZON_DAYS)

RULES = {
    "RENT": {
        "payee": "Demo landlord",
        "amount_min_usd": 800,
        "amount_max_usd": 2500,
        "due_in_days": 4,
    },
    "UTILITIES": {
        "payee": "Demo utilities",
        "amount_min_usd": 80,
        "amount_max_usd": 250,
        "due_in_days": 12,
    },
    "INSURANCE": {
        "payee": "Demo insurer",
        "amount_min_usd": 50,
        "amount_max_usd": 200,
        "due_in_days": 20,
    },
}

COLUMNS = [
    "payment_id",
    "user_id",
    "funding_account_id",
    "payment_type",
    "payee_name",
    "as_of_date",
    "due_date",
    "currency",
    "amount",
    "status",
    "data_origin",
]


def due_date(kind):
    return (
        SNAPSHOT_DATE
        + timedelta(days=RULES[kind]["due_in_days"])
    ).isoformat()


def valid_due_date(value):
    try:
        parsed = date.fromisoformat(value)
        return (
            parsed.isoformat() == value
            and SNAPSHOT_DATE < parsed <= WINDOW_END
        )
    except (ValueError, TypeError):
        return False


def generate_payments(cash_accounts):
    payments = []

    for aid, account in sorted(cash_accounts.items()):
        uid = account["user_id"]

        for kind, rule in sorted(RULES.items()):
            rng = Random(
                f"{VERSION}|{BASE_SEED}|{uid}|{AS_OF_DATE}|{kind}"
            )

            amount = rng.randint(
                rule["amount_min_usd"],
                rule["amount_max_usd"],
            ) * 100

            due = due_date(kind)

            payments.append({
                "payment_id": f"pay_{uid}_{kind.lower()}_{due}",
                "user_id": uid,
                "funding_account_id": aid,
                "payment_type": kind,
                "payee_name": rule["payee"],
                "as_of_date": AS_OF_DATE,
                "due_date": due,
                "currency": account["currency"],
                "amount": money(amount),
                "status": "SCHEDULED",
                "data_origin": "synthetic_extension",
            })

    return sorted(
        payments,
        key=lambda r: (
            r["user_id"],
            r["due_date"],
            r["payment_id"],
        ),
    )


def validate_payments(rows, cash_accounts):
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
        "Invalid payment columns or blank fields.",
    )

    amounts = [cents(r["amount"]) for r in rows]
    ids = [r["payment_id"] for r in rows]

    return {
        "payment_count_correct":
            len(rows) == len(cash_accounts) * len(RULES),

        "payment_ids_unique":
            len(ids) == len(set(ids)),

        "each_cash_account_has_three_payment_types":
            Counter(
                (r["funding_account_id"], r["payment_type"])
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

        "payment_labels_and_ids_valid": all(
            r["payment_type"] in RULES
            and r["payment_id"]
            == f"pay_{r['user_id']}_{r['payment_type'].lower()}_{r['due_date']}"
            and r["payee_name"]
            == RULES[r["payment_type"]]["payee"]
            for r in rows
        ),

        "snapshot_dates_correct": all(
            r["as_of_date"] == AS_OF_DATE for r in rows
        ),

        "due_dates_follow_rules": all(
            r["payment_type"] in RULES
            and r["due_date"] == due_date(r["payment_type"])
            for r in rows
        ),

        "payments_within_30_day_window": all(
            valid_due_date(r["due_date"]) for r in rows
        ),

        "currencies_match_accounts": all(
            r["funding_account_id"] in cash_accounts
            and r["currency"]
            == cash_accounts[r["funding_account_id"]]["currency"]
            for r in rows
        ),

        "amounts_follow_demo_ranges": all(
            r["payment_type"] in RULES
            and amount % 100 == 0
            and RULES[r["payment_type"]]["amount_min_usd"] * 100
            <= amount
            <= RULES[r["payment_type"]]["amount_max_usd"] * 100
            for r, amount in zip(rows, amounts)
        ),

        "all_payments_scheduled": all(
            r["status"] == "SCHEDULED" for r in rows
        ),

        "synthetic_origin_recorded": all(
            r["data_origin"] == "synthetic_extension"
            for r in rows
        ),
    }


def main():
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data" / "processed"

    output_path = data_dir / "scheduled_payments.csv"
    report_path = root / "docs" / "scheduled_payment_validation.json"

    users = read_table(
        root / "data" / "interim" / "users.csv",
        ["user_id", "user_name", "archetype"],
    )
    accounts = read_table(
        data_dir / "accounts.csv",
        ACCOUNT_COLUMNS,
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

    cash_accounts = {
        r["account_id"]: r
        for r in accounts
        if r["account_type"] == "CASH"
    }

    payments = generate_payments(cash_accounts)

    require(
        all(validate_payments(payments, cash_accounts).values()),
        "Generated payments failed validation. No outputs were written.",
    )

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(payments)

    saved = read_table(output_path, COLUMNS)

    checks = validate_payments(saved, cash_accounts)
    checks["csv_matches_generated_records"] = saved == payments

    report = {
        "scope": "One simulated upcoming bill occurrence per user and payment type",
        "generator_version": VERSION,
        "as_of_date": AS_OF_DATE,
        "window_start": (
            SNAPSHOT_DATE + timedelta(days=1)
        ).isoformat(),
        "window_end": WINDOW_END.isoformat(),
        "horizon_days": HORIZON_DAYS,
        "currency_note": "USD is a demonstration assumption",
        "base_seed": BASE_SEED,
        "seed_rule": "Version, seed, user ID, snapshot date, and payment type",
        "payment_rules": RULES,
        "accounting_note": "Future plans; no cash movement or additional liability recorded",
        "funding_note": "Amounts are independent of available cash; funding coverage is assessed separately",
        "limitations": "Three demo bills per user; not inferred from source history or a complete expense forecast",
        "users_checked": len(users),
        "funding_accounts_checked": len(cash_accounts),
        "scheduled_payments_checked": len(saved),
        "total_scheduled_usd": money(
            sum(cents(r["amount"]) for r in saved)
        ),
        "totals_by_type_usd": {
            kind: money(
                sum(
                    cents(r["amount"])
                    for r in saved
                    if r["payment_type"] == kind
                )
            )
            for kind in sorted(RULES)
        },
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
        "Payment validation failed. Review the report.",
    )

    print(
        f"\nSaved {len(saved):,} scheduled payments "
        f"for {len(users):,} users."
    )
    print(f"All {len(checks)} scheduled-payment checks passed.")
    print("Total scheduled (USD):", report["total_scheduled_usd"])
    print("CSV:", output_path)
    print("Report:", report_path)


if __name__ == "__main__":
    main()
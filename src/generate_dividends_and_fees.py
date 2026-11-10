"""Create fictional dividend and fee events after the simulated trades."""

import csv
import json
from collections import Counter
from pathlib import Path

from calculate_net_worth import cents, money, require
from generate_assets import COLUMNS as ASSET_COLUMNS, clean_text
from generate_asset_prices import valid_price
from generate_holdings import read_table
from generate_portfolio_trades import (
    COLUMNS as TRADE_COLUMNS, load_inputs, validate_trades,
)
from generate_price_history import DATES


VERSION = "dividends_and_fees_v1"
DIVIDEND_DATE = "2025-01-24"
FEE_DATE = "2025-01-27"
FEE_CENTS = 500

DIVIDEND_CENTS = {
    "demo_stock_01": 50,
    "demo_stock_02": 35,
    "demo_etf_01": 20,
    "demo_etf_02": 15,
}

COLUMNS = [
    "event_id", "user_id", "account_id", "event_date", "event_sequence",
    "event_type", "asset_id", "eligible_quantity", "amount_per_unit",
    "amount", "currency", "data_origin",
]

ASSET_FIELDS = {"asset_id", "eligible_quantity", "amount_per_unit"}


def event_id(aid, day, kind, asset):
    return f"cash_{aid}_{day}_{kind.lower()}_{asset or 'account'}"


def load_trade_state(root):
    inputs = load_inputs(root)
    investments, opening_cash, opening_units, _ = inputs
    data = root / "data/processed"

    trades = read_table(
        data / "portfolio_trade_events.csv", TRADE_COLUMNS
    )
    require(
        all(validate_trades(trades, *inputs).values()),
        "Trade validation failed. "
        "Rerun src/generate_portfolio_trades.py.",
    )
    require(
        DIVIDEND_DATE in DATES
        and FEE_DATE in DATES
        and max(r["event_date"] for r in trades)
        < DIVIDEND_DATE < FEE_DATE,
        "Dividend and fee dates must follow all trades "
        "within the price window.",
    )

    assets = read_table(data / "assets.csv", ASSET_COLUMNS)
    require(
        {
            r["asset_id"]
            for r in assets
            if r["asset_type"] in {"STOCK", "ETF"}
        } == set(DIVIDEND_CENTS),
        "Dividend rules do not match the stock and ETF catalog.",
    )

    cash = opening_cash.copy()
    units = {
        aid: positions.copy()
        for aid, positions in opening_units.items()
    }

    for row in sorted(
        trades,
        key=lambda r: (
            r["account_id"],
            r["event_date"],
            int(r["event_sequence"]),
        ),
    ):
        aid, asset = row["account_id"], row["asset_id"]
        sign = 1 if row["event_type"] == "BUY" else -1

        cash[aid] -= sign * cents(row["amount"])
        units[aid][asset] = (
            units[aid].get(asset, 0)
            + sign * int(row["quantity"])
        )

    return investments, cash, units


def make_event(
    account, day, sequence, kind, amount,
    asset="", quantity="", rate="",
):
    aid = account["account_id"]

    return {
        "event_id": event_id(aid, day, kind, asset),
        "user_id": account["user_id"],
        "account_id": aid,
        "event_date": day,
        "event_sequence": str(sequence),
        "event_type": kind,
        "asset_id": asset,
        "eligible_quantity": quantity,
        "amount_per_unit": rate,
        "amount": money(amount),
        "currency": "USD",
        "data_origin": "synthetic_extension",
    }


def generate_events(investments, cash_after_trades, units):
    events = []

    for aid in sorted(investments):
        available = cash_after_trades[aid]
        sequence = 0

        for asset in sorted(DIVIDEND_CENTS):
            quantity = units[aid].get(asset, 0)

            if quantity > 0:
                sequence += 1
                rate = DIVIDEND_CENTS[asset]
                amount = quantity * rate
                available += amount

                events.append(make_event(
                    investments[aid],
                    DIVIDEND_DATE,
                    sequence,
                    "DIVIDEND",
                    amount,
                    asset,
                    str(quantity),
                    money(rate),
                ))

        fee = min(FEE_CENTS, available)

        if fee > 0:
            events.append(make_event(
                investments[aid], FEE_DATE, 1, "FEE", fee
            ))

    return events


def read_events(path):
    # Fee rows intentionally leave the asset-specific fields blank.
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        require(
            reader.fieldnames == COLUMNS,
            "Unexpected cash-event columns.",
        )
        return list(reader)


def validate_events(
    rows, investments, cash_after_trades, units
):
    required = set(COLUMNS) - ASSET_FIELDS

    checks = {
        "schema_and_required_fields_valid": all(
            set(r) == set(COLUMNS)
            and all(clean_text(r.get(c)) for c in required)
            and all(
                isinstance(r.get(c), str)
                for c in ASSET_FIELDS
            )
            for r in rows
        ),
        "event_ids_unique": (
            len({r.get("event_id") for r in rows}) == len(rows)
        ),
        "account_date_sequence_keys_unique": len({
            (
                r.get("account_id"),
                r.get("event_date"),
                r.get("event_sequence"),
            )
            for r in rows
        }) == len(rows),
        "ownership_currency_and_origin_correct": all(
            r.get("account_id") in investments
            and r.get("user_id")
            == investments[r["account_id"]]["user_id"]
            and r.get("currency") == "USD"
            and r.get("data_origin") == "synthetic_extension"
            for r in rows
        ),
        "event_types_dates_and_ids_valid": all(
            r.get("event_type") in {"DIVIDEND", "FEE"}
            and r.get("event_date") == (
                DIVIDEND_DATE
                if r.get("event_type") == "DIVIDEND"
                else FEE_DATE
            )
            and r.get("event_id") == event_id(
                r.get("account_id"),
                r.get("event_date"),
                r.get("event_type"),
                r.get("asset_id"),
            )
            for r in rows
        ),
        "amounts_positive_with_cent_precision": all(
            valid_price(r.get("amount"))
            for r in rows
        ),
        "asset_fields_match_event_type": all(
            (
                r.get("asset_id") in DIVIDEND_CENTS
                and clean_text(r.get("eligible_quantity"))
                and valid_price(r.get("amount_per_unit"))
            )
            if r.get("event_type") == "DIVIDEND"
            else all(r.get(c) == "" for c in ASSET_FIELDS)
            for r in rows
        ),
    }

    details = dict.fromkeys([
        "dividend_and_fee_coverage_complete",
        "event_sequences_correct",
        "dividend_units_rates_and_amounts_match",
        "fees_match_cash_limited_rule",
        "cash_nonnegative_after_each_event",
        "closing_cash_reconciles_per_account",
    ], False)

    if not all(checks.values()):
        return {**checks, **details}

    expected = {}
    dividend_totals = Counter()
    fees = {}

    for aid in investments:
        eligible = sorted(
            asset
            for asset in DIVIDEND_CENTS
            if units[aid].get(asset, 0) > 0
        )

        for sequence, asset in enumerate(eligible, 1):
            quantity = units[aid][asset]
            rate = DIVIDEND_CENTS[asset]

            expected[(aid, "DIVIDEND", asset)] = (
                str(sequence),
                str(quantity),
                money(rate),
                quantity * rate,
            )
            dividend_totals[aid] += quantity * rate

        fees[aid] = min(
            FEE_CENTS,
            cash_after_trades[aid] + dividend_totals[aid],
        )

        if fees[aid] > 0:
            expected[(aid, "FEE", "")] = (
                "1", "", "", fees[aid]
            )

    actual_keys = [
        (r["account_id"], r["event_type"], r["asset_id"])
        for r in rows
    ]
    details["dividend_and_fee_coverage_complete"] = (
        Counter(actual_keys) == Counter(expected.keys())
    )

    if not details["dividend_and_fee_coverage_complete"]:
        return {**checks, **details}

    details.update(dict.fromkeys(details, True))
    closing_cash = cash_after_trades.copy()

    for row in rows:
        sequence, quantity, rate, amount = expected[
            (
                row["account_id"],
                row["event_type"],
                row["asset_id"],
            )
        ]

        details["event_sequences_correct"] &= (
            row["event_sequence"] == sequence
        )

        if row["event_type"] == "DIVIDEND":
            details["dividend_units_rates_and_amounts_match"] &= (
                row["eligible_quantity"] == quantity
                and row["amount_per_unit"] == rate
                and cents(row["amount"]) == amount
            )
        else:
            details["fees_match_cash_limited_rule"] &= (
                cents(row["amount"]) == amount
            )

    # Numeric sorting follows validation of the sequence values.
    if details["event_sequences_correct"]:
        for row in sorted(
            rows,
            key=lambda r: (
                r["account_id"],
                r["event_date"],
                int(r["event_sequence"]),
            ),
        ):
            aid = row["account_id"]
            sign = (
                1 if row["event_type"] == "DIVIDEND" else -1
            )

            closing_cash[aid] += sign * cents(row["amount"])
            details["cash_nonnegative_after_each_event"] &= (
                closing_cash[aid] >= 0
            )

        details["closing_cash_reconciles_per_account"] = all(
            closing_cash[aid]
            == cash_after_trades[aid]
            + dividend_totals[aid]
            - fees[aid]
            for aid in investments
        )
    else:
        details["cash_nonnegative_after_each_event"] = False
        details["closing_cash_reconciles_per_account"] = False

    return {**checks, **details}


def main():
    root = Path(__file__).resolve().parents[1]
    output_path = root / "data/processed/portfolio_cash_events.csv"
    report_path = root / "docs/portfolio_cash_event_validation.json"

    inputs = load_trade_state(root)
    events = generate_events(*inputs)

    require(
        all(validate_events(events, *inputs).values()),
        "Cash-event validation failed. No outputs were written.",
    )

    with output_path.open(
        "w", encoding="utf-8", newline=""
    ) as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(events)

    saved = read_events(output_path)
    checks = validate_events(saved, *inputs)
    checks["csv_matches_generated_records"] = saved == events

    totals = {
        kind: sum(
            cents(r["amount"])
            for r in saved
            if r["event_type"] == kind
        )
        for kind in ("DIVIDEND", "FEE")
    }
    counts = Counter(r["event_type"] for r in saved)

    report = {
        "scope": (
            "Simulated dividends and account fees "
            "after validated trades"
        ),
        "generator_version": VERSION,
        "generation_rule": (
            "Fixed rates and cash-limited fee; no randomness"
        ),
        "dividend_date": DIVIDEND_DATE,
        "fee_date": FEE_DATE,
        "dividend_per_unit_usd": {
            asset: money(value)
            for asset, value in DIVIDEND_CENTS.items()
        },
        "fee_limit_usd": money(FEE_CENTS),
        "eligibility_rule": (
            "Positive stock/ETF units held after all trades, "
            "at payment time"
        ),
        "fee_rule": (
            "Lesser of USD 5.00 and available investment cash; "
            "omit zero charges"
        ),
        "waiver_rule": (
            "Any uncharged fee portion is waived, "
            "not accrued as debt"
        ),
        "blank_fields_note": (
            "Fee asset_id, eligible_quantity, "
            "and amount_per_unit are blank"
        ),
        "limitations": (
            "No ex-dividend/record-date model, taxes, "
            "or dividend price adjustment; fictional distributions"
        ),
        "investment_accounts_checked": len(inputs[0]),
        "events_checked": len(saved),
        "event_type_counts": dict(counts),
        "accounts_without_fee": (
            len(inputs[0]) - counts["FEE"]
        ),
        "totals_usd": {
            "investment_cash_after_trades": money(
                sum(inputs[1].values())
            ),
            "dividends": money(totals["DIVIDEND"]),
            "fees": money(totals["FEE"]),
            "investment_cash_after_events": money(
                sum(inputs[1].values())
                + totals["DIVIDEND"]
                - totals["FEE"]
            ),
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
        "Cash-event validation failed. Review the report.",
    )

    print(
        f"\nSaved {counts['DIVIDEND']:,} dividends "
        f"and {counts['FEE']:,} fees."
    )
    print(f"All {len(checks)} cash-event checks passed.")
    print("CSV:", output_path)
    print("Report:", report_path)


if __name__ == "__main__":
    main()
    
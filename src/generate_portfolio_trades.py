"""Generate and replay-check fictional trades using existing opening balances."""

import csv
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from random import Random

from calculate_net_worth import CASH_COLUMNS, cents, money, require
from calculate_portfolio_opening import COLUMNS as OPENING_COLUMNS
from generate_assets import COLUMNS as ASSET_COLUMNS, clean_text, validate_assets
from generate_asset_prices import AS_OF_DATE, PRICE_COLUMNS, valid_price, validate_prices
from generate_holdings import ACCOUNT_COLUMNS, HOLDING_COLUMNS, read_table, validate_holdings
from generate_price_history import DATES, validate_history


VERSION = "portfolio_trades_v1"
BASE_SEED = 42
MAX_UNITS = 5
TRADE_DATES = (DATES[6], DATES[20])
COLUMNS = [
    "event_id", "user_id", "account_id", "event_date", "event_sequence",
    "event_type", "asset_id", "quantity", "unit_price", "amount",
    "currency", "data_origin",
]


def event_id(account_id, day, sequence):
    return f"trade_{account_id}_{day}_{sequence}"


def load_inputs(root):
    data = root / "data" / "processed"
    users = read_table(
        root / "data/interim/users.csv",
        ["user_id", "user_name", "archetype"],
    )
    accounts = read_table(data / "accounts.csv", ACCOUNT_COLUMNS)
    cash = read_table(data / "cash_balance_snapshots.csv", CASH_COLUMNS)
    assets = read_table(data / "assets.csv", ASSET_COLUMNS)
    prices = read_table(data / "asset_prices.csv", PRICE_COLUMNS)
    history = read_table(data / "asset_price_history.csv", PRICE_COLUMNS)
    holdings = read_table(data / "holding_snapshots.csv", HOLDING_COLUMNS)
    opening = read_table(
        data / "portfolio_opening_balances.csv", OPENING_COLUMNS
    )

    user_ids = {r["user_id"] for r in users}
    account_ids = {r["account_id"] for r in accounts}
    require(len(user_ids) == len(users), "Duplicate user IDs.")
    require(
        len(account_ids) == len(accounts)
        and Counter((r["user_id"], r["account_type"]) for r in accounts)
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
        "Invalid account identities or ownership.",
    )
    investments = {
        r["account_id"]: r
        for r in accounts
        if r["account_type"] == "INVESTMENT"
    }
    require(
        Counter((r["account_id"], r["as_of_date"]) for r in cash)
        == Counter((aid, AS_OF_DATE) for aid in account_ids)
        and all(
            r["currency"] == "USD"
            and r["data_origin"] == "synthetic_extension"
            for r in cash
        ),
        "Invalid cash snapshot coverage, dates, currency, or origin.",
    )
    all_cash = {
        r["account_id"]: cents(r["cash_balance"])
        for r in cash
    }
    opening_cash = {aid: all_cash[aid] for aid in investments}

    require(
        all(validate_assets(assets).values()),
        "Asset validation failed.",
    )
    assets_by_id = {r["asset_id"]: r for r in assets}
    require(
        all(validate_prices(prices, assets_by_id).values()),
        "Opening price validation failed.",
    )
    opening_prices = {r["asset_id"]: r for r in prices}
    require(
        all(
            validate_history(
                history, assets_by_id, opening_prices
            ).values()
        ),
        "Price history is incomplete or stale. "
        "Rerun src/generate_price_history.py.",
    )
    opening_keys = {
        (r["asset_id"], r["price_date"], r["quote_currency"])
        for r in prices
    }
    require(
        all(
            validate_holdings(
                holdings, investments, assets_by_id, opening_keys
            ).values()
        ),
        "Opening holding validation failed.",
    )
    price_lookup = {
        (r["asset_id"], r["price_date"], r["quote_currency"]):
        cents(r["price"])
        for r in history
    }
    positions = {aid: {} for aid in investments}
    for row in holdings:
        positions[row["account_id"]][row["asset_id"]] = int(
            Decimal(row["quantity"])
        )

    require(
        Counter(
            (r["account_id"], r["as_of_date"], r["currency"])
            for r in opening
        )
        == Counter(
            (aid, AS_OF_DATE, "USD")
            for aid in investments
        ),
        "Missing, duplicate, or wrongly dated portfolio opening balances.",
    )
    for row in opening:
        aid = row["account_id"]
        holding_value = sum(
            quantity * price_lookup[(asset, AS_OF_DATE, "USD")]
            for asset, quantity in positions[aid].items()
        )
        require(
            row["user_id"] == investments[aid]["user_id"]
            and row["data_origin"] == "synthetic_extension"
            and cents(row["opening_cash"]) == opening_cash[aid]
            and cents(row["opening_holdings_value"]) == holding_value
            and cents(row["opening_portfolio_value"])
            == opening_cash[aid] + holding_value,
            "Stale opening balances. "
            "Rerun src/calculate_portfolio_opening.py.",
        )
    return investments, opening_cash, positions, price_lookup


def generate_trades(
    investments, opening_cash, opening_positions, prices
):
    events = []
    asset_ids = sorted({key[0] for key in prices})

    for aid in sorted(investments):
        cash = opening_cash[aid]
        positions = opening_positions[aid].copy()

        for day in TRADE_DATES:
            rng = Random(f"{VERSION}|{BASE_SEED}|{aid}|{day}")

            for sequence, kind in ((1, "SELL"), (2, "BUY")):
                if kind == "SELL":
                    candidates = sorted(
                        asset
                        for asset, units in positions.items()
                        if units > 0
                    )
                else:
                    candidates = [
                        asset
                        for asset in asset_ids
                        if prices[(asset, day, "USD")] <= cash
                    ]

                require(
                    bool(candidates),
                    f"No eligible asset for {kind}: {aid}, {day}.",
                )
                asset = rng.choice(candidates)
                price = prices[(asset, day, "USD")]
                limit = (
                    positions[asset]
                    if kind == "SELL"
                    else cash // price
                )
                quantity = rng.randint(1, min(MAX_UNITS, limit))
                amount = quantity * price
                sign = 1 if kind == "BUY" else -1

                positions[asset] = (
                    positions.get(asset, 0) + sign * quantity
                )
                cash -= sign * amount

                events.append({
                    "event_id": event_id(aid, day, sequence),
                    "user_id": investments[aid]["user_id"],
                    "account_id": aid,
                    "event_date": day,
                    "event_sequence": str(sequence),
                    "event_type": kind,
                    "asset_id": asset,
                    "quantity": str(quantity),
                    "unit_price": money(price),
                    "amount": money(amount),
                    "currency": "USD",
                    "data_origin": "synthetic_extension",
                })

    return events


def validate_trades(
    rows, investments, opening_cash, opening_positions, prices
):
    checks = {
        "schema_and_required_fields_valid": bool(rows) and all(
            set(r) == set(COLUMNS)
            and all(clean_text(r.get(c)) for c in COLUMNS)
            for r in rows
        ),
        "event_ids_unique": (
            len({r.get("event_id") for r in rows}) == len(rows)
        ),
        "complete_trade_schedule": Counter(
            (
                r.get("account_id"),
                r.get("event_date"),
                r.get("event_sequence"),
                r.get("event_type"),
            )
            for r in rows
        ) == Counter(
            (aid, day, sequence, kind)
            for aid in investments
            for day in TRADE_DATES
            for sequence, kind in (("1", "SELL"), ("2", "BUY"))
        ),
        "ownership_currency_and_origin_correct": all(
            r.get("account_id") in investments
            and r.get("user_id")
            == investments[r["account_id"]]["user_id"]
            and r.get("currency") == "USD"
            and r.get("data_origin") == "synthetic_extension"
            for r in rows
        ),
        "event_ids_follow_rule": all(
            r.get("event_id")
            == event_id(
                r.get("account_id"),
                r.get("event_date"),
                r.get("event_sequence"),
            )
            for r in rows
        ),
        "quantities_and_amounts_valid": all(
            r.get("quantity")
            in {str(n) for n in range(1, MAX_UNITS + 1)}
            and valid_price(r.get("unit_price"))
            and valid_price(r.get("amount"))
            for r in rows
        ),
        "same_date_currency_prices_exist": all(
            (
                r.get("asset_id"),
                r.get("event_date"),
                r.get("currency"),
            ) in prices
            for r in rows
        ),
    }
    controls = {
        "execution_prices_and_amounts_match": False,
        "sufficient_cash_before_every_buy": False,
        "sufficient_units_before_every_sale": False,
        "trade_value_conserved_at_execution_price": False,
        "closing_cash_reconciles_per_account": False,
        "closing_units_reconcile_per_account_asset": False,
    }

    if not all(checks.values()):
        return {**checks, **controls}

    controls = dict.fromkeys(controls, True)
    cash = opening_cash.copy()
    positions = {
        aid: units.copy()
        for aid, units in opening_positions.items()
    }
    cash_changes = Counter()
    unit_changes = Counter()

    ordered = sorted(
        rows,
        key=lambda r: (
            r["account_id"],
            r["event_date"],
            int(r["event_sequence"]),
        ),
    )

    for row in ordered:
        aid, asset = row["account_id"], row["asset_id"]
        quantity = int(row["quantity"])
        amount = cents(row["amount"])
        price = prices[
            (asset, row["event_date"], row["currency"])
        ]

        controls["execution_prices_and_amounts_match"] &= (
            cents(row["unit_price"]) == price
            and amount == quantity * price
        )

        previous_units = positions[aid].get(asset, 0)
        previous_value = cash[aid] + previous_units * price

        if row["event_type"] == "BUY":
            controls["sufficient_cash_before_every_buy"] &= (
                cash[aid] >= amount
            )
            cash[aid] -= amount
            positions[aid][asset] = previous_units + quantity
        else:
            controls["sufficient_units_before_every_sale"] &= (
                previous_units >= quantity
            )
            cash[aid] += amount
            positions[aid][asset] = previous_units - quantity

        controls["trade_value_conserved_at_execution_price"] &= (
            cash[aid] + positions[aid][asset] * price
            == previous_value
        )

    # A separate signed aggregation reconciles the replayed closing state.
    for row in rows:
        key = (row["account_id"], row["asset_id"])

        if row["event_type"] == "BUY":
            cash_changes[row["account_id"]] -= cents(row["amount"])
            unit_changes[key] += int(row["quantity"])
        else:
            cash_changes[row["account_id"]] += cents(row["amount"])
            unit_changes[key] -= int(row["quantity"])

    controls["closing_cash_reconciles_per_account"] = all(
        cash[aid] == opening_cash[aid] + cash_changes[aid]
        for aid in investments
    )
    controls["closing_units_reconcile_per_account_asset"] = all(
        quantity
        == opening_positions[aid].get(asset, 0)
        + unit_changes[(aid, asset)]
        for aid, holdings in positions.items()
        for asset, quantity in holdings.items()
    )

    return {**checks, **controls}


def main():
    root = Path(__file__).resolve().parents[1]
    output_path = root / "data/processed/portfolio_trade_events.csv"
    report_path = root / "docs/portfolio_trade_validation.json"

    inputs = load_inputs(root)
    events = generate_trades(*inputs)

    require(
        all(validate_trades(events, *inputs).values()),
        "Generated trades failed validation. No outputs were written.",
    )

    with output_path.open(
        "w", encoding="utf-8", newline=""
    ) as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(events)

    saved = read_table(output_path, COLUMNS)
    checks = validate_trades(saved, *inputs)
    checks["csv_matches_generated_records"] = saved == events

    buy_total = sum(
        cents(r["amount"])
        for r in saved
        if r["event_type"] == "BUY"
    )
    sell_total = sum(
        cents(r["amount"])
        for r in saved
        if r["event_type"] == "SELL"
    )
    opening_cash_total = sum(inputs[1].values())

    report = {
        "scope": (
            "Simulated BUY and SELL events with cash and unit replay checks"
        ),
        "generator_version": VERSION,
        "base_seed": BASE_SEED,
        "seed_rule": "Version, base seed, account_id, and trade date",
        "opening_date": AS_OF_DATE,
        "trade_dates": list(TRADE_DATES),
        "trade_rule": (
            "One SELL followed by one BUY per account on each trade date"
        ),
        "quantity_rule": (
            "1 to 5 whole units, capped by units owned or cash available"
        ),
        "execution_rule": (
            "Same-date USD simulated price; "
            "immediate cash and unit settlement"
        ),
        "selection_note": (
            "Buy and sell may reference the same asset; "
            "this is not a trading strategy"
        ),
        "limitations": (
            "Trade-only scenario; excludes fees, dividends, transfers, "
            "taxes, spread, and slippage"
        ),
        "amount_note": (
            "Trade amounts are gross values, "
            "not investment profits or household spending"
        ),
        "investment_accounts_checked": len(inputs[0]),
        "events_checked": len(saved),
        "event_type_counts": dict(
            Counter(r["event_type"] for r in saved)
        ),
        "totals_usd": {
            "opening_investment_cash": money(opening_cash_total),
            "buy_amount": money(buy_total),
            "sell_amount": money(sell_total),
            "investment_cash_after_trades": money(
                opening_cash_total + sell_total - buy_total
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
        "Trade validation failed. Review the report.",
    )
    print(
        f"\nSaved {len(saved):,} simulated trades "
        f"for {len(inputs[0]):,} investment accounts."
    )
    print(f"All {len(checks)} portfolio-trade checks passed.")
    print("CSV:", output_path)
    print("Report:", report_path)


if __name__ == "__main__":
    main()
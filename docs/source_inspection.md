# Initial source inspection

This is a preparation note from inspecting the unchanged downloaded JSON. We will reproduce and explain these checks in a later Python lesson. It does not mean the learner's data pipeline has been implemented.

## Confirmed counts

| Check | Result |
|---|---:|
| Users | 500 |
| User groups | 10 |
| Transactions | 120,817 |
| CREDIT transactions | 8,371 |
| DEBIT transactions | 112,446 |
| Duplicate user IDs | 0 |
| Duplicate transaction IDs | 0 |
| Negative amounts | 0 |
| Users whose `tx_count` disagrees with their transaction list | 0 |

Earliest transaction: `2024-01-01`. Latest transaction: `2024-12-28`.

## How the JSON is organized

JSON is a text format that can hold records inside other records. This file contains metadata and an `archetypes` object. Each archetype contains a list of users, and each user contains a list of transactions.

The ten group labels are `overspender`, `high_debt`, `high_earner`, `recent_grad`, `freelancer`, `retired_fixed`, `dual_income`, `paycheck_to_paycheck`, `small_biz_owner`, and `gig_worker`. These are synthetic scenario labels provided by the author, not inferred facts about real people.

| Level | Observed fields |
|---|---|
| File | `generated_at`, `total_users`, `archetypes` |
| User | `user_id`, `name`, `tx_count`, `avg_monthly_income`, `transactions` |
| Transaction | `transaction_id`, `date`, `description`, `merchant_name`, `amount`, `balance`, `transaction_type`, `category`, `subcategory` |

When we later flatten the transactions into a table, we must carry the parent `user_id` into each transaction row. The transaction object itself does not contain that link.

## Limitations that affect future calculations

1. **Amounts need direction.** Both credit and debit amounts are stored as nonnegative numbers. We will derive a signed cash movement after validating `transaction_type`.
2. **Balances are not yet reliable ledger evidence.** Only 8,678 of 120,317 adjacent transaction pairs reconcile to within one cent when tested in supplied order as previous balance plus signed next amount. No account ID or within-day ordering timestamp is present. This diagnostic does not identify which values are wrong. We will preserve the field, flag its limitations, and avoid using it as validated net-worth or account-balance input.
3. **Some merchant/category pairings look inconsistent.** For example, a source record pairs Uber Eats with PERSONAL_CARE / Salon/Spa. We will preserve raw labels, record quality rules, and separate verified corrections from assumptions.
4. **No currency field is supplied.** The author describes U.S.-calibrated data. Treating amounts as USD will be an explicit project assumption, not an observed row-level currency fact.
5. **The snapshot is incomplete for wealth reporting.** It has no detailed account table, opening balances, holdings, prices, liability balances, goals, or contractual future payment schedules. These must be sourced or explicitly modeled before those dashboard cards are built.
6. **Outflows are not all spending.** INVESTMENTS and LOAN_PAYMENT categories are present. We will distinguish cash movement from consumption and avoid inventing a principal/interest split.

These limitations make the source useful for learning validation, but it should not be described as audited financial data or used to estimate real population behavior.

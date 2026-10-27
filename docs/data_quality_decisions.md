# Data quality decisions

## Verified checkpoint

The extracted tables contain 500 synthetic users and 120,817 transactions.

- All 11 configured table validation checks passed.
- Exported user and transaction fields match the original JSON.
- Reconciliation found zero unmatched records in either direction.

Evidence:
- [Table validation](table_validation.json)
- [Source reconciliation](source_reconciliation.json)
- [Initial source inspection](source_inspection.md)

These checks establish extraction accuracy within their stated scope.
They do not establish that the source is an audited financial ledger.

## Decisions for subsequent development

| Area | Observation | Handling decision |
|---|---|---|
| Amount direction | Amounts are nonnegative; CREDIT and DEBIT provide direction. | Preserve the original amount. Derive positive cash movement for CREDIT and negative cash movement for DEBIT. |
| Source balances | Supplied balances are unverified. Account IDs and within-day ordering are absent. | Retain `source_balance` for traceability. Exclude it from net worth, available cash, and runway calculations until a supported balance model exists. |
| Categories | Some merchant/category combinations appear inconsistent, including Uber Eats under PERSONAL_CARE / Salon/Spa. | Preserve source labels. Document suspicious combinations for review. Any later correction must use a separate, documented mapping. |
| Currency | Transaction records contain no currency field. | Treat USD as an explicit demonstration assumption. Do not present it as a source-provided field or infer exchange rates. |
| Reporting period | Observed transaction dates run from 2024-01-01 through 2024-12-28. | Label reports with this historical coverage. Do not imply complete calendar-year coverage or live data. |
| Cash flow and spending | Investment and loan-payment categories are present. | Separate cash movement from consumption spending. Do not invent a loan principal/interest split. |
| Missing financial entities | The snapshot lacks detailed holdings, verified account balances, liability balances, goals, and future payment schedules. | Design clearly labeled synthetic extensions linked to existing user IDs. Document their assumptions and origin. |
| Interpretation | Users and their groups are synthetic scenarios. | Present findings as demonstration results, without claims about real customers or population behavior. |

## File handling

- `data/raw/`: preserve the downloaded source unchanged.
- `data/interim/`: keep reproducible exports of selected source fields.
- `data/processed/`: reserve for later transformations using documented rules.
- `docs/`: retain validation evidence and explanations of decisions.

Do not silently delete or overwrite questionable source records.
Record any future exclusions or corrections and explain their effect.

## Implementation status

This document defines the rules for later development.
The processed-data transformations and synthetic extensions have
not yet been implemented.
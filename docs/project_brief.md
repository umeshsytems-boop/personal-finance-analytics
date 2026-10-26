# Project brief

## Objective

Build a medium-sized, reproducible personal-finance analytics project. First deliver a conventional Python, SQL, and Power BI implementation. Then reuse its validated data and calculations for a custom web dashboard inspired by the visual references.

## First useful deliverable

A monthly cash-flow report for selected fictional users, showing income credits, debit outflows, net cash movement, category breakdowns, and month-to-month changes.

The first version will use the actual 2024 source window. Historical values must be labeled with that period rather than presented as live balances.

## Business questions

- How much money came in and went out each month?
- Which categories account for the largest outflows?
- Which users have recurring negative monthly cash flow?
- How do patterns differ across the source's fictional user groups?
- Which data checks must pass before a metric can be trusted?

## Proposed learning stack

- Python for reading source files, transformation, and validation.
- SQL Server Developer for local development, with SSMS as the query editor.
- Power BI Desktop for the initial report.
- GitHub for code, documentation, validation evidence, and report screenshots.

Power BI Desktop is free for local report creation. SQL Server Developer is free for non-production development and testing. Cloud sharing and hosted deployments will be considered separately when needed; no paid cloud service is required for this first stage.

Sources: [Microsoft Power BI Desktop](https://learn.microsoft.com/en-us/power-bi/fundamentals/desktop-get-the-desktop), [Microsoft SQL Server downloads](https://www.microsoft.com/en-us/sql-server/sql-server-downloads).

## Definitions we will validate before implementation

- Source amounts are nonnegative; `CREDIT` and `DEBIT` provide direction.
- Cash movement and spending are different metrics. An investment purchase is a cash outflow but is not automatically a consumption expense.
- Loan payments cannot be divided into principal and interest without supporting fields or an explicit model.
- Net cash movement is not an account balance. A balance requires a verified opening balance, complete movements, and ordering rules.
- Net worth requires assets minus liabilities at a specified date.
- Portfolio value changes are not automatically investment returns; contributions, withdrawals, fees, and distributions need separate treatment.

## Later extensions

The banking snapshot does not include usable detailed holdings, debt balances, account opening balances, savings goals, or payment schedules. We will design explicitly synthetic extensions when those modules begin, link them to existing fictional user IDs, and document every assumption.

Public market prices will join through asset identifiers and dates. They do not supply customer identities or a person's holdings. We will not claim that an unrelated portfolio dataset belongs to these banking users.

## Learning cadence

Each lesson will contain a small task, an explanation of why it matters, a completion check, and a GitHub mini-step. Features will only be marked complete after the learner runs and checks them locally.

## Current checkpoint

Step 1 materials prepared. Learner setup and GitHub publication are pending. No software pipeline or dashboard has been built yet.

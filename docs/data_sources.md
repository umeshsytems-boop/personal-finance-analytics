# Data sources

Checked on October 25, 2026 (America/New_York).

## Selected now: synthetic banking transactions

- Dataset: The Artha Personal-Finance Reasoning Benchmark, by Tejashwar Reddy Katika (2026).
- Publisher page: https://huggingface.co/datasets/Tej-Katika/artha-benchmark
- Dataset DOI: https://doi.org/10.57967/hf/9387
- Source file: `data/artha_users_v2.json`
- Download: https://huggingface.co/datasets/Tej-Katika/artha-benchmark/resolve/main/data/artha_users_v2.json?download=true
- Dataset revision reviewed: `b05bd75379e8c36205b22cb2a66b093eb35cb729`
- Pinned download: https://huggingface.co/datasets/Tej-Katika/artha-benchmark/resolve/b05bd75379e8c36205b22cb2a66b093eb35cb729/data/artha_users_v2.json?download=true
- Local destination: `data/raw/artha/artha_users_v2.json`
- Observed size: 48,923,018 bytes (about 46.7 MiB).
- Observed population: 500 fictional users, 10 groups, and 120,817 transactions.
- Observed transaction window: January 1 through December 28, 2024.
- Source metadata `generated_at`: `2026-05-10`. This is not the transaction period.
- SHA-256: `2831720921fd70ba9d74effc449d6774c88d00db081f9995fa524a6bf815b958`
- The downloaded file matches the publisher's stated checksum. It is included unchanged in the starter download.

The dataset card declares CC BY 4.0. The original component license and citation file are retained in `docs/third_party/`. The source is synthetic, although the author describes its spending distributions as calibrated using U.S. Bureau of Labor Statistics survey data. This project has not independently validated that calibration.

### Manual download if the raw file is missing

1. Open the pinned download link above in a browser.
2. Save the file as `artha_users_v2.json`.
3. Place it in `data/raw/artha/` under the project folder.
4. Keep it unchanged. Do not rename it with a `.csv` extension.

To verify it later in Windows PowerShell, opened in the project folder:

```powershell
Get-FileHash .\data\raw\artha\artha_users_v2.json -Algorithm SHA256
```

The hash is a file fingerprint. It should match the value recorded above, ignoring letter case. A mismatch means the bytes differ; do not silently replace the expected value.

## Sources identified for later stages

| Component | Source | Intended use | Current status |
|---|---|---|---|
| Historical stock prices | [Stooq](https://stooq.com/db/h/) and [Apple history example](https://stooq.com/q/d/?s=aapl.us) | Evaluate daily historical stock prices for local portfolio exercises | Candidate only; no price file downloaded or validated. Publisher states personal use only. Do not redistribute raw data or assume public-app rights. |
| Historical crypto metrics | [Coin Metrics community archives](https://github.com/coinmetrics/data) | Evaluate BTC/ETH `PriceUSD` history matching 2024 | Candidate only; no market file downloaded or validated. Repository declares CC BY-NC 4.0. Attribute and observe the noncommercial restriction. |
| Customer holdings, goals, debt balances | Project-specific synthetic extensions | Supply fields absent from the banking snapshot | Not created yet. Must be labeled synthetic and connected explicitly to the existing user IDs. |

We will check actual date coverage, missing prices, corporate actions, price definitions, and terms when adding each market source. The current lesson only requires the banking file. No paid API or account connection is needed to download the selected banking snapshot.

## Source caveats already identified

Read `source_inspection.md` before using the supplied balances or categories. The small `investments_users_v2.json` in the source repository contains portfolio/user identifiers and counts, not the detailed security positions and trade ledger required by our dashboard; it is not part of this starter package.

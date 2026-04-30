# HLTV Rating 3.0 Verifier & Forensic Analysis

A complete, automated forensic analysis tool suite designed to verify the statistical integrity of HLTV's Rating 3.0 system.

This repository was created to definitively test the persistent community rumor that HLTV artificially manipulates (or "boosts") the Rating 3.0 statistics of certain top-tier CS2 players (e.g., ZywOo).

By applying forensic accounting techniques (Last Digit Test) and Kernel Density Estimation (KDE) to over **8,000 top-tier matches**, this project provides conclusive proof of whether the system exhibits signs of manual tampering or algorithmic truncation bias.

## Features

- **Anti-Bot Bypassing Scraper**: Utilizes `DrissionPage` to securely authenticate and scrape player match histories while bypassing Cloudflare protections.
- **Rating 3.0 Filtering**: Intelligently halts pagination upon encountering legacy Rating 2.0/1.0 data.
- **Statistical Forensic Analysis**:
  - **Last Digit Test (LDT)**: Uses Chi-Square goodness-of-fit to detect unnatural manipulation in the trailing decimals of ratings.
  - **KL Divergence**: Measures information entropy between actual rating distributions and perfect uniformity.
  - **KDE "Cliff" Detection**: Visualizes distributions to detect hardcoded "floors" or "ceilings" (unnatural truncation).

## Methodology

1. **Last Digit Uniformity**: In an unmanipulated mathematical system with high variance, the trailing decimal digits of ratings (e.g., the '5' in 1.25) should be perfectly uniform (10% distribution across 0-9).
2. **KDE Continuity**: If data manipulation pushes "bad" scores above a threshold (e.g., boosting a 0.98 to a 1.05), a density plot will reveal an unnatural "cliff" and an artificial peak.

## Installation

```bash
# We recommend using uv
uv venv
uv pip install -r requirements.txt
```

## Usage

1. **Scraping Data**:
   Ensure Google Chrome is installed. The script will automatically open a real browser window to bypass CAPTCHAs.
   ```bash
   python auto_scraper.py
   ```
2. **Running the LDT Analysis**:
   ```bash
   python analyze.py
   ```
3. **Running the KDE Analysis**:
   ```bash
   python analyze_kde.py
   ```

## Key Findings (Summary)

- **ZywOo is Clean**: ZywOo's ratings exhibited perfect statistical randomness in trailing digits ($p=0.38$) and continuous, smooth KDE distributions. There is **zero evidence** of manual score boosting.
- **No Manual Manipulation**: 17 out of 20 top players showed perfectly uniform distributions.
- **Algorithmic Truncation Bias**: Anomalies were found in NiKo, donk, and Jame's ratings (a massive spike in the trailing digit `5`). This is a documented phenomenon where extreme playstyles (e.g., Jame's extremely low death rate) hit boundary multipliers in HLTV's proprietary mathematical formula, causing rounding collapse. It is a machine artifact, not human intervention.

## License

MIT

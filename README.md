# Google Ads Negative Keyword Conflict Finder 🚫🔑

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)]()

A Python tool that finds conflicts between your positive keywords and negative keywords in Google Ads campaigns. Negative keyword conflicts silently block your ads, drain budgets, and kill performance — this script surfaces every conflict across campaigns, ad groups, and shared negative lists in seconds.

## The Problem

Negative keyword conflicts are one of the most common — and most invisible — mistakes in Google Ads. A campaign-level negative like `free` blocks your ad group keyword `free shipping offer`. A shared negative list added to the wrong campaign wipes out your best-performing ad group. Google Ads doesn't warn you. You only find out when impressions collapse.

## The Solution

Export your keywords and negatives from Google Ads Editor, run this script, and get a prioritized conflict report: which negatives are blocking which keywords, at which level (campaign vs. ad group vs. shared list), and how to fix each one.

## Features

- 📥 Parse Google Ads Editor CSV exports (keywords + negatives)
- 🔍 Detect exact, phrase, and broad match conflicts
- 📊 Report conflicts by campaign, ad group, and shared negative list
- 🏷️ Handle all negative match types (exact, phrase, broad)
- 📋 Generate prioritized conflict list (HIGH / MEDIUM / LOW severity)
- 💾 Export results as CSV or formatted console report
- ⚡ Analyze accounts with 100,000+ keywords in under 30 seconds
- 🔁 Run as a scheduled pre-launch audit
- 🛠️ Zero external dependencies — Python standard library only

## Tech Stack

- Python 3.8+ (standard library only — no pip install required)
- Optional: `pandas` for large dataset performance

## Installation

```bash
git clone https://github.com/mehranmoghadasi/google-ads-negative-conflict-finder.git
cd google-ads-negative-conflict-finder
python conflict_finder.py --demo   # test with built-in sample data
```

No `pip install` required. Uses Python standard library only.

## Exporting Data from Google Ads Editor

1. Open **Google Ads Editor**
2. Select the campaigns to audit
3. **File → Export → Export spreadsheet (CSV)**
4. Export both the **Keywords** and **Negative keywords** tabs
5. Save as `keywords.csv` and `negatives.csv`

## Usage

```bash
# Run with demo data (no CSV files needed)
python conflict_finder.py --demo

# Audit your account
python conflict_finder.py --keywords keywords.csv --negatives negatives.csv

# Save report as CSV
python conflict_finder.py --keywords keywords.csv --negatives negatives.csv --output conflicts.csv

# Show only high-severity conflicts
python conflict_finder.py --keywords keywords.csv --negatives negatives.csv --min-severity high
```

## Sample Output

```
Google Ads Negative Keyword Conflict Report
Generated: 2026-05-06 | Account audit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  HIGH SEVERITY (likely blocking significant traffic)

  Campaign: Brand_Exact | Ad Group: Core Brand
    Keyword:    [nike running shoes]  (exact)
    Blocked by: "running" (phrase negative, campaign level)
    Fix: Remove "running" from campaign negatives or move keyword to a separate campaign

  Campaign: Shopping_PMax | (Campaign Level)
    Keyword:    +buy +sneakers +online  (broad)
    Blocked by: [buy sneakers] (exact negative, shared list: Competitor Exclusions)
    Fix: Review Competitor Exclusions — [buy sneakers] is too broad for this campaign

🔶 MEDIUM SEVERITY (may limit reach)

  Campaign: Search_Generic | Ad Group: Footwear General
    Keyword:    "affordable shoes"  (phrase)
    Blocked by: affordable (broad negative, ad group level)
    Fix: Change broad negative to exact [affordable] or remove it

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total keywords analyzed:  4,832
Total negatives analyzed: 1,247
Conflicts found:          23  (2 high · 6 medium · 15 low)
```

## How Conflict Detection Works

| Positive Match Type | Negative Exact | Negative Phrase | Negative Broad |
|---------------------|----------------|-----------------|----------------|
| Exact `[keyword]`   | ✅ Blocked      | ✅ If phrase contained | ✅ If all words present |
| Phrase `"keyword"`  | Only if exact  | ✅ If phrase contained | ✅ If all words present |
| Broad `keyword`     | Only on exact  | Only phrase queries   | ✅ If all words present |

## Use Cases

- **Pre-launch audit**: Run before every campaign launch to catch conflicts early
- **Weekly health check**: Schedule as a cron job to catch newly introduced conflicts
- **Shared list review**: Identify shared negative lists that are too aggressive
- **Account takeover**: Quickly find inherited conflicts when taking over an account

## License

MIT License — see [LICENSE](LICENSE) for details.

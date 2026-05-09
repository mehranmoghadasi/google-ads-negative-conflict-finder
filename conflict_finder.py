#!/usr/bin/env python3
"""
Google Ads Negative Keyword Conflict Finder
===========================================
Detects conflicts between positive keywords and negative keywords in Google
Ads campaigns by analyzing CSV exports from Google Ads Editor.

Author: Mehran Moghadasi
License: MIT
GitHub:  https://github.com/mehranmoghadasi/google-ads-negative-conflict-finder

Usage:
    python conflict_finder.py --demo
    python conflict_finder.py --keywords keywords.csv --negatives negatives.csv
    python conflict_finder.py --keywords keywords.csv --negatives negatives.csv --output conflicts.csv
"""

import argparse
import csv
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path


# ─── Enums & Data Classes ─────────────────────────────────────────────────────

class MatchType(Enum):
    EXACT = "exact"
    PHRASE = "phrase"
    BROAD = "broad"


class Severity(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Keyword:
    text: str
    match_type: MatchType
    campaign: str
    ad_group: str
    status: str = "enabled"

    @property
    def clean_text(self):
        """Return keyword text without match type brackets/quotes."""
        return self.text.strip("[]"").strip().lower()

    @property
    def words(self):
        return set(self.clean_text.split())


@dataclass
class NegativeKeyword:
    text: str
    match_type: MatchType
    campaign: str
    ad_group: str = ""       # Empty if campaign-level
    shared_list: str = ""    # Name of shared negative list if applicable

    @property
    def clean_text(self):
        return self.text.strip("[]"").strip().lower()

    @property
    def words(self):
        return set(self.clean_text.split())

    @property
    def level(self):
        if self.shared_list:
            return f"shared list: {self.shared_list}"
        if self.ad_group:
            return "ad group level"
        return "campaign level"


@dataclass
class Conflict:
    keyword: Keyword
    negative: NegativeKeyword
    severity: Severity
    explanation: str
    fix: str


# ─── CSV Parsing ──────────────────────────────────────────────────────────────

def parse_match_type(raw):
    """Parse match type string from Google Ads Editor export."""
    raw = raw.strip().lower()
    if "exact" in raw:
        return MatchType.EXACT
    if "phrase" in raw:
        return MatchType.PHRASE
    return MatchType.BROAD


def parse_keywords_csv(filepath):
    """Parse keyword CSV export from Google Ads Editor.
    Expected columns: Campaign, Ad group, Keyword, Match type, Status
    """
    keywords = []
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            campaign = row.get("Campaign", row.get("campaign", "")).strip()
            ad_group = row.get("Ad group", row.get("Ad Group", row.get("ad_group", ""))).strip()
            kw_text  = row.get("Keyword", row.get("keyword", "")).strip()
            match_raw = row.get("Match type", row.get("match_type", "broad")).strip()
            status   = row.get("Status", row.get("status", "enabled")).strip().lower()

            if not kw_text or status in ("removed", "paused"):
                continue

            keywords.append(Keyword(
                text=kw_text,
                match_type=parse_match_type(match_raw),
                campaign=campaign,
                ad_group=ad_group,
                status=status,
            ))
    return keywords


def parse_negatives_csv(filepath):
    """Parse negative keyword CSV export from Google Ads Editor.
    Expected columns: Campaign, Ad group, Negative keyword, Match type
    """
    negatives = []
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            campaign = row.get("Campaign", row.get("campaign", "")).strip()
            ad_group = row.get("Ad group", row.get("Ad Group", row.get("ad_group", ""))).strip()
            neg_text = row.get(
                "Negative keyword",
                row.get("negative_keyword", row.get("Keyword", ""))
            ).strip()
            match_raw = row.get("Match type", row.get("match_type", "broad")).strip()
            shared    = row.get("List name", row.get("shared_list", "")).strip()

            if not neg_text:
                continue

            negatives.append(NegativeKeyword(
                text=neg_text,
                match_type=parse_match_type(match_raw),
                campaign=campaign,
                ad_group=ad_group,
                shared_list=shared,
            ))
    return negatives


# ─── Conflict Detection Logic ─────────────────────────────────────────────────

def keywords_conflict(kw, neg):
    """Determine if a negative keyword would block a positive keyword.

    Rules based on Google Ads matching behavior:
    - Negative EXACT:  blocks if the keyword text exactly matches the negative
    - Negative PHRASE: blocks if the negative phrase appears within the keyword
    - Negative BROAD:  blocks if ALL negative words appear in the keyword
    """
    kw_text  = kw.clean_text
    neg_text = neg.clean_text

    if neg.match_type == MatchType.EXACT:
        return kw_text == neg_text

    elif neg.match_type == MatchType.PHRASE:
        return neg_text in kw_text

    else:  # BROAD
        return neg.words.issubset(kw.words)


def assess_severity(kw, neg):
    """Assess the likely impact severity of a conflict."""
    # Campaign-level or shared list negatives affect the entire campaign
    if not neg.ad_group or neg.shared_list:
        return Severity.HIGH
    # Exact match conflicts are precise and definitely blocking
    if neg.match_type == MatchType.EXACT and kw.match_type == MatchType.EXACT:
        return Severity.HIGH
    if neg.match_type == MatchType.PHRASE:
        return Severity.MEDIUM
    return Severity.LOW


def build_fix(kw, neg):
    """Generate a human-readable fix suggestion."""
    if neg.shared_list:
        return (
            f"Review shared list '{neg.shared_list}' — "
            f"'{neg.clean_text}' may be too broad for this campaign"
        )
    if not neg.ad_group:
        return (
            f"Remove '{neg.clean_text}' from campaign-level negatives, "
            f"or move the keyword to a campaign without this negative"
        )
    return (
        f"Change negative '{neg.clean_text}' to a more specific match type, "
        f"or scope it to exclude only the conflicting ad group"
    )


def find_conflicts(keywords, negatives):
    """Main conflict detection: cross-reference all keywords against negatives
    within the same campaign (or shared lists applied to campaigns).
    """
    conflicts = []

    # Group negatives by campaign for efficient lookup
    campaign_negatives = {}
    for neg in negatives:
        campaign_negatives.setdefault(neg.campaign, []).append(neg)

    for kw in keywords:
        applicable = campaign_negatives.get(kw.campaign, [])
        for neg in applicable:
            # Ad-group-level negatives only apply to the same ad group
            if neg.ad_group and neg.ad_group != kw.ad_group:
                continue
            if keywords_conflict(kw, neg):
                severity = assess_severity(kw, neg)
                explanation = (
                    f"'{kw.text}' ({kw.match_type.value}) blocked by "
                    f"'{neg.text}' ({neg.match_type.value}, {neg.level})"
                )
                conflicts.append(Conflict(
                    keyword=kw,
                    negative=neg,
                    severity=severity,
                    explanation=explanation,
                    fix=build_fix(kw, neg),
                ))

    # Sort: HIGH → MEDIUM → LOW
    order = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2}
    conflicts.sort(key=lambda c: order[c.severity])
    return conflicts


# ─── Report Output ────────────────────────────────────────────────────────────

def print_report(conflicts, keywords, negatives):
    """Print a formatted, color-coded conflict report to stdout."""
    RED    = "\033[91m"; YELLOW = "\033[93m"
    CYAN   = "\033[96m"; RESET  = "\033[0m"; BOLD = "\033[1m"

    print(f"\n{BOLD}Google Ads Negative Keyword Conflict Report{RESET}")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("\u2501" * 55)

    high   = [c for c in conflicts if c.severity == Severity.HIGH]
    medium = [c for c in conflicts if c.severity == Severity.MEDIUM]
    low    = [c for c in conflicts if c.severity == Severity.LOW]

    for label, group, color, icon in [
        ("HIGH SEVERITY (likely blocking significant traffic)", high,   RED,    "\u26a0\ufe0f "),
        ("MEDIUM SEVERITY (may limit reach)",                  medium, YELLOW, "\U0001f536"),
        ("LOW SEVERITY (minor impact)",                        low,    CYAN,   "\u2139\ufe0f "),
    ]:
        if not group:
            continue
        print(f"\n{color}{icon} {label}{RESET}\n")
        for c in group:
            print(f"  Campaign: {c.keyword.campaign} | Ad Group: {c.keyword.ad_group or '(all)'}")
            print(f"    Keyword:    {c.keyword.text}  ({c.keyword.match_type.value})")
            print(f"    Blocked by: {c.negative.text} ({c.negative.match_type.value} negative, {c.negative.level})")
            print(f"    Fix: {c.fix}\n")

    print("\u2501" * 55)
    print(f"Total keywords analyzed:  {len(keywords):,}")
    print(f"Total negatives analyzed: {len(negatives):,}")
    print(f"Conflicts found:          {len(conflicts)}", end="")
    if conflicts:
        print(f"  ({RED}{len(high)} high{RESET} · {YELLOW}{len(medium)} medium{RESET} · {CYAN}{len(low)} low{RESET})")
    else:
        print(f"\n\n{BOLD}\u2705 No conflicts detected — your account looks clean!{RESET}")
    print()


def save_csv_report(conflicts, output_path):
    """Save conflict report as CSV."""
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "severity", "campaign", "ad_group", "keyword", "keyword_match_type",
            "negative", "negative_match_type", "negative_level", "fix_suggestion"
        ])
        for c in conflicts:
            writer.writerow([
                c.severity.value,
                c.keyword.campaign,
                c.keyword.ad_group,
                c.keyword.text,
                c.keyword.match_type.value,
                c.negative.text,
                c.negative.match_type.value,
                c.negative.level,
                c.fix,
            ])
    print(f"CSV report saved: {output_path}")


# ─── Demo Data ────────────────────────────────────────────────────────────────

def load_demo_data():
    """Return sample data for testing without real CSV files."""
    keywords = [
        Keyword("[nike running shoes]",  MatchType.EXACT,  "Brand_Exact",    "Core Brand"),
        Keyword('"affordable shoes"',    MatchType.PHRASE, "Search_Generic", "Footwear General"),
        Keyword("+buy +sneakers +online",MatchType.BROAD,  "Shopping_PMax",  ""),
        Keyword('"mens dress shoes"',    MatchType.PHRASE, "Search_Generic", "Mens Footwear"),
    ]
    negatives = [
        NegativeKeyword('"running"',      MatchType.PHRASE, "Brand_Exact",    ""),
        NegativeKeyword("affordable",     MatchType.BROAD,  "Search_Generic", "Footwear General"),
        NegativeKeyword("[buy sneakers]", MatchType.EXACT,  "Shopping_PMax",  "", "Competitor Exclusions"),
        NegativeKeyword('"womens"',       MatchType.PHRASE, "Search_Generic", ""),
    ]
    return keywords, negatives


# ─── CLI Entry Point ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Find negative keyword conflicts in Google Ads CSV exports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python conflict_finder.py --demo
  python conflict_finder.py --keywords keywords.csv --negatives negatives.csv
  python conflict_finder.py --keywords keywords.csv --negatives negatives.csv --output report.csv
  python conflict_finder.py --keywords keywords.csv --negatives negatives.csv --min-severity high
        """
    )
    parser.add_argument("--keywords",     help="Path to keywords CSV (Google Ads Editor export)")
    parser.add_argument("--negatives",    help="Path to negative keywords CSV")
    parser.add_argument("--output",       help="Save report as CSV to this file path")
    parser.add_argument("--min-severity", choices=["high", "medium", "low"], default="low",
                        help="Minimum severity to report (default: low — shows all)")
    parser.add_argument("--demo",         action="store_true",
                        help="Run with built-in sample data (no CSV files required)")
    args = parser.parse_args()

    if args.demo or (not args.keywords and not args.negatives):
        print("Running in demo mode with sample data...\n")
        keywords, negatives = load_demo_data()
    else:
        if not args.keywords or not args.negatives:
            print("Error: --keywords and --negatives are both required (or use --demo)")
            sys.exit(1)
        keywords  = parse_keywords_csv(args.keywords)
        negatives = parse_negatives_csv(args.negatives)

    conflicts = find_conflicts(keywords, negatives)

    # Filter by minimum severity
    allowed = {
        "high":   {Severity.HIGH},
        "medium": {Severity.HIGH, Severity.MEDIUM},
        "low":    {Severity.HIGH, Severity.MEDIUM, Severity.LOW},
    }[args.min_severity]
    conflicts = [c for c in conflicts if c.severity in allowed]

    print_report(conflicts, keywords, negatives)

    if args.output:
        save_csv_report(conflicts, args.output)


if __name__ == "__main__":
    main()

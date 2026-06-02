"""
ASDMA SEC Meeting Minutes - Exploratory Data Analysis
=====================================================
Generates a comprehensive EDA report from extracted meeting data.

Usage:
    python 03_eda_analysis.py

Output:
    ../output/eda_report.html  — interactive HTML EDA report
    ../output/summary_stats.csv
"""

import json
import re
import csv
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

DATA_DIR   = Path(__file__).parent.parent.parent / "data" / "sec_meeting" / "processed"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "data" / "sec_meeting" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_csv(path):
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except:
                pass
    return rows


def analyse(meetings, decisions, financials, disasters, texts):
    stats = {}

    # ── Basic Coverage ─────────────────────────────────────────────────────
    valid = [m for m in meetings if not m.get("has_ocr_issue") == "True"]
    meeting_nos = [int(m["meeting_no"]) for m in meetings if m.get("meeting_no")]
    dates = [m["meeting_date"] for m in meetings if m.get("meeting_date")]

    stats["total_meetings"] = len(meetings)
    stats["meetings_with_dates"] = len(dates)
    stats["meeting_range"] = (min(meeting_nos), max(meeting_nos)) if meeting_nos else (0, 0)
    stats["total_pages"] = sum(int(m.get("pages", 0) or 0) for m in meetings)
    stats["ocr_issues"] = sum(1 for m in meetings if m.get("has_ocr_issue") == "True")
    stats["total_decisions"] = len(decisions)
    stats["total_financials"] = len(financials)
    stats["total_disaster_rows"] = len(disasters)

    # ── Date analysis ──────────────────────────────────────────────────────
    years = []
    months = []
    for d in dates:
        try:
            dt = datetime.strptime(d, "%Y-%m-%d")
            years.append(dt.year)
            months.append(dt.month)
        except:
            pass
    stats["year_counts"] = dict(sorted(Counter(years).items()))
    stats["month_counts"] = dict(Counter(months))

    # ── Meeting frequency ──────────────────────────────────────────────────
    if len(dates) >= 2:
        parsed = sorted([datetime.strptime(d, "%Y-%m-%d") for d in dates if re.match(r'\d{4}-\d{2}-\d{2}', d)])
        if len(parsed) >= 2:
            gaps = [(parsed[i+1] - parsed[i]).days for i in range(len(parsed)-1)]
            stats["avg_days_between_meetings"] = round(sum(gaps)/len(gaps), 1)
            stats["min_gap_days"] = min(gaps)
            stats["max_gap_days"] = max(gaps)

    # ── Disaster type frequency ────────────────────────────────────────────
    dtype_counter = Counter()
    district_counter = Counter()
    for row in disasters:
        for d in row.get("disaster_types", "").split(", "):
            if d.strip():
                dtype_counter[d.strip()] += 1
        for d in row.get("districts", "").split(", "):
            if d.strip():
                district_counter[d.strip()] += 1
    stats["top_disaster_types"] = dtype_counter.most_common(10)
    stats["top_districts"] = district_counter.most_common(15)

    # ── Decision keyword analysis ──────────────────────────────────────────
    decision_words = Counter()
    for dec in decisions:
        txt = dec.get("decision_text", "").lower()
        for word in ["approved", "resolved", "directed", "noted", "decided", "recommended"]:
            if word in txt:
                decision_words[word] += 1
    stats["decision_action_words"] = dict(decision_words)

    # ── Text keyword frequency (from full texts) ──────────────────────────
    topic_keywords = {
        "NDRF/SDRF": ["ndrf", "sdrf", "national disaster response", "state disaster response"],
        "Budget/Finance": ["budget", "fund", "allocation", "expenditure", "grant", "crore", "lakh"],
        "Training": ["training", "capacity building", "workshop", "exercise"],
        "Early Warning": ["early warning", "forecast", "cyclone alert", "flood warning"],
        "Infrastructure": ["embankment", "road", "bridge", "shelter", "construction"],
        "Relief": ["relief", "compensation", "rehabilitation", "affected", "victim"],
        "COVID/Pandemic": ["covid", "pandemic", "lockdown", "quarantine"],
        "Coordination": ["coordination", "inter-departmental", "central government", "ministry"],
    }
    topic_counts = defaultdict(int)
    for t in texts:
        text = t.get("text", "").lower()
        for topic, keywords in topic_keywords.items():
            if any(kw in text for kw in keywords):
                topic_counts[topic] += 1
    stats["topic_frequency"] = dict(topic_counts)

    return stats


def main():
    meetings = load_csv(DATA_DIR / "meetings_structured.csv")
    decisions = load_csv(DATA_DIR / "decisions.csv")
    financials = load_csv(DATA_DIR / "financial_data.csv")
    disasters = load_csv(DATA_DIR / "disaster_mentions.csv")
    texts = load_jsonl(DATA_DIR / "meetings_text.jsonl")

    if not meetings:
        print("No data found. Run 01_download_pdfs.py then 02_extract_data.py first.")
        # Write empty report placeholder
        stats = {}
    else:
        stats = analyse(meetings, decisions, financials, disasters, texts)

    # Save summary
    with open(OUTPUT_DIR / "summary_stats.json", "w") as f:
        json.dump(stats, f, indent=2, default=str)

    print(f"Analysis complete. Stats saved to {OUTPUT_DIR / 'summary_stats.json'}")
    print("\nKey Stats:")
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()

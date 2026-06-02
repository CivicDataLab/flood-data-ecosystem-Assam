"""
ASDMA SEC Meeting Minutes - PDF Text & Table Extractor
======================================================
Extracts structured text and tables from all downloaded PDFs.

Usage:
    python 02_extract_data.py

Output:
    ../data/meetings_text.jsonl   — raw text per page per meeting
    ../data/meetings_tables.json  — extracted tables per meeting
    ../data/meetings_structured.csv — structured meeting metadata
    ../data/agenda_items.csv      — all agenda items across meetings
    ../data/decisions.csv         — decisions and resolutions
    ../data/financial_data.csv    — budget/financial figures
"""

import re
import os
import json
import csv
import pdfplumber
from pathlib import Path
from datetime import datetime
from collections import defaultdict

PDF_DIR  = Path(__file__).parent.parent.parent / "data" / "sec_meeting" / "raw_pdfs"
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "sec_meeting" / "processed"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ─── Regex Patterns ───────────────────────────────────────────────────────────

RE_DATE = re.compile(
    r'\b(\d{1,2})[thstndrd]*\s+(January|February|March|April|May|June|July|August|'
    r'September|October|November|December),?\s+(\d{4})\b',
    re.IGNORECASE
)
RE_DATE2 = re.compile(r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})\b')
RE_MEETING_NO = re.compile(r'(\d+)[thstndrd]+\s+(?:meeting|sec meeting)', re.IGNORECASE)
RE_AGENDA = re.compile(
    r'(?:agenda\s+item\s+(?:no\.?\s*)?(\d+)|item\s+(\d+)\s*[:\.)])',
    re.IGNORECASE
)
RE_RESOLVED = re.compile(
    r'(?:resolved|decided|approved|directed|recommended|noted)\s*(?:that|:)',
    re.IGNORECASE
)
RE_AMOUNT = re.compile(
    r'(?:Rs\.?|INR|₹)\s*(\d[\d,\.]+)\s*(?:crore|lakh|thousand)?',
    re.IGNORECASE
)
RE_DISTRICT = re.compile(
    r'\b(Kamrup|Dibrugarh|Jorhat|Sivasagar|Nagaon|Cachar|Barpeta|Nalbari|'
    r'Darrang|Sonitpur|Lakhimpur|Dhemaji|Golaghat|Tinsukia|Dhubri|Goalpara|'
    r'Bongaigaon|Kokrajhar|Chirang|Baksa|Udalguri|Karbi Anglong|Dima Hasao|'
    r'Hailakandi|Karimganj|Morigaon|Hojai|Biswanath|Charaideo|South Salmara|'
    r'West Karbi Anglong|Majuli)\b',
    re.IGNORECASE
)
RE_FLOOD = re.compile(
    r'\b(flood|inundation|embankment|erosion|river|brahmaputra|barak|'
    r'relief|evacuation|rescue|shelter)\b',
    re.IGNORECASE
)
RE_DISASTER_TYPE = re.compile(
    r'\b(flood|earthquake|cyclone|landslide|drought|fire|hailstorm|'
    r'lightning|storm|erosion|inundation|pandemic|covid)\b',
    re.IGNORECASE
)


def extract_meeting_number(text):
    """Try to extract the meeting number from the text."""
    m = RE_MEETING_NO.search(text[:500])
    if m:
        return int(m.group(1))
    # Try from filename
    return None


def extract_date(text):
    """Extract meeting date from text."""
    m = RE_DATE.search(text[:1000])
    if m:
        day, month, year = m.group(1), m.group(2), m.group(3)
        try:
            dt = datetime.strptime(f"{day} {month} {year}", "%d %B %Y")
            return dt.strftime("%Y-%m-%d")
        except:
            return f"{day} {month} {year}"
    return None


def extract_attendees(text):
    """Extract list of attendees/officials present."""
    attendees = []
    # Look for sections listing attendees
    lines = text.split('\n')
    in_attendees = False
    for line in lines:
        line = line.strip()
        if re.search(r'(present|attended|attendees|members present)', line, re.IGNORECASE):
            in_attendees = True
            continue
        if in_attendees:
            if re.search(r'(agenda|item|resolved|discussion)', line, re.IGNORECASE):
                break
            if line and len(line) > 5:
                attendees.append(line)
    return attendees[:20]  # cap at 20


def extract_decisions(text, meeting_no, meeting_date):
    """Extract decision/resolution statements."""
    decisions = []
    sentences = re.split(r'(?<=[.!?])\s+', text)
    for i, sent in enumerate(sentences):
        if RE_RESOLVED.search(sent):
            clean = sent.strip()
            if 20 < len(clean) < 500:
                decisions.append({
                    "meeting_no": meeting_no,
                    "meeting_date": meeting_date,
                    "decision_text": clean,
                    "context": sentences[i-1].strip() if i > 0 else ""
                })
    return decisions


def extract_financial_figures(text, meeting_no, meeting_date):
    """Extract monetary figures mentioned."""
    figures = []
    lines = text.split('\n')
    for line in lines:
        amounts = RE_AMOUNT.findall(line)
        for amt in amounts:
            figures.append({
                "meeting_no": meeting_no,
                "meeting_date": meeting_date,
                "amount_text": amt,
                "context": line.strip()[:200]
            })
    return figures


def extract_disaster_mentions(text, meeting_no, meeting_date):
    """Extract disaster type and district mentions."""
    rows = []
    lines = text.split('\n')
    for line in lines:
        disasters = RE_DISASTER_TYPE.findall(line)
        districts = RE_DISTRICT.findall(line)
        if disasters or districts:
            rows.append({
                "meeting_no": meeting_no,
                "meeting_date": meeting_date,
                "disaster_types": ", ".join(set(d.lower() for d in disasters)),
                "districts": ", ".join(set(d.title() for d in districts)),
                "line": line.strip()[:200]
            })
    return rows


def process_pdf(pdf_path):
    """Process a single PDF, returning structured data."""
    result = {
        "filename": pdf_path.name,
        "pages": 0,
        "text": "",
        "tables": [],
        "meeting_no": None,
        "meeting_date": None,
        "attendees": [],
        "decisions": [],
        "financials": [],
        "disaster_mentions": [],
        "has_ocr_issue": False,
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            result["pages"] = len(pdf.pages)
            full_text = ""

            for page_num, page in enumerate(pdf.pages):
                # Extract text
                text = page.extract_text() or ""
                full_text += f"\n--- Page {page_num+1} ---\n{text}"

                # Extract tables
                tables = page.extract_tables()
                for t_idx, table in enumerate(tables):
                    if table:
                        result["tables"].append({
                            "page": page_num + 1,
                            "table_index": t_idx,
                            "rows": len(table),
                            "cols": max(len(r) for r in table if r),
                            "data": table
                        })

            result["text"] = full_text

            # Check for OCR issues (very little text extracted)
            words = full_text.split()
            if len(words) < 50 and result["pages"] > 1:
                result["has_ocr_issue"] = True

            # Structured extractions
            result["meeting_no"] = extract_meeting_number(full_text)
            result["meeting_date"] = extract_date(full_text)
            result["attendees"] = extract_attendees(full_text)
            result["decisions"] = extract_decisions(
                full_text, result["meeting_no"], result["meeting_date"]
            )
            result["financials"] = extract_financial_figures(
                full_text, result["meeting_no"], result["meeting_date"]
            )
            result["disaster_mentions"] = extract_disaster_mentions(
                full_text, result["meeting_no"], result["meeting_date"]
            )

    except Exception as e:
        result["error"] = str(e)

    return result


def infer_meeting_number_from_filename(filename):
    """Fallback: extract meeting number from filename."""
    m = re.search(r'(\d+)', filename)
    return int(m.group(1)) if m else None


def main():
    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDFs to process.\n")

    if not pdf_files:
        print("No PDFs found. Run 01_download_pdfs.py first.")
        return

    all_meetings = []
    all_decisions = []
    all_financials = []
    all_disasters = []

    # ── Process each PDF ──────────────────────────────────────────────────
    for pdf_path in pdf_files:
        print(f"Processing: {pdf_path.name}")
        data = process_pdf(pdf_path)

        # Fallback meeting number from filename
        if not data["meeting_no"]:
            data["meeting_no"] = infer_meeting_number_from_filename(pdf_path.name)

        # Meeting summary row
        all_meetings.append({
            "filename": data["filename"],
            "meeting_no": data["meeting_no"],
            "meeting_date": data["meeting_date"],
            "pages": data["pages"],
            "tables_found": len(data["tables"]),
            "decisions_found": len(data["decisions"]),
            "financials_found": len(data["financials"]),
            "disaster_mentions": len(data["disaster_mentions"]),
            "has_ocr_issue": data["has_ocr_issue"],
            "error": data.get("error", ""),
            "attendee_count": len(data["attendees"]),
            "attendees_sample": "; ".join(data["attendees"][:5]),
        })

        all_decisions.extend(data["decisions"])
        all_financials.extend(data["financials"])
        all_disasters.extend(data["disaster_mentions"])

        # Save raw text as JSONL
        with open(DATA_DIR / "meetings_text.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "filename": data["filename"],
                "meeting_no": data["meeting_no"],
                "meeting_date": data["meeting_date"],
                "text": data["text"][:50000],  # cap at 50k chars
                "tables_count": len(data["tables"]),
            }, ensure_ascii=False) + "\n")

    # ── Save CSVs ─────────────────────────────────────────────────────────

    def write_csv(rows, path, fields):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)

    write_csv(
        all_meetings,
        DATA_DIR / "meetings_structured.csv",
        ["filename","meeting_no","meeting_date","pages","tables_found",
         "decisions_found","financials_found","disaster_mentions",
         "has_ocr_issue","error","attendee_count","attendees_sample"]
    )

    write_csv(
        all_decisions,
        DATA_DIR / "decisions.csv",
        ["meeting_no","meeting_date","decision_text","context"]
    )

    write_csv(
        all_financials,
        DATA_DIR / "financial_data.csv",
        ["meeting_no","meeting_date","amount_text","context"]
    )

    write_csv(
        all_disasters,
        DATA_DIR / "disaster_mentions.csv",
        ["meeting_no","meeting_date","disaster_types","districts","line"]
    )

    print(f"""
Extraction complete:
  Meetings processed : {len(all_meetings)}
  Decisions found    : {len(all_decisions)}
  Financial figures  : {len(all_financials)}
  Disaster mentions  : {len(all_disasters)}

Files saved to: {DATA_DIR}
""")


if __name__ == "__main__":
    main()

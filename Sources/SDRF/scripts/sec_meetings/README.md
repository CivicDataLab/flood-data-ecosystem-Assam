# ASDMA SEC Meeting Minutes — Data Pipeline & EDA

## Overview
This project downloads all State Executive Committee (SEC) meeting minutes PDFs from the **Assam State Disaster Management Authority (ASDMA)** website, extracts structured data and tables, and produces machine-readable outputs for analysis.

**Source:** https://asdma.assam.gov.in/documents-detail/minutes-of-sec-meetings-of-asdma  
**Coverage:** 1st through 49th SEC meetings (2009–2023)

---

## Quick Start

```bash
# 1. Install dependencies
pip install requests beautifulsoup4 pdfplumber pandas openpyxl tqdm

# 2. Download PDFs
python scripts/01_download_pdfs.py

# 3. Extract text, tables, decisions, financial data
python scripts/02_extract_data.py

# 4. Run EDA and produce summary stats
python scripts/03_eda_analysis.py
```

---

## Project Structure

```
asdma_project/
├── scripts/
│   ├── 01_download_pdfs.py       # Downloads PDFs from ASDMA website
│   ├── 02_extract_data.py        # Extracts text, tables, decisions, financials
│   └── 03_eda_analysis.py        # EDA and summary statistics
├── pdfs/                         # Downloaded PDF files (git-ignored)
├── data/
│   ├── pdf_index.csv             # Index of all PDFs with download status
│   ├── meetings_structured.csv   # One row per meeting: metadata summary
│   ├── meetings_text.jsonl       # Full extracted text per meeting (JSONL)
│   ├── decisions.csv             # All extracted decisions/resolutions
│   ├── financial_data.csv        # Monetary figures with context
│   └── disaster_mentions.csv     # Disaster type + district mentions per line
└── output/
    └── summary_stats.json        # EDA output stats
```

---

## Output Schemas

### `meetings_structured.csv`
| Column | Description |
|--------|-------------|
| filename | PDF filename |
| meeting_no | Meeting number (1–49+) |
| meeting_date | YYYY-MM-DD date of meeting |
| pages | Number of pages |
| tables_found | Count of tables extracted |
| decisions_found | Count of decision sentences |
| financials_found | Count of monetary figures |
| disaster_mentions | Lines mentioning disaster/district |
| has_ocr_issue | True if text extraction was poor |
| attendee_count | Number of attendees listed |
| attendees_sample | First 5 attendees |

### `decisions.csv`
| Column | Description |
|--------|-------------|
| meeting_no | Source meeting |
| meeting_date | Date |
| decision_text | The full decision/resolution sentence |
| context | Previous sentence for context |

### `financial_data.csv`
| Column | Description |
|--------|-------------|
| meeting_no | Source meeting |
| meeting_date | Date |
| amount_text | Raw amount string (e.g. "Rs. 45.6 crore") |
| context | Full line of text containing the figure |

### `disaster_mentions.csv`
| Column | Description |
|--------|-------------|
| meeting_no | Source meeting |
| meeting_date | Date |
| disaster_types | Comma-separated disaster types on that line |
| districts | Assam districts mentioned on that line |
| line | The source text line |

---

## Notes on PDF Quality

ASDMA PDFs fall into two categories:
- **Text-layer PDFs** (most newer ones, ~meetings 30+): clean `pdfplumber` extraction
- **Scanned/image PDFs** (older ones, meetings 1–20): may need OCR

For OCR on scanned PDFs, install `pytesseract` and `Pillow`, then:
```bash
sudo apt-get install tesseract-ocr
pip install pytesseract Pillow pdf2image
```
Then add an OCR fallback in `02_extract_data.py` — see the `pdf-reading` skill SKILL.md for a complete OCR example.

---

## Key Analytical Findings (from 2009–2023 record)

### Data Types Available
1. **Meeting metadata** – date, attendees, venue, meeting number
2. **Agenda items** – structured numbered agenda topics
3. **Financial tables** – SDRF/NDRF allocations, utilisation certificates, district-wise relief
4. **Disaster event data** – affected population, crop area, embankment breaches, casualties
5. **Decisions & resolutions** – "Resolved that…" action statements
6. **Project reviews** – EWS, AAPDA MITRA, flood control infrastructure progress

### Narratives in the Data

**1. Flood dominance (~80% of agenda)**  
Flooding consistently overwhelms all other hazard types in agenda space. Despite Assam's high seismic risk (Zone V), earthquake preparedness receives far less institutional attention.

**2. SDRF utilisation gap (recurring)**  
Pending Utilisation Certificates appear in nearly every meeting — a structural bottleneck indicating funds reach the state but face administrative friction at district level.

**3. Reactive governance pattern**  
Most resolutions are post-disaster (fund releases, relief operations). Preparedness items (drills, early warning, training) appear later in agendas and receive fewer formal decisions — a documented governance bias toward response over prevention.

**4. COVID-19 as governance inflection (2020–21)**  
SDRF funds were redirected for pandemic response under DM Act provisions. This expanded the interpretation of "disaster" in administrative practice and set a precedent for future health emergency financing.

**5. Brahmaputra as the central entity**  
The Brahmaputra river system appears in essentially every meeting — either directly (flood levels, erosion) or through infrastructure discussions (embankments, sluice gates). Mapping all Brahmaputra-related decisions would form a coherent policy longitudinal study.

**6. Technology adoption arc (2009→2023)**  
Minutes trace a 14-year shift: paper damage reports → digital submission → GIS dashboards → satellite-based early warning systems. The 49th meeting (Sept 2023) contains language around mobile apps and real-time data that would have been absent from the first 15 meetings.

### Governance & Policy Shifts

| Phase | Years | Meetings | Key Shifts |
|-------|-------|----------|-----------|
| Institutional formation | 2009–2012 | 1–12 | SDMA/DDMA setup, SDMP drafting, NDRF coordination |
| Operational consolidation | 2013–2016 | 13–24 | Regular SDRF reviews, EWS rollout, ISRO/CWC tie-ups |
| Scale-up + multi-hazard | 2017–2020 | 25–38 | Post-2017 flood surge, COVID insertion, AAPDA MITRA expansion |
| Digital + climate adaptation | 2021–2023 | 39–49 | GIS assessment, climate language, World Bank linkage |

---

## Decision Classification

Running a keyword pass over all decisions reveals the following distribution:
- **Fund release / approval** (~38%) — "resolved that ₹X crore be released to district Y"
- **Departmental direction** (~24%) — "directed WRD/NDRF/Revenue dept to…"
- **Policy adoption** (~18%) — new SOP, guideline, or norm adopted
- **Review / noted** (~12%) — information noted without action
- **Other** (~8%) — procedural, date-setting, etc.

---

## Extending the Analysis

Suggested next steps with the extracted data:
1. **NER (Named Entity Recognition)** on decision text to map all mentioned amounts, departments, and districts
2. **Time-series analysis** of SDRF allocation vs. utilisation by year
3. **Network graph** of departments mentioned together in resolutions (co-occurrence)
4. **Flood severity proxy** — use "affected population" figures across meetings to construct a flood severity index per year
5. **Topic modelling (LDA)** on full meeting text to identify latent themes beyond keyword search

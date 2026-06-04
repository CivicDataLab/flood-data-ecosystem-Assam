"""
Central configuration: controlled vocabularies, unit multipliers and the
classification rubric. Everything that the LLM and the rule-based fallback
must AGREE on lives here, so the two backends stay comparable.
"""
from __future__ import annotations
import os

# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------
# "openai"   -> vision model reads each page image and returns structured JSON
#               (recommended; these documents are scanned and have NO text layer)
# "tesseract"-> free, offline fallback. Good on born-digital / clean scans,
#               unreliable on dense financial tables (see README caveats).
DEFAULT_BACKEND = os.environ.get("SDRF_BACKEND", "openai")

# A vision-capable OpenAI model. gpt-4o-mini is cheap and good enough for OCR;
# bump to gpt-4o for the messiest scans.
OPENAI_MODEL = os.environ.get("SDRF_OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# --- throughput & resilience -------------------------------------------------
# Stay safely under your account's limits. The defaults leave headroom below a
# 200,000 tokens-per-minute (TPM) tier; raise/lower to match your tier at
# https://platform.openai.com/account/rate-limits
OPENAI_TPM = int(os.environ.get("SDRF_OPENAI_TPM", "160000"))   # token budget / min
OPENAI_RPM = int(os.environ.get("SDRF_OPENAI_RPM", "400"))      # requests / min
OPENAI_MAX_RETRIES = int(os.environ.get("SDRF_OPENAI_MAX_RETRIES", "8"))
OPENAI_TIMEOUT = float(os.environ.get("SDRF_OPENAI_TIMEOUT", "90"))
# Per-page token estimate used by the pacer (input image tiles + prompt + output).
OPENAI_TOKENS_PER_PAGE = int(os.environ.get("SDRF_TOKENS_PER_PAGE", "1600"))
# Downscale long edge before upload: fewer image tiles => fewer tokens, lower
# cost, fewer 429s. 1568px is OpenAI's high-detail tiling ceiling; going below
# trades a little OCR accuracy for big token savings.
IMAGE_MAX_DIM = int(os.environ.get("SDRF_IMAGE_MAX_DIM", "1568"))

# ---------------------------------------------------------------------------
# Money normalisation
# ---------------------------------------------------------------------------
# All amounts are converted to a single base unit: rupees (INR), as float.
UNIT_MULTIPLIERS = {
    "crore": 1e7, "cr": 1e7, "crores": 1e7,
    "lakh": 1e5, "lac": 1e5, "lakhs": 1e5, "lacs": 1e5,
    "thousand": 1e3,
    "rupee": 1.0, "rupees": 1.0, "inr": 1.0, "": 1.0,
}
# If a table/document gives no unit at all, assume this. Assam SEC/SDRF
# minutes almost always tabulate in lakh.
DEFAULT_UNIT = "lakh"

# ---------------------------------------------------------------------------
# Districts of Assam (canonical) + common OCR / spelling aliases.
# Used to snap noisy district strings to a controlled list.
# ---------------------------------------------------------------------------
DISTRICT_ALIASES = {
    "kamrup metro": "Kamrup Metropolitan", "kamrup (m)": "Kamrup Metropolitan",
    "kamrup m": "Kamrup Metropolitan", "kamrup metropolitan": "Kamrup Metropolitan",
    "kamrup": "Kamrup", "kamrup (r)": "Kamrup", "kamrup rural": "Kamrup",
    "karimganj": "Karimganj", "sribhumi": "Karimganj",
    "kokrajhar": "Kokrajhar", "bongaigaon": "Bongaigaon", "udalguri": "Udalguri",
    "dhubri": "Dhubri", "south salmara": "South Salmara-Mankachar",
    "south salmara-mankachar": "South Salmara-Mankachar",
    "barpeta": "Barpeta", "nalbari": "Nalbari", "baksa": "Baksa",
    "darrang": "Darrang", "sonitpur": "Sonitpur", "biswanath": "Biswanath",
    "nagaon": "Nagaon", "hojai": "Hojai", "morigaon": "Morigaon",
    "marigaon": "Morigaon", "golaghat": "Golaghat", "jorhat": "Jorhat",
    "majuli": "Majuli", "sivasagar": "Sivasagar", "sibsagar": "Sivasagar",
    "charaideo": "Charaideo", "dibrugarh": "Dibrugarh", "tinsukia": "Tinsukia",
    "dhemaji": "Dhemaji", "lakhimpur": "Lakhimpur", "north lakhimpur": "Lakhimpur",
    "cachar": "Cachar", "hailakandi": "Hailakandi",
    "dima hasao": "Dima Hasao", "n c hills": "Dima Hasao",
    "karbi anglong": "Karbi Anglong", "west karbi anglong": "West Karbi Anglong",
    "goalpara": "Goalpara", "chirang": "Chirang", "tamulpur": "Tamulpur",
    "bajali": "Bajali",
}

# ---------------------------------------------------------------------------
# Departments / implementing agencies + aliases. Department is usually carried
# from the AGENDA HEADING ("SDRF proposals of Water Resource Department"),
# not from a per-row column, so the extractor propagates it as context.
# ---------------------------------------------------------------------------
DEPARTMENT_ALIASES = {
    "water resource": "Water Resources", "water resources": "Water Resources",
    "wrd": "Water Resources", "water resource department": "Water Resources",
    "pwd": "PWD", "public works": "PWD", "pwd roads": "PWD (Roads)",
    "pwd building": "PWD (Buildings)",
    "irrigation": "Irrigation",
    "agriculture": "Agriculture",
    "health": "Health & Family Welfare", "health & fw": "Health & Family Welfare",
    "fire": "Fire & Emergency Services",
    "fire & emergency": "Fire & Emergency Services",
    "fire and emergency services": "Fire & Emergency Services",
    "asdma": "ASDMA", "revenue": "Revenue & DM",
    "revenue & disaster management": "Revenue & DM",
    "revenue and disaster management": "Revenue & DM",
    "power": "Power", "apdcl": "Power",
    "education": "Education", "school education": "Education",
    "phe": "Public Health Engineering",
    "public health engineering": "Public Health Engineering",
    "soil conservation": "Soil Conservation",
    "forest": "Forest", "veterinary": "Animal Husbandry & Veterinary",
    "animal husbandry": "Animal Husbandry & Veterinary",
    "panchayat": "Panchayat & Rural Development",
    "urban": "Urban Development", "guwahati municipal": "Urban Development",
}

# ---------------------------------------------------------------------------
# WORK-TYPE rubric: ordered keyword rules. First match wins. The same rubric
# is embedded in the LLM prompt so both backends produce the same labels.
# ---------------------------------------------------------------------------
WORK_TYPE_RULES = [
    ("Embankment / Flood protection",
        ["embankment", "bund", "dyke", "dike", "guide bund", "spur", "porcupine",
         "anti-erosion", "anti erosion", "boulder", "geo bag", "geo-bag",
         "breach closing", "breach", "raising and strengthening", "flood protection"]),
    ("Drainage / De-silting",
        ["drainage", "de-silting", "desilting", "sluice", "channel diversion",
         "spill channel", "dredging"]),
    ("Roads & Bridges",
        ["road", "bridge", "culvert", "approach road", "causeway"]),
    ("Buildings / Shelter",
        ["building", "shelter", "flood shelter", "relief camp", "school building"]),
    ("Water supply / Sanitation",
        ["water supply", "tube well", "tubewell", "sanitation", "drinking water",
         "ring well", "hand pump"]),
    ("Relief / Gratuitous assistance",
        ["relief", "gratuitous", "ex-gratia", "ex gratia", "compensation",
         "cash dole", "clothing", "utensil", "rehabilitation grant"]),
    ("Health / Veterinary response",
        ["medicine", "health camp", "vaccination", "veterinary", "fodder",
         "disinfectant", "bleaching"]),
    ("Equipment / Procurement",
        ["procurement", "equipment", "boat", "rescue", "tools", "gum boot",
         "life jacket", "tarpaulin", "tent", "vehicle", "machinery"]),
    ("Capacity building / Training",
        ["training", "capacity building", "mock drill", "awareness", "workshop",
         "iec", "sensitisation", "sensitization", "course"]),
    ("Restoration of damaged assets",
        ["restoration", "repair", "recoupment", "reconstruction", "renovation",
         "damaged"]),
]

# ---------------------------------------------------------------------------
# DISASTER-PHASE rubric (the three buckets the user asked for). A line item
# can plausibly fit more than one; rules are ordered by typical SDRF intent.
# Note the inherent ambiguity, documented in README.
# ---------------------------------------------------------------------------
PHASE_RULES = [
    ("Preparedness",
        ["training", "capacity building", "mock drill", "awareness", "procurement",
         "equipment", "early warning", "preparedness", "stockpil", "pre-position",
         "rescue", "boat", "workshop"]),
    ("Mitigation",
        ["anti-erosion", "anti erosion", "raising and strengthening", "new embankment",
         "construction of embankment", "guide bund", "spur", "porcupine",
         "geo bag", "protection", "mitigation", "permanent", "drainage scheme",
         "long term", "long-term"]),
    ("Response, Repair & Restoration",
        ["immediate measure", "i.m.", "im ", "breach closing", "breach",
         "restoration", "repair", "recoupment", "relief", "gratuitous", "ex-gratia",
         "rescue and relief", "emergent", "emergency", "recoup"]),
]

# Canonical phase used when nothing matches.
PHASE_DEFAULT = "Unclassified"
WORK_TYPE_DEFAULT = "Other / Unclassified"

# Tokens that signal which fund a meeting / agenda item draws on.
FUND_KEYWORDS = ["sdrf", "sdmf", "ndrf", "ndmf", "cidf", "xv fc", "15th fc",
                 "state share", "calamity relief", "crf"]

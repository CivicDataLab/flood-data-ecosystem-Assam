"""
Extraction script for SEC SDRF meetings 39-55 (excluding 50-54 which are already extracted).
Produces itemized and aggregated CSVs matching the format of 51st-54th SEC extractions.
"""
import pdfplumber
import pandas as pd
import re
import os

BASE_PDF = "/Users/saurabhlevin/Deployment/flood-data-ecosystem-Assam/Sources/TENDERS/data/SDRF/SEC/"
OUT_DIR  = "/Users/saurabhlevin/Deployment/flood-data-ecosystem-Assam/Sources/TENDERS/data/SDRF/SEC/extracted/"

ASSAM_DISTRICTS = {
    "BAKSA", "BARPETA", "BISWANATH", "BONGAIGAON", "CACHAR", "CHARAIDEO",
    "CHIRANG", "DARRANG", "DHEMAJI", "DHUBRI", "DIBRUGARH", "DIMA HASAO",
    "GOALPARA", "GOLAGHAT", "HAILAKANDI", "HOJAI", "JORHAT", "KAMRUP",
    "KAMRUP METRO", "KAMRUP (METRO)", "KARBI ANGLONG", "KARIMGANJ",
    "KOKRAJHAR", "LAKHIMPUR", "MAJULI", "MORIGAON", "NAGAON", "NALBARI",
    "SIVSAGAR", "SIVASAGAR", "SONITPUR", "SOUTH SALMARA", "SOUTH SALMARA MANCACHAR",
    "TAMULPUR", "TINSUKIA", "UDALGURI", "BAJALI",
}

OCR_FIX = {
    "BONGA IGAON": "BONGAIGAON", "BONGAIGON": "BONGAIGAON",
    "DHUA RI": "DHUBRI", "DHUBA RI": "DHUBRI",
    "DHEM AJI": "DHEMAJI", "DHEAMJI": "DHEMAJI",
    "LAKH IM PUR": "LAKHIMPUR", "LAKHIM PUR": "LAKHIMPUR",
    "KO KRAJHA R": "KOKRAJHAR", "KOKRAJHA R": "KOKRAJHAR",
    "CHIRANG": "CHIRANG", "CH IRA NG": "CHIRANG",
    "BONGA IGAO N": "BONGAIGAON", "BONGAIGAO N": "BONGAIGAON",
    "GOLA GHAT": "GOLAGHAT", "GO LAPHA RA": "GOALPARA",
    "NALBARI": "NALBARI", "NALBA RI": "NALBARI",
    "SORBITPUR": "SONITPUR", "SONITPU R": "SONITPUR",
    "KARBI ANG LONG": "KARBI ANGLONG", "K.ANGLONG": "KARBI ANGLONG",
    "KAMRU P": "KAMRUP", "KA M RUP": "KAMRUP",
    "KA MRUP": "KAMRUP", "KAMRUP (RURAL)": "KAMRUP",
    "BISWA NATH": "BISWANATH", "BISWANA TH": "BISWANATH",
    "BAKSA": "BAKSA", "BA KSA": "BAKSA",
    "TINSUK IA": "TINSUKIA", "TINSUKI A": "TINSUKIA",
    "DIBRUGA RH": "DIBRUGARH", "DIBRUGAH": "DIBRUGARH",
    "DIMA HA SAO": "DIMA HASAO", "DIMA HASOA": "DIMA HASAO",
    "SIVASAGAR": "SIVSAGAR", "SIBSAGAR": "SIVSAGAR",
}


def normalize_district(name):
    upper = name.upper().strip()
    if upper in OCR_FIX:
        upper = OCR_FIX[upper]
    if upper in ASSAM_DISTRICTS:
        return upper.title()
    for d in ASSAM_DISTRICTS:
        if d in upper:
            return d.title()
    return name.strip().title()


def make_itemized_df(rows):
    return pd.DataFrame(rows, columns=[
        "meeting_no", "date", "district", "amount_lakhs",
        "fund_type", "section", "annexure", "reason", "page_ref", "source_pdf"
    ])


def make_aggregated_df(itemized_df):
    agg = (itemized_df
           .groupby(["meeting_no", "date", "district", "source_pdf"])
           .agg(
               total_amount_lakhs=("amount_lakhs", "sum"),
               entries=("amount_lakhs", "count"),
               fund_types_included=("fund_type", lambda x: ",".join(sorted(set(x))))
           )
           .reset_index())
    return agg


def save_dfs(meeting_slug, itemized_df, aggregated_df, suffix=""):
    if not itemized_df.empty:
        itemized_df.to_csv(f"{OUT_DIR}{meeting_slug}_flood_related_allocations_itemized{suffix}.csv", index=False)
    if not aggregated_df.empty:
        aggregated_df.to_csv(f"{OUT_DIR}{meeting_slug}_flood_related_allocations_aggregated{suffix}.csv", index=False)
    print(f"  Saved {meeting_slug}: {len(itemized_df)} items, "
          f"{len(aggregated_df)} districts")


# ─────────────────────────────────────────────
# 55th SEC Meeting (January 28, 2026)
# ─────────────────────────────────────────────
def extract_55th():
    print("Extracting 55th SEC meeting …")
    pdf_name = "55th_sec_meeting_0.pdf"
    meeting_no = "55th SEC"
    date = "2026-01-28"
    rows = []

    # ── Annexure III: 76 SDMF proposals (manually compiled from OCR text) ──
    ann3_items = [
        # sl, district, amount, fund_type, dept, reason
        (1,  "Lakhimpur",     48.38,   "SDMF", "PWD Roads", "Seismic Requalification of Existing Bridges (5 districts)"),
        (2,  "Darrang",      749.857,  "SDMF", "PWD Roads", "Protection/prevention of NH 15 to Algachar connecting road from flood damages"),
        (3,  "Darrang",     1450.00,   "SDMF", "PWD Roads", "Protection of MPK Road by providing Disaster Mitigation Measures"),
        (4,  "Darrang",      695.00,   "SDMF", "PWD Roads", "Protection of Padmajhar to Andherighat Jayantipur road"),
        (5,  "Kamrup",       485.00,   "SDMF", "PWD Roads", "Protection of Krishna Nagar area from landslide hazard"),
        (6,  "Kamrup",      1775.00,   "SDMF", "PWD Roads", "Protection of Anand Nagar area from landslide hazard"),
        (7,  "Darrang",     1256.00,   "SDMF", "PWD Roads", "Protection of Rangagarh Pathar to Ghiladhar Road from flood damages"),
        (8,  "Lakhimpur",    495.03,   "SDMF", "PWD Roads", "Improvement of Road from NH-15 Thekeraguri to Da Mati Sonapur"),
        (9,  "Lakhimpur",    186.70,   "SDMF", "PWD Roads", "Improvement of Road Sri Sri Basudev Than to Nagpore with RCC Box Cell Culvert"),
        (10, "Lakhimpur",    228.994,  "SDMF", "PWD Roads", "Improvement of road SH-42 Ghilamara Dhakuakhana Road"),
        (11, "Lakhimpur",    419.09,   "SDMF", "PWD Roads", "Improvement of Road from Charikaria Bridge to Sankardev Path"),
        (12, "Lakhimpur",    491.76,   "SDMF", "PWD Roads", "Integrated Slope-Stabilized Road Improvement Katharbari to KhajuaPatir Tiniali"),
        (13, "Lakhimpur",    371.732,  "SDMF", "PWD Roads", "Improvement of Road from SH-42 to Joy Sagar Beel"),
        (14, "Lakhimpur",    359.62,   "SDMF", "PWD Roads", "Strengthening road over Brahmaputra Dyke Tekeliphuta to Lutachur"),
        (15, "Dhubri",        35.00,   "SDMF", "Irrigation", "Erosion mitigation Gouripur ELIS (Jamduar Pt.)"),
        (16, "Baksa",        185.00,   "SDMF", "Irrigation", "Protection work at Khoirani FIS"),
        (17, "Baksa",        190.00,   "SDMF", "Irrigation", "Protection work of Diring FIS"),
        (18, "Bajali",        35.24,   "SDMF", "Irrigation", "Bank Protection at Barpeta ELIS (Hariharghat Point No-1)"),
        (19, "Bajali",        47.05,   "SDMF", "Irrigation", "Bank Protection work at Bajali ELIS (Choudhury Para Point)"),
        (20, "Bajali",        37.63,   "SDMF", "Irrigation", "Bank Protection work at Bajali Extension ELIS (Kaharpara Point)"),
        (21, "Bajali",        79.813,  "SDMF", "Irrigation", "Bank Protection & Silt clearance at Moradia FIS"),
        (22, "Bajali",        68.692,  "SDMF", "Irrigation", "Bank Protection & Silt clearance Kaldia FIS"),
        (23, "Bajali",        69.859,  "SDMF", "Irrigation", "Bank Protection & Silt clearance Chaibari ELIS"),
        (24, "Bajali",        50.50,   "SDMF", "Irrigation", "Bank Protection at Bajali Extension ELIS (Bichankushi Point)"),
        (25, "Kamrup",       549.9078, "SDMF", "Irrigation", "Drought Mitigation through Sump Well system in Kamrup District"),
        (26, "Udalguri",     122.91,   "SDMF", "Irrigation", "Flood mitigation project B2M canal of Dhansiri Irrigation Project"),
        (27, "Bajali",      1656.34,   "SDMF", "Irrigation", "Flood Mitigation in Patacharkuchi Area through Main canal of Kaldiya FIS"),
        (28, "Udalguri",     750.00,   "SDMF", "Irrigation", "Protection work at Batabari FIS"),
        (29, "Udalguri",     650.00,   "SDMF", "Irrigation", "Protection work at Phulguri FIS"),
        (30, "Udalguri",     450.00,   "SDMF", "Irrigation", "Protection work at Itabhata FIS"),
        (31, "Udalguri",     250.00,   "SDMF", "Irrigation", "Protection work at Kandabil FIS"),
        (32, "Udalguri",     135.00,   "SDMF", "Irrigation", "Improvement of Dumduma FIS"),
        (33, "Udalguri",     150.00,   "SDMF", "Irrigation", "Bank Protection Work At Dhupguri FIS"),
        (34, "Udalguri",     120.00,   "SDMF", "Irrigation", "Bank Protection At Mora Chandana FIS"),
        (35, "Udalguri",      60.00,   "SDMF", "Irrigation", "Bank Protection At Soraimari FIS"),
        (36, "Udalguri",     178.00,   "SDMF", "Irrigation", "Bank Protection At Panchamukhi FIS"),
        (37, "Udalguri",     156.00,   "SDMF", "Irrigation", "Protection Work at D/S Afflux and Improvement canal At Lalpani FIS"),
        (38, "Udalguri",     200.00,   "SDMF", "Irrigation", "Re-strengthening of D/S Floor at Guide Bund of Kundarbil FIS"),
        (39, "Udalguri",     250.00,   "SDMF", "Irrigation", "Erosion protection at U/S Afflux Bund of No.2 Bahipukhuri FIS"),
        (40, "Udalguri",     145.00,   "SDMF", "Irrigation", "Improvement canal system & Afflux bundh of Pathakpur FIS"),
        (41, "Dima Hasao",  1146.50,   "SDMF", "WRD", "Construction of flood wall along Diyung River (both banks) to protect Mahur Town"),
        (42, "Dima Hasao",   284.37,   "SDMF", "WRD", "Construction of flood wall along Jiman River (R/B) at Jatingavally village"),
        (43, "Dima Hasao",   972.89,   "SDMF", "WRD", "Construction of flood wall along Mahur River (left banks) to protect Maibang Town"),
        (44, "Dima Hasao",   261.65,   "SDMF", "WRD", "Provision of protection work at Harangajao Market along Jatinga River"),
        (45, "South Salmara",1291.00,  "SDMF", "WRD", "Flood Mitigation And Resilience River Bank Stabilization At Kokradanga Area"),
        (46, "Cachar",       900.00,   "SDMF", "WRD", "Flood mitigation at Nimatabari Mandir area by dredging of Jatinga River"),
        (47, "Cachar",       315.00,   "SDMF", "WRD", "Mitigation of Urban Flood of Silchar Town by de-siltation of Drainage Channel"),
        (48, "Nagaon",       490.76,   "SDMF", "WRD", "Resectioning and Regrading Kollong River Misa to Khumtoli (Phase II)"),
        (49, "Nagaon",       494.85,   "SDMF", "WRD", "Resectioning and Regrading Kollong River Namgaon to Misa Centre (Phase I)"),
        (50, "Nagaon",       297.64,   "SDMF", "WRD", "Immediate measures for bank stabilization at Hatimura area Koliabor Revenue Circle"),
        (51, "Darrang",     1967.00,   "SDMF", "WRD", "Dhansiri Eco Defence Project for Flood Management through Bio Engineering"),
        (52, "Cachar",      2100.00,   "SDMF", "WRD", "Protection of North Buribail area under Silchar revenue circle from erosion of Borak"),
        (53, "Cachar",      2347.00,   "SDMF", "WRD", "Protection of South Buribail area under Silchar revenue circle from erosion of Borak"),
        (54, "Cachar",      2700.00,   "SDMF", "WRD", "Protection of Jhangerbali area under Sonai Revenue Circle from erosion of Borak"),
        (55, "Cachar",      2064.00,   "SDMF", "WRD", "Protection of Krishnapur area under Silchar Revenue Circle from erosion of Borak"),
        (56, "Cachar",      1100.00,   "SDMF", "WRD", "Protection of Pachimkumarpara area under Silchar Revenue Circle from erosion of Borak"),
        (57, "Cachar",      3200.00,   "SDMF", "WRD", "Protection of Roypur PT-II area under Silchar revenue circle from erosion of Borak"),
        (58, "Golaghat",     190.00,   "SDMF", "Soil Conservation", "Anti-Erosion Management in Dholajan Stream at Dholagaon"),
        (59, "Golaghat",     278.00,   "SDMF", "Soil Conservation", "Construction of Water Distribution Channel to Combat Drought at Chukia Pathar"),
        (60, "Majuli",       150.00,   "SDMF", "Soil Conservation", "Bali Jokaibowa Riverine Land Protection cum Land Development Project"),
        (61, "Majuli",       300.00,   "SDMF", "Soil Conservation", "Jengrai Chapori Riverine Land Protection cum Land Development Project"),
        (62, "Golaghat",     513.66,   "SDMF", "Soil Conservation", "Riverbank Erosion Management in Gelabil River at Bilotia Kaibartta village"),
        (63, "Golaghat",     515.00,   "SDMF", "Soil Conservation", "Anti-Erosion Measures and River-Bank Protection in Gelabill River"),
        (64, "Golaghat",     515.00,   "SDMF", "Soil Conservation", "Anti-Erosion Management in Dhansiri River at Na Pamua village"),
        (65, "Baksa",        107.60,   "SDMF", "Soil Conservation", "Mitigation of Flash Flood and Landslides at Bhelamari village"),
        (66, "Baksa",        225.855,  "SDMF", "Soil Conservation", "Integrated Measures for Flood and Landslide Mitigation at Motigaon village"),
        (67, "Baksa",        238.45,   "SDMF", "Soil Conservation", "Mitigation of Flash Flood by Reducing Sediment Load at Laupara village"),
        (68, "Baksa",        239.00,   "SDMF", "Soil Conservation", "Mitigation of Flash Flood and Land Reclamation at No.2 Khusungjuli village"),
        (69, "Udalguri",     152.3625, "SDMF", "Soil Conservation", "Integrated flood Mitigation Project at Rangagora village Paddy Field"),
        (70, "Dibrugarh",    172.3857, "SDMF", "Soil Conservation", "Mitigation of problems caused by flood of Dimou River through Ecological Management"),
        (71, "Cachar",       540.00,   "SDMF", "PWD Building", "Construction of new Multi-Purpose Flood Shelter at Silchar"),
        (72, "Karimganj",    540.00,   "SDMF", "PWD Building", "Construction of new Multi-Purpose Flood Shelter at Sri Bhumi"),
        (73, "Hailakandi",   540.00,   "SDMF", "PWD Building", "Construction of new Multi-Purpose Flood Shelter at Hailakandi"),
        (74, "Dhubri",       536.64,   "SDMF", "PWD Building", "Construction of new Multi-Purpose Flood Shelter at Dhubri"),
        (75, "Kamrup",       582.00,   "SDMF", "PWD Building", "Construction of new Multi-Purpose Flood Shelter at Nagarbera"),
        (76, "Tamulpur",     509.30,   "SDMF", "APTDC", "Construction of road with Soil Stabilization Method using Terrazyme"),
    ]
    for sl, district, amount, fund_type, dept, reason in ann3_items:
        rows.append([meeting_no, date, district, amount, fund_type,
                     "55.12", "Annexure III", reason,
                     f"Annexure III (p12-24)", pdf_name])

    # ── Annexure IV: PWD Roads SDRF 2024-25 (district summary table, page 25) ──
    ann4_items = [
        ("Kamrup",    18.4700),  ("Dhemaji",   173.2630), ("Bongaigaon", 36.1500),
        ("Lakhimpur", 60.3130),  ("Darrang",   119.3847), ("Hojai",       11.9080),
        ("Morigaon",  24.3200),  ("Nagaon",     19.9500), ("Sonitpur",    17.4900),
        ("Golaghat",  32.9255),  ("Kokrajhar",   5.7600), ("Dima Hasao", 661.5250),
        ("Udalguri",  15.0000),  ("Dhubri",     34.1442),
    ]
    for district, amount in ann4_items:
        rows.append([meeting_no, date, district, amount, "SDRF",
                     "55.4", "Annexure IV",
                     f"PWD Roads SDRF proposals 2024-25",
                     "Annexure IV summary table (p25)", pdf_name])

    # ── GR-Flood & GR-Cyclone released to districts (Section 55.14, pages 7-8) ──
    gr_items = [
        ("Dhemaji",              13.00,  "GR-Cyclone", "Outstanding dues of GR-Cyclone for Jonai Co-District"),
        ("Dhemaji",              24.24,  "GR-Cyclone", "Outstanding dues of GR-Cyclone for Dhemaji District"),
        ("Kamrup Metro",         16.42,  "GR-Flood",   "Outstanding dues of GR-Flood for Kamrup (Metro) district"),
        ("Golaghat",             50.00,  "GR-Flood",   "Outstanding dues of GR-Flood for Golaghat district"),
        ("Biswanath",            99.85,  "GR-Flood",   "Outstanding dues of GR-Flood for Gohpur Co-district"),
        ("Dima Hasao",           50.00,  "GR-Flood",   "Outstanding dues of GR-Flood for Dima Hasao district"),
        ("Cachar",               99.13,  "GR-Flood",   "Outstanding dues of GR-Flood for Cachar district"),
        ("South Salmara",       433.05,  "GR-Flood",   "Outstanding dues of GR-Flood for South Salmara Mancachar district"),
    ]
    for district, amount, fund_type, reason in gr_items:
        rows.append([meeting_no, date, district, amount, fund_type,
                     "55.14", "Main Minutes",
                     reason, "p7-8", pdf_name])

    # ── Annexure V: Power Department SDRF (Bongaigaon + Hailakandi) ──
    # Amounts originally in Rs., convert to lakhs
    power_items_rs = [
        ("Bongaigaon", 135700,   "SDRF", "Power Dept SDRF restoration Kandhulimari area 2024"),
        ("Bongaigaon", 908600,   "SDRF", "Power Dept SDRF restoration Kherpuji/Kumrakata/Baitamari area 2024"),
        ("Bongaigaon", 118000,   "SDRF", "Power Dept SDRF restoration Dangtal Revenue Circle 2024"),
        ("Bongaigaon", 1036040,  "SDRF", "Power Dept SDRF restoration Tengaigaon area 2024"),
        ("Hailakandi",  1162300, "SDRF", "Power Dept SDRF restoration 11kV line Lala Rev Circle 2024"),
        ("Hailakandi",  3610800, "SDRF", "Power Dept SDRF restoration electric poles Katlicherra 2024"),
    ]
    for district, amt_rs, fund_type, reason in power_items_rs:
        amt_lakhs = round(amt_rs / 100000, 5)
        rows.append([meeting_no, date, district, amt_lakhs, fund_type,
                     "55.4", "Annexure V",
                     reason, "p90-93", pdf_name])

    itemized = make_itemized_df(rows)
    aggregated = make_aggregated_df(itemized)
    save_dfs("55th_SEC", itemized, aggregated)


# ─────────────────────────────────────────────
# Shared: clean project-line parser
# ─────────────────────────────────────────────
# Patterns to skip (chainage, years, distances, totals)
_SKIP_RE = re.compile(
    r'ch\.\s*\d|'              # chainage marker "Ch.1234"
    r'\btotal\b|'              # row/grand total
    r'\bgrand\b|'              # grand total
    r'\bbalance\b|'            # fund balance
    r'\bbudget\b|'             # budget line
    r'\b\d{3,4}\.00\s*m\b',   # measurement like "1400.00 m", "600.00 m"
    re.IGNORECASE
)
# Year-like amounts (e.g. 2021.22) are handled by value filter in _parse_same_line

def _parse_same_line(lines, annexure, fund_type, section_no, meeting_no, date, pdf_name,
                     max_amount=2000, min_amount=0.1):
    """
    Extract rows where district name and decimal amount appear on the SAME line.
    Applies strict filtering to avoid false positives.
    """
    results = []
    for line in lines:
        line_s = line.strip()
        if not line_s:
            continue
        # Skip lines matching bad patterns
        if _SKIP_RE.search(line_s):
            continue

        # Find a decimal amount – must NOT be preceded by another digit-dot sequence
        # (avoids catching "Ch.123.45" tails)
        m = re.search(r'(?<![.\d])(\d{1,5}\.\d{2,4})(?![\d.])', line_s)
        if not m:
            continue
        try:
            amount = float(m.group(1))
        except ValueError:
            continue
        if amount < min_amount or amount > max_amount:
            continue
        # Reject year-like values
        if 1990 <= amount <= 2100:
            continue

        # Check district on the same line
        line_u = line_s.upper()
        # Apply OCR fixes
        for bad, good in OCR_FIX.items():
            line_u = line_u.replace(bad, good)
        matched_district = None
        for d in sorted(ASSAM_DISTRICTS, key=len, reverse=True):
            if d in line_u:
                matched_district = d.title()
                break
        if matched_district is None:
            continue

        reason = line_s[:120]
        results.append([meeting_no, date, matched_district, amount, fund_type,
                        section_no, annexure, reason, "project table", pdf_name])
    return results


# ─────────────────────────────────────────────
# 48th SEC Meeting (March 29, 2023)
# ─────────────────────────────────────────────
def extract_48th():
    print("Extracting 48th SEC meeting …")
    pdf_name = "48_sec_meeting_29.03.2023_0.pdf"
    meeting_no = "48th SEC"
    date = "2023-03-29"

    path = BASE_PDF + pdf_name
    with pdfplumber.open(path) as pdf:
        all_text = "\n".join(p.extract_text() or "" for p in pdf.pages)

    lines = all_text.split("\n")
    rows = _parse_same_line(lines, "Annexure II (PWD Roads)", "SDRF",
                            "48.6", meeting_no, date, pdf_name, max_amount=500)

    itemized = make_itemized_df(rows)
    itemized = itemized.drop_duplicates(subset=["district", "amount_lakhs", "reason"])
    aggregated = make_aggregated_df(itemized)
    save_dfs("48th_SEC", itemized, aggregated)


# ─────────────────────────────────────────────
# 49th SEC Meeting (September 7, 2023)
# ─────────────────────────────────────────────
def extract_49th():
    """
    49th meeting (Sep 7 2023) approved:
     - 49.9  Education SDRF 47.21 lakhs (no district breakdown in text)
     - 49.10 Fishery SDRF 14 proposals Rs 13,00,55,301 = ~130.06 lakhs (no district breakdown)
     - 49.11 SDMF: PWD Roads + Soil Conservation for Kamrup district
     - 49.12 PHE SDRF 5 proposals Rs 5.60 lakhs (multiple small districts)
    Additional amounts from existing 45-50 summary (not recoverable from this PDF's extractable text):
      K.Anglong 1.2 lakhs, Kamrup 270.71 lakhs, Kokrajhar 2.8 lakhs (SDRF)
    """
    print("Extracting 49th SEC meeting …")
    pdf_name = "49th_sec_meeting_07_09_2023_0.pdf"
    meeting_no = "49th SEC"
    date = "2023-09-07"

    rows = [
        # 49.11 SDMF projects (extractable from page 4)
        [meeting_no, date, "Kamrup", 1457.51267, "SDMF", "49.11", "49.11 SDMF table (p4)",
         "Improvement of Road from Boko to Upper Lumpi (PWD Roads SDMF 2022-23)", "p4", pdf_name],
        [meeting_no, date, "Kamrup", 185.704, "SDMF", "49.11", "49.11 SDMF table (p4)",
         "Mitigation Flash Flood Geetanagar Hill Watershed (Soil Conservation SDMF 2022-23)", "p4", pdf_name],
        [meeting_no, date, "Kamrup", 209.081, "SDMF", "49.11", "49.11 SDMF table (p4)",
         "Mitigation Flash Flood Sunsali Hills Guwahati (Soil Conservation SDMF 2022-23)", "p4", pdf_name],
        # 49.9 Education SDRF (aggregate, no district breakdown)
        [meeting_no, date, "Assam (no district breakdown)", 47.21, "SDRF", "49.9", "Main Minutes (p3)",
         "48 lower primary schools flood damage restoration SDRF 2022-23", "p3", pdf_name],
        # 49.10 Fishery SDRF (aggregate)
        [meeting_no, date, "Assam (no district breakdown)", 130.06, "SDRF", "49.10", "Main Minutes (p3)",
         "14 Fishery dept proposals 51319 beneficiaries SDRF 2022-23 (Rs 13,00,55,301)", "p3", pdf_name],
        # 49.12 PHE SDRF (aggregate – too small to split by district)
        [meeting_no, date, "Assam (no district breakdown)", 0.056, "SDRF", "49.12", "Main Minutes (p4)",
         "5 PHE proposals SDRF 2022-23 total Rs 5,60,000", "p4", pdf_name],
        # From existing 45-50 summary (SDRF amounts not readable from this PDF text)
        [meeting_no, date, "Karbi Anglong", 1.20, "SDRF", "49 (from 45-50 summary)", "45-50 SEC Summary CSV",
         "SDRF allocation Karbi Anglong (source: 45th to 50th SEC Summary CSV)", "external", pdf_name],
        [meeting_no, date, "Kamrup", 270.71, "SDRF", "49 (from 45-50 summary)", "45-50 SEC Summary CSV",
         "SDRF allocation Kamrup (source: 45th to 50th SEC Summary CSV)", "external", pdf_name],
        [meeting_no, date, "Kokrajhar", 2.80, "SDRF", "49 (from 45-50 summary)", "45-50 SEC Summary CSV",
         "SDRF allocation Kokrajhar (source: 45th to 50th SEC Summary CSV)", "external", pdf_name],
    ]

    itemized = make_itemized_df(rows)
    # Exclude the aggregate-only rows from per-district aggregation
    dist_rows = itemized[~itemized["district"].str.startswith("Assam")]
    aggregated = make_aggregated_df(dist_rows)
    save_dfs("49th_SEC", itemized, aggregated)
    print("  NOTE: 49th meeting – SDMF items from PDF text; SDRF district amounts from 45-50 summary.")


# ─────────────────────────────────────────────
# 47th SEC Meeting (February 10, 2023)
# ─────────────────────────────────────────────
def extract_47th():
    print("Extracting 47th SEC meeting …")
    pdf_name = "47th_sec_meeting_10.12.2022.pdf"
    meeting_no = "47th SEC"
    date = "2023-02-10"

    # Only aggregate totals available (no district breakdown in extractable text).
    # WRD: 175 projects, Rs 117.43 cr total
    # PHED: 268 projects, Rs 340.00224 lakh total
    rows = [
        [meeting_no, date, "Assam (total, no district breakdown)",
         11743.0, "SDRF", "47.11A", "WRD schemes",
         "175 WRD projects Rs 117.43 cr approved for 2022-23 (no district breakdown in minutes)",
         "p3", pdf_name],
        [meeting_no, date, "Assam (total, no district breakdown)",
         340.00224, "SDRF", "47.10", "PHED schemes",
         "268 PHED projects Rs 340.00224 lakh approved for 2022-23 (no district breakdown in minutes)",
         "p3", pdf_name],
    ]
    itemized = make_itemized_df(rows)
    aggregated = make_aggregated_df(itemized)
    save_dfs("47th_SEC", itemized, aggregated)
    print("  NOTE: 47th meeting only has aggregate totals; district breakdown not available in minutes text.")


# ─────────────────────────────────────────────
# 46th SEC Meeting (November 4 + December 6, 2022)
# ─────────────────────────────────────────────
def extract_46th():
    """
    The 46th meeting PDF text is very limited. Most project-level detail is in scanned
    portions. We supplement with data from the existing '45th to 50th SEC - Summary.csv'
    (column '46 SDRF TENDER (lakhs)') which was manually compiled.
    """
    print("Extracting 46th SEC meeting …")
    pdf_name_nov = "46th_sec_meeting.pdf"
    meeting_no = "46th SEC"
    date = "2022-11-04"
    rows = []

    # ── From 45th-to-50th SEC Summary CSV (manually compiled, authoritative for 46th) ──
    # Corresponds to '46 SDRF TENDER (lakhs)' column (timeperiod 2022_03 → March 2022 batch)
    summary_46 = {
        "Barpeta":   239.135,  "Bongaigaon": 132.96,
        "Chirang":   175.45,   "Darrang":     75.59,
        "Goalpara":    1.90,   "Kamrup":      35.60,
        "Kokrajhar": 623.97,   "Nagaon":     433.39,
    }
    for district, amount in summary_46.items():
        rows.append([meeting_no, date, district, amount, "SDRF",
                     "46 (from 45-50 summary)", "45th to 50th SEC Summary CSV",
                     f"SDRF allocation {district} (source: 45th to 50th SEC Summary CSV '46 SDRF TENDER')",
                     "external", pdf_name_nov])

    # Note: page 10 of the Nov PDF has Kokrajhar project details (ex-post-facto),
    # but those are already captured in the summary total (623.97). Parsing them
    # separately would cause double-counting, so we use only the summary CSV here.

    itemized = make_itemized_df(rows)
    aggregated = make_aggregated_df(itemized)
    save_dfs("46th_SEC", itemized, aggregated)
    print("  NOTE: 46th meeting – district amounts from 45-50 summary CSV + limited PDF text.")


# ─────────────────────────────────────────────
# 45th SEC Meeting (March 23, 2022)
# ─────────────────────────────────────────────
def extract_45th():
    """
    Extract WRD (Annexure II, IIA, IIB) and PWD Roads (Annexure III) projects.
    Only extracts rows where district AND amount appear on the SAME line.
    WRD projects (Annexure II/IIA/IIB): typically 1-1000 lakhs.
    PWD Roads (Annexure III): typically 1-200 lakhs per project.
    """
    print("Extracting 45th SEC meeting …")
    pdf_name = "45th_sec_meeting.pdf"
    meeting_no = "45th SEC"
    date = "2022-03-23"

    path = BASE_PDF + pdf_name
    with pdfplumber.open(path) as pdf:
        pages = [(i+1, p.extract_text() or "") for i, p in enumerate(pdf.pages)]

    # Annexure II: WRD ex-post-facto (pages 5-6) – large amounts up to ~1000 lakhs
    ann2_lines  = [l for pnum, txt in pages if 5 <= pnum <= 6
                   for l in txt.split("\n")]
    # Annexure IIA: admissible WRD (pages 7-13) – large amounts up to ~2000 lakhs
    ann2a_lines = [l for pnum, txt in pages if 7 <= pnum <= 13
                   for l in txt.split("\n")]
    # Annexure IIB: erosion-related (pages 14-16)
    ann2b_lines = [l for pnum, txt in pages if 14 <= pnum <= 16
                   for l in txt.split("\n")]
    # Annexure III: PWD Roads (pages 17-54) – smaller amounts, max ~200 lakhs
    ann3_lines  = [l for pnum, txt in pages if 17 <= pnum <= 54
                   for l in txt.split("\n")]

    rows = []
    rows += _parse_same_line(ann2_lines,  "Annexure II (WRD ex-post-facto)", "SDRF",
                             "45.3 WRD", meeting_no, date, pdf_name, max_amount=1500)
    rows += _parse_same_line(ann2a_lines, "Annexure IIA (WRD admissible)",   "SDRF",
                             "45.3 WRD", meeting_no, date, pdf_name, max_amount=2000)
    rows += _parse_same_line(ann2b_lines, "Annexure IIB (WRD erosion)",      "SDRF",
                             "45.3 WRD", meeting_no, date, pdf_name, max_amount=2000)
    rows += _parse_same_line(ann3_lines,  "Annexure III (PWD Roads)",        "SDRF",
                             "45.3 PWD", meeting_no, date, pdf_name, max_amount=250)

    itemized = make_itemized_df(rows)
    itemized = itemized.drop_duplicates(subset=["district", "amount_lakhs", "reason"])
    aggregated = make_aggregated_df(itemized)
    save_dfs("45th_SEC", itemized, aggregated)


# ─────────────────────────────────────────────
# 44th SEC Meeting (January 11, 2022)
# ─────────────────────────────────────────────
def extract_44th():
    """
    Extract PWD Roads (Annexure VII) and Irrigation (Annexure VIII) projects.
    Only extracts rows where district AND amount appear on the SAME line.
    PWD Roads: typically 1-300 lakhs. Irrigation: typically 0.5-50 lakhs.
    """
    print("Extracting 44th SEC meeting …")
    pdf_name = "44th_sec_meeting.pdf"
    meeting_no = "44th SEC"
    date = "2022-01-11"

    path = BASE_PDF + pdf_name
    with pdfplumber.open(path) as pdf:
        pages = [(i+1, p.extract_text() or "") for i, p in enumerate(pdf.pages)]

    # Pages 15-25: Annexure VII (PWD Roads 163 projects)
    ann7_lines = [l for pnum, txt in pages if 15 <= pnum <= 25
                  for l in txt.split("\n")]
    # Pages 26-48: Annexure VIII (Irrigation – many small projects)
    ann8_lines = [l for pnum, txt in pages if 26 <= pnum <= 48
                  for l in txt.split("\n")]

    rows = []
    rows += _parse_same_line(ann7_lines, "Annexure VII (PWD Roads)",    "SDRF",
                             "44.8", meeting_no, date, pdf_name, max_amount=300)
    rows += _parse_same_line(ann8_lines, "Annexure VIII (Irrigation)",  "SDRF",
                             "44.9", meeting_no, date, pdf_name, max_amount=50)

    itemized = make_itemized_df(rows)
    itemized = itemized.drop_duplicates(subset=["district", "amount_lakhs", "reason"])
    aggregated = make_aggregated_df(itemized)
    save_dfs("44th_SEC", itemized, aggregated)


# ─────────────────────────────────────────────
# Scanned PDFs – cannot extract without OCR
# ─────────────────────────────────────────────
def report_scanned():
    scanned = {
        "39th_sec_meeting.pdf":  "39th SEC",
        "40th_sec_meeting.pdf":  "40th SEC",
        "41st_sec_meeting.pdf":  "41st SEC",
        "42nd_sec_meeting.pdf":  "42nd SEC",
        "43rd_sec_meeting.pdf":  "43rd SEC",
    }
    print("\n⚠️  Scanned PDFs – no extractable text (OCR required):")
    for fname, label in scanned.items():
        path = BASE_PDF + fname
        with pdfplumber.open(path) as pdf:
            total_chars = sum(len(p.extract_text() or "") for p in pdf.pages)
        print(f"  {label}: {fname} ({len(pdf.pages)} pages, {total_chars} chars extracted) – SKIPPED")


# ─────────────────────────────────────────────
# Run all extractions
# ─────────────────────────────────────────────
if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    extract_55th()
    extract_49th()
    extract_48th()
    extract_47th()
    extract_46th()
    extract_45th()
    extract_44th()
    report_scanned()
    print("\nDone.")

import pandas as pd
import os
import re
import dateutil.parser
import glob

# Build file paths using os.path.join
data_path = os.path.join(os.getcwd(), 'Sources', 'SDRF', 'data', 'all_extracted_data_v2.csv')

flood_codes = ['2245-02-101-2621-000-32-01','2245-02-101-4385-000-32-01','2245-02-101-4703-000-32-01','2245-02-105-0000-000-32-01',
'2245-02-106-0000-000-17-02',
'2245-02-122-0999-000-17-05',
'2245-02-122-1000-000-17-05',
'2245-02-193-1001-000-17-05',
'2245-80-800-0821-000-17-05',
'2245-80-800-1360-000-17-05',
'2245-80-800-1360-000-32-01',
'2245-80-800-5004-000-17-05',
'2245-80-800-4617-000-17-05',
'2245-80-800-4616-000-14-99',
'2245-80-800-4615-000-17-99',
'2245-80-800-6313-000-17-05',
'2245-80-800-6314-000-17-05'
]

# Flood Keywords
POSITIVE_KEYWORDS = ['Flood', 'Embankment', 'embkt', 'Relief', 'Erosion', 'SDRF', 'Inundation', 'Hydrology',
                     'Silt', 'Siltation', 'Bund', 'Trench', 'Breach', 'Culvert', 'Sluice', 'Dyke',
                     'Storm water drain','Emergency','Immediate', 'IM', 'AE','A E', 'AAPDA MITRA']
NEGATIVE_KEYWORDS = ['Floodlight', 'Flood Light','GAS', 'FIFA', 'pipe','pipes', 'covid']

# Helper function to initialize keyword count dictionaries
def populate_keyword_dict(keyword_list): 
    return {keyword: 0 for keyword in keyword_list}

# Identify flood related tenders using keywords
def flood_filter(row):
    """
    For a given row, count the occurrences of positive and negative keywords.
    Returns a tuple of:
      (is_flood_tender, positive_keywords_dict, negative_keywords_dict)
    """
    hoa_number = str(row.get('HOA_Number', ''))[:26]
    if hoa_number in flood_codes:
        return "True", str(populate_keyword_dict(POSITIVE_KEYWORDS)), str(populate_keyword_dict(NEGATIVE_KEYWORDS))
    positive_keywords_dict = populate_keyword_dict(POSITIVE_KEYWORDS)
    negative_keywords_dict = populate_keyword_dict(NEGATIVE_KEYWORDS)
    
    # Combine selected fields into one text string
    expense_slug = ' '.join([
        str(row.get('Name of the Scheme', '')),
        str(row.get('Brief nature of the scheme', '')),
        str(row.get('Aim, objectives and benefit expected from the scheme/project', '')),
        str(row.get('Project Classification', ''))
    ])
    expense_slug = re.sub(r'[^a-zA-Z0-9 \n\.]', ' ', expense_slug)
    
    is_flood_tender = False
    for keyword in POSITIVE_KEYWORDS:
        pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
        keyword_count = len(re.findall(pattern, expense_slug.lower()))
        positive_keywords_dict[keyword] = keyword_count
        if keyword_count > 0:
            is_flood_tender = True
            
    # If any negative keyword is found, mark tender as not flood-related
    for keyword in NEGATIVE_KEYWORDS:
        pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
        keyword_count = len(re.findall(pattern, expense_slug.lower()))
        negative_keywords_dict[keyword] = keyword_count
        if keyword_count > 0:
            is_flood_tender = False
           
    return str(is_flood_tender), str(positive_keywords_dict), str(negative_keywords_dict)

# Read the CSV file
sdrf_df = pd.read_csv(data_path)

# Remove duplicate rows
sdrf_df = sdrf_df.drop_duplicates()
sdrf_df = sdrf_df[
    sdrf_df['HOA_Number']
        .astype(str)
        .str[:26]                # first 26 characters
        .isin(flood_codes)       # exact-match against your list
].copy()

# Apply flood_filter to every row and add the results as new columns
flood_filter_tuples = sdrf_df.apply(flood_filter, axis=1)
sdrf_df['is_flood_related'] = [tpl[0] for tpl in flood_filter_tuples]
sdrf_df['positive_keywords_dict'] = [tpl[1] for tpl in flood_filter_tuples]
sdrf_df['negative_keywords_dict'] = [tpl[2] for tpl in flood_filter_tuples]

print('Number of flood related expenditure filtered: ', sdrf_df.shape[0])

# Filter rows based on date format "dd-mm-yyyy"
date_pattern = r"^\d{2}-\d{2}-\d{4}$"
invalid_dates = sdrf_df[~sdrf_df['Proposal Date'].astype(str).str.match(date_pattern, na=False)]
sdrf_df = sdrf_df.drop(invalid_dates.index)

# Helper function to classify season based on Proposal Date
def classify_season(proposal_date_str):
    published_date = dateutil.parser.parse(proposal_date_str)
    if 1 <= published_date.month <= 5:
        # In May, dates after the 14th are considered Monsoon
        return "Monsoon" if (published_date.month == 5 and published_date.day > 14) else "Pre-Monsoon"
    elif 6 <= published_date.month <= 10:
        # In October, dates after the 14th are Post-Monsoon; otherwise, Monsoon
        return "Post-Monsoon" if (published_date.month == 10 and published_date.day > 14) else "Monsoon"
    else:
        return "Post-Monsoon"

sdrf_df['Season'] = sdrf_df['Proposal Date'].apply(classify_season)

# Identify scheme related information using a set of keywords
scheme_kw = {'ridf', 'sdrf', 'sopd', 'cidf', 'ltif'}
def identify_scheme(row):
    expense_slug = ' '.join([
        str(row.get('Name of the Scheme', '')),
        str(row.get('Brief nature of the scheme', '')),
        str(row.get('Aim, objectives and benefit expected from the scheme/project', '')),
        str(row.get('Project Classification', ''))
    ])
    expense_slug = re.sub(r'[^a-zA-Z0-9 \n\.]', ' ', expense_slug).lower()
    tokens = set(re.split(r'[-.,()_\s/]\s*', expense_slug))
    tokens.discard('')  # Remove any empty strings
    intersect = tokens & scheme_kw
    return list(intersect)[0].upper() if intersect else ''

sdrf_df['Scheme'] = sdrf_df.apply(identify_scheme, axis=1)

# Classify Erosion related tenders
EROSION_KEYWORDS = ['anti erosion', 'ae', 'a/e', 'a e', 'erosion', 'eroded', 'erroded', 'errosion']
def classify_erosion(row):
    expense_slug = ' '.join([
        str(row.get('Name of the Scheme', '')),
        str(row.get('Brief nature of the scheme', '')),
        str(row.get('Aim, objectives and benefit expected from the scheme/project', '')),
        str(row.get('Project Classification', ''))
    ])
    expense_slug = re.sub(r'[^a-zA-Z0-9 \n\.]', ' ', expense_slug)
    total = sum(len(re.findall(r"\b" + re.escape(kw.lower()) + r"\b", expense_slug.lower())) for kw in EROSION_KEYWORDS)
    return total > 0

sdrf_df['Erosion'] = sdrf_df.apply(classify_erosion, axis=1)

# Classify Roads, Bridges, and Embankments related tenders
ROADS_BRIDGES_EMBANKMENTS_KEYWORDS = ['roads', 'bridges', 'road', 'bridge', 'storm water drain', 'drain',
                                      'box cul', 'box culvert', 'box culv', 'culvert', 'embankment', 'embkt',
                                      'river bank protection', 'bund', 'bunds', 'bundh', 'bank protection', 'dyke',
                                      'dyke wall', 'dyke walls', 'silt', 'siltation', 'sluice', 'breach']
def classify_roads_bridges(row):
    expense_slug = ' '.join([
        str(row.get('Name of the Scheme', '')),
        str(row.get('Brief nature of the scheme', '')),
        str(row.get('Aim, objectives and benefit expected from the scheme/project', '')),
        str(row.get('Project Classification', ''))
    ])
    expense_slug = re.sub(r'[^a-zA-Z0-9 \n\.]', ' ', expense_slug)
    total = sum(len(re.findall(r"\b" + re.escape(kw.lower()) + r"\b", expense_slug.lower())) for kw in ROADS_BRIDGES_EMBANKMENTS_KEYWORDS)
    return total > 0

sdrf_df['Roads_Bridges_Embkt'] = sdrf_df.apply(classify_roads_bridges, axis=1)

# Classification of Tenders based on Response Type
IMMEDIATE_MEASURES_KEYWORDS = ['sdrf','im','i/m','gr','g/r','relief','package','pkt','immediate', 'emergency', 'pk', 'g.r.', 'i.m.']
REPAIR_RESTORATION_IMPROVEMENTS_KEYWORDS = ['improvement', 'imp.', 'impvt', 'impt.', 'repair',
                                            'repairing', 'restoration', 'reconstruction', 'reconstn', 'recoupment',
                                            'raising', 'strengthening', 'r/s', 'm and r', 'upgradation', 'renovation',
                                            'repairing/renovation', 'up-gradation', 'm-r', 'm-r ', 'mr', 'widening', 'r s', 'extension']
PREPAREDNESS_KEYWORDS = ['shelter', 'shelters', 'tarpaulin', 'shelter ',
                         'responder kit', 'aapda mitra volunteers','aapda mitra volunteer', 
                         'district emergency stockpile', 'search light', 'life buoys', 
                         'boat ambulances', 'boat ambulance', 'inflatable rubber', 
                         'mechanized boats', 'mechanised boats','mechanized boat', 'mechanised boat']

def classify_response(row):
    expense_slug = ' '.join([
        str(row.get('Name of the Scheme', '')),
        str(row.get('Brief nature of the scheme', '')),
        str(row.get('Aim, objectives and benefit expected from the scheme/project', '')),
        str(row.get('Project Classification', ''))
    ])
    expense_slug = re.sub(r'[^a-zA-Z0-9 \n\.]', ' ', expense_slug)
    
    immediate_dict = populate_keyword_dict(IMMEDIATE_MEASURES_KEYWORDS)
    repair_dict = populate_keyword_dict(REPAIR_RESTORATION_IMPROVEMENTS_KEYWORDS)
    preparedness_dict = populate_keyword_dict(PREPAREDNESS_KEYWORDS)
    
    response_type = "Others"
    
    # Check Immediate Measures
    for keyword in immediate_dict:
        pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
        count = len(re.findall(pattern, expense_slug.lower()))
        immediate_dict[keyword] = count if count > 0 else False
        if count > 0:
            response_type = "Immediate Measures"
    
    # Check Repair and Restoration (update only if response_type is still "Others")
    for keyword in repair_dict:
        pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
        count = len(re.findall(pattern, expense_slug.lower()))
        repair_dict[keyword] = count if count > 0 else False
        if count > 0 and response_type == "Others":
            response_type = "Repair and Restoration"
    
    # Check Preparedness Measures (update only if response_type is still "Others")
    for keyword in preparedness_dict:
        pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
        count = len(re.findall(pattern, expense_slug.lower()))
        preparedness_dict[keyword] = count if count > 0 else False
        if count > 0 and response_type == "Others":
            response_type = "Preparedness Measures"
    
    subhead = ""
    if response_type == "Immediate Measures":
        sub_dict = {k: v for k, v in immediate_dict.items() if v}
        subhead = str(sub_dict)
    elif response_type == "Repair and Restoration":
        sub_dict = {k: v for k, v in repair_dict.items() if v}
        subhead = str(sub_dict)
    elif response_type == "Preparedness Measures":
        sub_dict = {k: v for k, v in preparedness_dict.items() if v}
        subhead = str(sub_dict)
    
    return response_type, subhead

response_classification = sdrf_df.apply(classify_response, axis=1)
sdrf_df['Response Type'] = [res[0] for res in response_classification]
sdrf_df['Flood Response - Subhead'] = [res[1] for res in response_classification]

# Write the output CSV using os.path.join
output_path = os.path.join(os.getcwd(), 'Sources', 'SDRF', 'data', 'flood_expenditure_v2.csv')
sdrf_df.to_csv(output_path, encoding='utf-8', index=False)

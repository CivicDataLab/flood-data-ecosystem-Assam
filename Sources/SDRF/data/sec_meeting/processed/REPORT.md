# Assam SEC / SDRF minutes — analysis

## 0. Corpus & data coverage

- Documents parsed: **21**
- Meeting date range: **2013–2026**
- Meetings with a parseable date: **21/21**
- Allocation line-items extracted: **8344**
- Total allocation captured: **₹47807.308 crore**
- Line-items with low-confidence auto-classification: **21%** (review these before quoting work-type/phase splits)
- Line-items with **amount_flag set: 323** — these had an ambiguous unit (bare 6+ digit value, or a comma-grouped value < ₹1000) and were read as rupees; verify against the source PDF. Filter `amount_flag` in `line_items.csv`.

## 1. Spending patterns over time

|   year |   allocation_cr |   meetings_with_data |
|-------:|----------------:|---------------------:|
|   2013 |         682.647 |                    3 |
|   2019 |         819.532 |                    2 |
|   2020 |        8650.32  |                    2 |
|   2021 |       17566.3   |                    1 |
|   2022 |        8028.77  |                    5 |
|   2023 |          74.47  |                    2 |
|   2024 |        3322.29  |                    2 |
|   2025 |        4540.8   |                    3 |
|   2026 |        4122.19  |                    1 |

> Caveat: yearly totals reflect *which meetings approved money*, not a steady budget series — SDRF approval meetings are irregular and some years have none. Treat gaps as missing data, not zero spend.

## 2. District & department analysis (allocation)

**Top districts (₹ crore):**

| district      |   allocation_cr |
|:--------------|----------------:|
| Golaghat      |       17203.3   |
| Udalguri      |        1951.47  |
| Darrang       |         317.981 |
| Guwahati City |         276.22  |
| Jorhat        |         274.334 |
| Dibrugarh     |         267.015 |
| Cachar        |         221.151 |
| Barpeta       |         220.688 |
| Kamrup        |         174.148 |
| udalgur       |         154.981 |

**By department (₹ crore):**

| department                               |   allocation_cr |
|:-----------------------------------------|----------------:|
| Water Resources                          |       28231.5   |
| Revenue & DM                             |        9703.04  |
| Disaster Management Department           |        3805.96  |
| PWD                                      |        2848     |
| Fire & Emergency Services                |        2603.97  |
| Animal Husbandry & Veterinary            |         257.449 |
| Home Department                          |         127.977 |
| Soil Conservation                        |          98.543 |
| ASDMA                                    |          41.052 |
| PWD (Roads)                              |          35.668 |
| PWD (Buildings)                          |          21.566 |
| Fishery Department                       |          13.006 |
| Power                                    |           7.957 |
| Education                                |           6.648 |
| Irrigation                               |           4.491 |
| Handloom & Textile Department            |           0.347 |
| Dhubri Civil Sub Division T. R. Division |           0.065 |
| Public Health Engineering                |           0.056 |

> Utilisation vs allocation: the minutes record *approved allocations*. Actual fund **utilisation/expenditure** appears only sporadically inside Action-Taken-Reports and is not a structured column — so a clean allocation-vs-utilisation comparison is **not** reliably available from this corpus. Allocation is reported here; utilisation is partial at best.

## 3. Types of work

| work_type                      |   items |   allocation_cr |
|:-------------------------------|--------:|----------------:|
| Other / Unclassified           |    1968 |       33556.1   |
| Roads & Bridges                |    3713 |        8149.71  |
| Restoration of damaged assets  |    1469 |        3655.63  |
| Embankment / Flood protection  |     703 |         728.5   |
| Buildings / Shelter            |     198 |         670.467 |
| Relief / Gratuitous assistance |      89 |         544.026 |
| Equipment / Procurement        |      95 |         247.164 |
| Capacity building / Training   |      76 |         213.3   |
| Drainage / De-silting          |      28 |          35.165 |
| Health / Veterinary response   |       2 |           5.714 |
| Water supply / Sanitation      |       3 |           1.495 |

_(work-type × department cross-tab saved to `03_worktype_by_department.csv`)_

## 4. Stakeholder / attendance analysis

- Distinct attendees identified: **434** across **15** meetings

**Most frequent attendees:**

| name                       |   meetings |
|:---------------------------|-----------:|
| Dr. Ravi Kota, IAS         |          6 |
| Biswajit Kalita            |          5 |
| Varshaty Das               |          4 |
| Dr. Sadique Ali Ahmed      |          4 |
| Debajit Bhuyan             |          4 |
| Sudip Kr. Roy              |          3 |
| Shri Paban Kumar Borthakur |          3 |
| Biraj Das                  |          3 |
| Rakesh Das                 |          3 |
| Paban Terang               |          3 |
| Pranab Borah               |          3 |
| P. Saikia                  |          3 |
| Shri Jishnu Barua, IAS     |          3 |
| Hemanga Talukdar           |          3 |
| Seema Rabha                |          3 |

**Departments represented (by attendance count):**

| department                |   appearances |
|:--------------------------|--------------:|
| Water Resources           |            42 |
| Irrigation                |            18 |
| Assam                     |            14 |
| Agriculture               |            12 |
| Public Health Engineering |            11 |
| PWD                       |            11 |
| Soil Conservation         |            11 |
| ASDMA                     |            10 |
| Health & Family Welfare   |             8 |
| Power                     |             8 |
| Education                 |             8 |
| Fire & Emergency Services |             7 |
| Revenue & DM              |             6 |
| SSA                       |             5 |
| Govt. of Assam            |             5 |

## 5. Disaster-management phase split

| disaster_phase                 |   items |   allocation_cr |
|:-------------------------------|--------:|----------------:|
| Mitigation                     |     382 |        2307.33  |
| Preparedness                   |     207 |         842.319 |
| Response, Repair & Restoration |    5660 |       10124.5   |
| Unclassified                   |    2095 |       34533.2   |

> Phase labels are inferred from work descriptions with a keyword rubric (preparedness / mitigation / response-repair-restoration). Many SDRF items are 'Immediate Measures' which are inherently response/restoration; genuinely preventive 'mitigation' spend is the harder, more ambiguous bucket — verify low-confidence rows.

## 6. How priorities shifted over time

_Phase share by year saved to `06_phase_share_by_year.csv` and `charts/06_phase_share.png`._
_Work-type share by year saved to `06_worktype_share_by_year.csv`._

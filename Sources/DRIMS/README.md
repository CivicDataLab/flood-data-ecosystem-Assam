# FRIMS

The Assam State Disaster Management Authority (ASDMA) maintains a robust data system that collects information on damages due to floods in every monsoon season. This data includes population affected by floods, houses damaged, crop area affected, infrastructure affected etc. ASDMA released the damages data on a daily basis during monsoons using the Flood Reporting and Information Management System ([FRIMS](http://www.asdma.gov.in/reports.html))

Since October 2023, the FRIMS reporting system has been updated to the Disaster Reporting and Information Management System (DRIMS). Raw data is now accessed through an api and saved in the folder "data/DRIMS-api_output". The notebooks DRIMS_data-explorer and DRIMS_extractor in the "scripts" folder are used to explore the data structure and transform relevant variables for ingestion into IDS-DRR. The folder "data/variables" contains the monthly variables indexed at the revenue circle level.

## Variables extracted from the source

1. `total-animal-washed-away`: Number of animals washed away
2. `total-animal-affected`: Number of animals affected
3. `population-affected-total`: Population affected due to floods
4. `Relief-Camp-inmates`: Number of Relief camp inmates
5. `human-live-lost`: Human lives lost due to floods
6. `crop-area`: Crop area affected due to floods
7. `total-house-fully-damaged`: Number of houses damaged due to floods
8. `embankments-affected`: Number of embankments affected due to floods
9. `roads`: Number of roads damaged due to floods
10. `Bridge`: Number of bridges damaged due to floods
11. `number-relief-camps`: Number of Relief camps established
12. `Embankment breached`: Number of embankments breached due to floods


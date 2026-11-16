"""Catalogue of every downloaded file.

Each entry says where the file comes from and which licence covers it. The
licence evidence is the page that was read on 2026-11-16 and the sentence
found there. Numbers never come from this file; they come from the raw files.
"""

SOURCES = [
    {
        "id": "eia_mer_t0901",
        "title": "EIA Monthly Energy Review, Table 9.1: Crude Oil Price Summary",
        "publisher": "U.S. Energy Information Administration",
        "url": "https://www.eia.gov/totalenergy/data/browser/csv.php?tbl=T09.01",
        "filename": "T09.01.csv",
        "region": "US",
        "licence": "Public domain (U.S. government publication)",
        "licence_url": "https://www.eia.gov/about/copyrights_reuse.php",
        "licence_evidence": "U.S. government publications are in the public domain and are not subject to copyright protection.",
    },
    {
        "id": "eia_mer_t0904",
        "title": "EIA Monthly Energy Review, Table 9.4: Retail Motor Gasoline and On-Highway Diesel Fuel Prices",
        "publisher": "U.S. Energy Information Administration",
        "url": "https://www.eia.gov/totalenergy/data/browser/csv.php?tbl=T09.04",
        "filename": "T09.04.csv",
        "region": "US",
        "licence": "Public domain (U.S. government publication)",
        "licence_url": "https://www.eia.gov/about/copyrights_reuse.php",
        "licence_evidence": "U.S. government publications are in the public domain and are not subject to copyright protection.",
    },
    {
        "id": "eia_mer_t0307c",
        "title": "EIA Monthly Energy Review, Table 3.7c: Petroleum Consumption, Transportation and Electric Power Sectors",
        "publisher": "U.S. Energy Information Administration",
        "url": "https://www.eia.gov/totalenergy/data/browser/csv.php?tbl=T03.07C",
        "filename": "T03.07C.csv",
        "region": "US",
        "licence": "Public domain (U.S. government publication)",
        "licence_url": "https://www.eia.gov/about/copyrights_reuse.php",
        "licence_evidence": "U.S. government publications are in the public domain and are not subject to copyright protection.",
    },
    {
        "id": "eia_mer_t1105",
        "title": "EIA Monthly Energy Review, Table 11.5: CO2 Emissions From Energy Consumption, Transportation Sector",
        "publisher": "U.S. Energy Information Administration",
        "url": "https://www.eia.gov/totalenergy/data/browser/csv.php?tbl=T11.05",
        "filename": "T11.05.csv",
        "region": "US",
        "licence": "Public domain (U.S. government publication)",
        "licence_url": "https://www.eia.gov/about/copyrights_reuse.php",
        "licence_evidence": "U.S. government publications are in the public domain and are not subject to copyright protection.",
    },
    {
        "id": "eia_brent_annual",
        "title": "EIA Europe Brent Spot Price FOB, annual (RBRTE)",
        "publisher": "U.S. Energy Information Administration",
        "url": "https://www.eia.gov/dnav/pet/hist_xls/RBRTEa.xls",
        "filename": "RBRTEa.xls",
        "region": "World benchmark",
        "licence": "Public domain (U.S. government publication)",
        "licence_url": "https://www.eia.gov/about/copyrights_reuse.php",
        "licence_evidence": "U.S. government publications are in the public domain and are not subject to copyright protection.",
    },
    {
        "id": "fhwa_vm203",
        "title": "FHWA Highway Statistics 2024, Table VM-203: Annual vehicle-miles of travel, 1957-2024",
        "publisher": "U.S. Federal Highway Administration",
        "url": "https://www.fhwa.dot.gov/policyinformation/statistics/2024/xls/vm203.xlsx",
        "filename": "vm203.xlsx",
        "region": "US",
        "licence": "U.S. government work (not subject to U.S. copyright, 17 U.S.C. 105)",
        "licence_url": "https://www.usa.gov/government-copyright",
        "licence_evidence": "FHWA is a U.S. federal agency; U.S. government works are not subject to U.S. copyright (17 U.S.C. 105). Data.gov lists FHWA's related VM-1 dataset under https://www.usa.gov/government-works.",
    },
    {
        "id": "fhwa_vm1_2000_2024",
        "title": "FHWA Annual Vehicle Distance Traveled in Miles and Related Data, 2000-2024 (Table VM-1)",
        "publisher": "U.S. Federal Highway Administration (data.transportation.gov)",
        "url": "https://data.transportation.gov/api/v3/views/9ey8-2qc4/export.csv?accessType=DOWNLOAD",
        "filename": "vm1_2000_2024.csv",
        "region": "US",
        "licence": "U.S. government work",
        "licence_url": "https://catalog.data.gov/dataset/annual-vehicle-distance-traveled-in-miles-and-related-data-2000-2023-vm-1",
        "licence_evidence": "Catalog entry: License https://www.usa.gov/government-works; access level public; publisher Federal Highway Administration.",
    },
    {
        "id": "worldbank_pop",
        "title": "World Bank World Development Indicators, SP.POP.TOTL (Population, total) for World and United States",
        "publisher": "World Bank",
        "url": "https://api.worldbank.org/v2/country/WLD;USA/indicator/SP.POP.TOTL?format=json&per_page=500",
        "filename": "sp_pop_totl.json",
        "region": "World and US",
        "licence": "CC BY 4.0",
        "licence_url": "https://datacatalog.worldbank.org/search/dataset/0037712/World-Development-Indicators",
        "licence_evidence": "License: Creative Commons Attribution 4.0",
    },
    {
        "id": "ember_ev_monthly",
        "title": "Ember Monthly EV Sales Data (new car registrations by drivetrain)",
        "publisher": "Ember",
        "url": "https://files.ember-energy.org/public-downloads/transport/outputs/monthly_ev_sales.csv",
        "filename": "monthly_ev_sales.csv",
        "region": "World and US",
        "licence": "CC BY 4.0",
        "licence_url": "https://ember-energy.org/data/monthly-ev-sales-data",
        "licence_evidence": "All data is free and open-access under the Creative Commons Attribution 4.0 (CC-BY 4.0) license; footer: All content is released under a Creative Commons Attribution Licence (CC-BY-4.0).",
    },
    {
        "id": "epa_trends_tier1",
        "title": "EPA Air Pollutant Emissions Trends Data, national Tier 1 criteria air pollutants (updated 2026-09-04)",
        "publisher": "U.S. Environmental Protection Agency",
        "url": "https://www.epa.gov/system/files/other-files/2026-09/national_tier1_caps_04sep2026.xlsx",
        "filename": "national_tier1_caps.xlsx",
        "region": "US",
        "licence": "U.S. government work; EPA web policy allows free distribution and use for non-commercial, scientific and educational purposes",
        "licence_url": "https://www.epa.gov/web-policies-and-procedures/epa-disclaimers",
        "licence_evidence": "may be freely distributed and used for non-commercial, scientific and educational purposes",
    },
]

# Sources that were considered and NOT used, with the reason. Shown on the
# licences page so the gaps are visible.
REJECTED = [
    {
        "name": "IEA Global EV Outlook data (EV stock, world and US)",
        "reason": "Licence could not be verified for the downloadable file. Our World in Data's metadata cites the 2026 report as CC BY 4.0, "
        "while a web-search summary of IEA's 2026 data-product page reported IEA terms for non-CC material. iea.org refused "
        "our requests (HTTP 403), so the page itself could not be read. Not used.",
    },
    {
        "name": "BTS National Transportation Statistics (vehicles in use, Table 1-11; EV sales, Table 1-19)",
        "reason": "bts.gov refused scripted requests (HTTP 403). The block was not circumvented. Not used.",
    },
    {
        "name": "Argonne National Laboratory light-duty electric drive vehicle monthly sales",
        "reason": "anl.gov refused scripted requests (HTTP 403). Not used.",
    },
    {
        "name": "FHWA Highway Statistics Summary to 1995, Table MV-200 (registrations 1900-1995)",
        "reason": "Published only as an Excel 4 workbook (.xlw, BIFF4W) and a PDF; no parser in this project reads either reliably. Not used.",
    },
    {
        "name": "OICA world motor vehicle production",
        "reason": "Its licence was not checked in this build and no openly licensed alternative was found. Not used.",
    },
]

NOT_COVERED = [
    {"item": "Number of car companies over time", "why": "No citable, openly licensed time series was found."},
    {"item": "Cars in use before 2000, and anything since the first car", "why": "U.S. registered vehicles here start in 2000 (FHWA VM-1) and miles driven in 1957 (FHWA VM-203). The only official long series found (FHWA MV-200, 1900-1995) is not machine-readable here; see the sources page."},
    {"item": "World cars in use and world car production", "why": "No openly licensed source with a verifiable licence was found."},
    {"item": "World transport CO2", "why": "Not downloaded in this build; no sector-level open file was added."},
    {"item": "EV fleet (stock) size", "why": "The openly licensed EV file (Ember) gives new registrations, not the fleet in use."},
]


def by_id(source_id):
    for s in SOURCES:
        if s["id"] == source_id:
            return s
    raise KeyError(source_id)

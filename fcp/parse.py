"""Parse the raw downloaded files into annual series.

Every value is read from a file in data/raw. Nothing is typed by hand.
Flags mark values that must stay out of correlations and scoring by default:
  provisional      latest year of an EIA Monthly Energy Review table (EIA revises it)
  carried_forward  EPA says the year repeats an earlier inventory for mobile sources
  partial          a calendar year with fewer than 12 monthly values
  estimated        derived with an assumption (only used where stated)

Usage: python -m fcp.parse   (writes data/processed/series.json)
"""

import csv
import datetime as dt
import json
import os

from fcp.fetch import RAW, ROOT

PROCESSED = os.path.join(ROOT, "data", "processed", "series.json")

# EPA README, sheet README of the 2026-09-04 workbook, revision note:
# "2024 is the same as 2023 NEI data but includes year 2024 updates for NOX and
# SO2 EGU data ... 2025 is also the same as the 2023 NEI except for year 2025 NOX
# and SO2 EGU data ..." Highway vehicles are not EGUs, so for them 2024 and 2025
# repeat 2023. tests/test_data.py checks this against the numbers.
EPA_CARRIED_FORWARD_YEARS = (2024, 2025)


def raw_path(source_id, filename):
    return os.path.join(RAW, source_id, filename)


def _num(s):
    s = (s or "").strip().replace(",", "")
    if s in ("", "Not Available", "Not Meaningful", "Not Applicable", "Withheld", "NA", "--"):
        return None
    return float(s)


def mer_annual(source_id, filename, msn):
    """Annual values (YYYY13 rows) for one MSN code of an EIA MER CSV."""
    vals = {}
    table_last = 0
    with open(raw_path(source_id, filename), encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row["YYYYMM"].endswith("13") and _num(row["Value"]) is not None:
                table_last = max(table_last, int(row["YYYYMM"][:4]))
            if row["MSN"] != msn or not row["YYYYMM"].endswith("13"):
                continue
            v = _num(row["Value"])
            if v is not None:
                vals[int(row["YYYYMM"][:4])] = v
    flags = {}
    if vals and max(vals) == table_last:
        flags[max(vals)] = "provisional"
    return vals, flags


def brent_annual():
    import xlrd

    book = xlrd.open_workbook(raw_path("eia_brent_annual", "RBRTEa.xls"))
    sh = book.sheet_by_name("Data 1")
    vals = {}
    for i in range(3, sh.nrows):
        d, v = sh.row_values(i)[:2]
        if isinstance(d, float) and isinstance(v, float):
            year = xlrd.xldate_as_datetime(d, book.datemode).year
            vals[year] = v
    return vals, {}


def vm203_total_vmt():
    """FHWA VM-203 grand total (all roads), millions of vehicle-miles."""
    import openpyxl

    ws = openpyxl.load_workbook(raw_path("fhwa_vm203", "vm203.xlsx"), data_only=True, read_only=True)["SUMMARY"]
    vals = {}
    for row in ws.iter_rows(values_only=True):
        y = row[0]
        try:
            year = int(str(y).strip())
        except (TypeError, ValueError):
            continue
        if 1900 < year < 2100 and isinstance(row[19], (int, float)):
            vals[year] = float(row[19])
    return vals, {}


VM1_TYPES = (
    "Light Duty Vehicles Short Wheelbase",
    "Light Duty Vehicles Long Wheelbase",
    "Motorcycles",
    "Buses",
    "Single Unit Trucks",
    "Combination Trucks",
)


def vm1_total_vmt():
    """FHWA VM-1 total vehicle-miles (millions), six vehicle types summed.

    Used only to cross-check VM-203 (the pre-registered series); never joined to it.
    """
    best = {}
    with open(raw_path("fhwa_vm1_2000_2024", "vm1_2000_2024.csv"), encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row["Item"] != "Total_VMT" or row["Vehicle_Type"] not in VM1_TYPES:
                continue
            v = _num(row["Data"])
            if v is None:
                continue
            key = (int(row["Year"]), row["Vehicle_Type"])
            ry = int(row["Report_Year"])
            if key not in best or ry > best[key][0]:
                best[key] = (ry, v)
    years = sorted({k[0] for k in best})
    return {y: sum(best[(y, t)][1] for t in VM1_TYPES) / 1e6 for y in years if all((y, t) in best for t in VM1_TYPES)}


def vm1_registered_vehicles():
    """FHWA VM-1: registered vehicles, sum of six disjoint vehicle types.

    A year appears in more than one report year (revisions). The value from the
    latest report year is used. A year missing any of the six types is left out.
    """
    best = {}  # (year, type) -> (report_year, value)
    with open(raw_path("fhwa_vm1_2000_2024", "vm1_2000_2024.csv"), encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row["Item"] != "No._Vehicles_Registered" or row["Vehicle_Type"] not in VM1_TYPES:
                continue
            v = _num(row["Data"])
            if v is None:
                continue
            key = (int(row["Year"]), row["Vehicle_Type"])
            ry = int(row["Report_Year"])
            if key not in best or ry > best[key][0]:
                best[key] = (ry, v)
    years = sorted({k[0] for k in best})
    vals = {}
    for y in years:
        parts = [best.get((y, t)) for t in VM1_TYPES]
        if all(p is not None for p in parts):
            vals[y] = sum(p[1] for p in parts)
    return vals, {}


def worldbank_pop(country_iso3):
    with open(raw_path("worldbank_pop", "sp_pop_totl.json"), encoding="utf-8") as f:
        data = json.load(f)
    vals, flags = {}, {}
    for r in data[1]:
        if r["countryiso3code"] != country_iso3 or r["value"] is None:
            continue
        y = int(r["date"])
        vals[y] = float(r["value"])
        if r.get("obs_status"):
            flags[y] = "estimated"
    return vals, flags


def ember_annual(area, drivetrain):
    """Sum of monthly registrations per calendar year; years with <12 months flagged partial."""
    sums, months = {}, {}
    with open(raw_path("ember_ev_monthly", "monthly_ev_sales.csv"), encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row["Area"] != area or row["Drivetrain"] != drivetrain or row["Data frequency"] != "Monthly":
                continue
            v = _num(row["Registrations"])
            if v is None:
                continue
            y = int(row["Date"][:4])
            sums[y] = sums.get(y, 0.0) + v
            months.setdefault(y, set()).add(row["Date"][:7])
    flags = {y: "partial" for y, m in months.items() if len(m) < 12}
    return sums, flags


def epa_highway(pollutant_sheet):
    """EPA trends workbook: national HIGHWAY VEHICLES row (thousand short tons)."""
    import openpyxl

    ws = openpyxl.load_workbook(raw_path("epa_trends_tier1", "national_tier1_caps.xlsx"), data_only=True, read_only=True)[pollutant_sheet]
    header = None
    vals = {}
    for row in ws.iter_rows(values_only=True):
        if row and row[0] == "Source Category":
            header = row
            continue
        if header and row and isinstance(row[0], str) and row[0].strip().upper() == "HIGHWAY VEHICLES":
            for h, v in zip(header[1:], row[1:]):
                if isinstance(h, (int, float)) and isinstance(v, (int, float)):
                    vals[int(h)] = float(v)
            break
    flags = {y: "carried_forward" for y in EPA_CARRIED_FORWARD_YEARS if y in vals}
    return vals, flags


def ratio(num, den, scale=1.0):
    return {y: scale * num[y] / den[y] for y in num if y in den and den[y]}


def merge_flags(*flag_dicts):
    out = {}
    for fd in flag_dicts:
        for y, f in fd.items():
            out.setdefault(y, f)
    return out


def build():
    series = []

    def add(sid, label, region, unit, source_ids, vals, flags, note="", kind="level"):
        series.append({
            "id": sid,
            "label": label,
            "region": region,
            "unit": unit,
            "sources": source_ids,
            "note": note,
            "kind": kind,
            "values": {str(y): vals[y] for y in sorted(vals)},
            "flags": {str(y): flags[y] for y in sorted(flags) if y in vals},
        })

    v, f = mer_annual("eia_mer_t0901", "T09.01.csv", "RACPUUS")
    add("us_crude_rac", "U.S. crude oil price (refiner acquisition cost, composite)", "US", "dollars per barrel", ["eia_mer_t0901"], v, f)
    v, f = mer_annual("eia_mer_t0904", "T09.04.csv", "RUUCUUS")
    add("us_gasoline_unleaded", "U.S. retail unleaded regular gasoline (city average, incl. taxes)", "US", "dollars per gallon", ["eia_mer_t0904"], v, f)
    v, f = mer_annual("eia_mer_t0904", "T09.04.csv", "RLUCUUS")
    add("us_gasoline_leaded", "U.S. retail leaded regular gasoline (city average, incl. taxes)", "US", "dollars per gallon", ["eia_mer_t0904"], v, f,
        note="Separate EIA series; not joined to the unleaded line.")
    v, f = mer_annual("eia_mer_t0307c", "T03.07C.csv", "MGACPUS")
    add("us_motor_gasoline_use", "U.S. motor gasoline consumed by transportation", "US", "thousand barrels per day", ["eia_mer_t0307c"], v, f)
    v, f = mer_annual("eia_mer_t1105", "T11.05.csv", "TEACEUS")
    add("us_transport_co2", "U.S. transportation-sector CO2 emissions (total energy)", "US", "million metric tons CO2", ["eia_mer_t1105"], v, f)
    vmt, f = vm203_total_vmt()
    add("us_vmt", "U.S. vehicle-miles traveled, all roads", "US", "million vehicle-miles", ["fhwa_vm203"], vmt, f)
    reg, f = vm1_registered_vehicles()
    add("us_registered_vehicles", "U.S. registered vehicles (FHWA VM-1, six vehicle types summed)", "US", "vehicles", ["fhwa_vm1_2000_2024"], reg, f)
    us_pop, f_pop = worldbank_pop("USA")
    add("us_population", "U.S. population", "US", "people", ["worldbank_pop"], us_pop, f_pop)
    add("us_vehicles_per_1000", "U.S. registered vehicles per 1,000 people", "US", "vehicles per 1,000 people",
        ["fhwa_vm1_2000_2024", "worldbank_pop"], ratio(reg, us_pop, 1000.0), f_pop, kind="derived",
        note="FHWA registrations divided by World Bank population for the same year.")
    ev, f_ev = ember_annual("United States", "Electric vehicle (BEV+PHEV)")
    allc, f_all = ember_annual("United States", "All drivetrains")
    add("us_ev_registrations", "U.S. new electric car registrations (BEV+PHEV)", "US", "cars per year", ["ember_ev_monthly"], ev, f_ev)
    add("us_new_car_registrations", "U.S. new car registrations, all drivetrains", "US", "cars per year", ["ember_ev_monthly"], allc, f_all)
    add("us_ev_share", "U.S. electric share of new car registrations", "US", "percent", ["ember_ev_monthly"],
        ratio(ev, allc, 100.0), merge_flags(f_ev, f_all), kind="derived")
    for sheet, name in (("NOX", "NOx"), ("CO", "CO"), ("VOC", "VOC"), ("PM25Primary", "PM2.5 (primary)")):
        v, f = epa_highway(sheet)
        add("us_highway_" + sheet.lower().replace("primary", ""), "U.S. highway-vehicle %s emissions" % name, "US",
            "thousand short tons", ["epa_trends_tier1"], v, f)
    v, f = brent_annual()
    add("world_brent", "Brent crude oil spot price (world benchmark)", "World", "dollars per barrel", ["eia_brent_annual"], v, f)
    wp, f_wp = worldbank_pop("WLD")
    add("world_population", "World population", "World", "people", ["worldbank_pop"], wp, f_wp)
    ev, f_ev = ember_annual("World", "Electric vehicle (BEV+PHEV)")
    allc, f_all = ember_annual("World", "All drivetrains")
    add("world_ev_registrations", "World new electric car registrations (BEV+PHEV)", "World", "cars per year", ["ember_ev_monthly"], ev, f_ev,
        note="Ember global estimate.")
    add("world_new_car_registrations", "World new car registrations, all drivetrains", "World", "cars per year", ["ember_ev_monthly"], allc, f_all,
        note="Ember global estimate.")
    add("world_ev_share", "World electric share of new car registrations", "World", "percent", ["ember_ev_monthly"],
        ratio(ev, allc, 100.0), merge_flags(f_ev, f_all), kind="derived")
    return series


def main():
    series = build()
    os.makedirs(os.path.dirname(PROCESSED), exist_ok=True)
    with open(PROCESSED, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"generated_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(), "series": series}, f, indent=1)
        f.write("\n")
    for s in series:
        ys = [int(y) for y in s["values"]]
        print("%-28s %4s-%4s n=%3d flags=%s" % (s["id"], min(ys) if ys else "-", max(ys) if ys else "-", len(ys), s["flags"]))


if __name__ == "__main__":
    main()

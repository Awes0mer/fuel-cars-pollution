"""Citations for every source, with the edition date read from the files.

The release or update date is taken from the downloaded file itself where the
file states one; otherwise only the retrieval date (from data/manifest.json)
is given. Nothing here is typed by hand except the citation pattern.
"""

import datetime as dt
import json
import os
import re

from fcp.fetch import MANIFEST, RAW
from fcp.sources import SOURCES

HYDRADB = {
    "name": "HydraDB",
    "version": "v0.4.0",
    "url": "https://github.com/hydra-db/hydradb",
    "licence": "Elastic License 2.0",
    "licence_url": "https://www.elastic.co/licensing/elastic-license",
}


def _raw(source_id, filename):
    return os.path.join(RAW, source_id, filename)


def _retrieved(source_id):
    with open(MANIFEST, encoding="utf-8") as f:
        m = {e["id"]: e for e in json.load(f)["files"]}
    return dt.datetime.fromisoformat(m[source_id]["retrieved_at_utc"]) if source_id in m else None


def edition(source_id):
    """Release/update statement found inside the downloaded file, or None."""
    if source_id.startswith("eia_mer_"):
        # The landing page states the release current when it was read. A table belongs to that
        # release only if the page was read after the table was downloaded AND the release it
        # names came out on an earlier day than the download: no newer release can sit between the two reads.
        # Otherwise the association is unknown and no date is given.
        with open(_raw("eia_mer_index", "index.html"), encoding="utf-8", errors="replace") as f:
            m = re.search(r'Release Date:</span>\s*<span class="date">\s*([^<]+?)\s*</span>', f.read())
        if not m or source_id == "eia_mer_index":
            return "release of %s" % m.group(1) if m else None
        try:
            released = dt.datetime.strptime(m.group(1), "%B %d, %Y").date()
        except ValueError:
            return None
        t_table, t_index = _retrieved(source_id), _retrieved("eia_mer_index")
        if t_table and t_index and t_table <= t_index and released < t_table.date():  # a same-day release could be newer than the table
            return "release of %s" % m.group(1)
        return None
    if source_id == "eia_brent_annual":
        import xlrd

        sh = xlrd.open_workbook(_raw(source_id, "RBRTEa.xls")).sheet_by_name("Contents")
        for i in range(sh.nrows):
            row = [str(c).strip() for c in sh.row_values(i) if str(c).strip()]
            if len(row) >= 2 and row[0] == "Release Date:":
                return "release of %s" % row[1]
        return None
    if source_id == "fhwa_vm203":
        import openpyxl

        ws = openpyxl.load_workbook(_raw(source_id, "vm203.xlsx"), read_only=True)["SUMMARY"]
        for row in ws.iter_rows(min_row=1, max_row=8, values_only=True):
            for c in row:
                if isinstance(c, str) and re.fullmatch(r"[A-Z]+ \d{4}", c.strip()):
                    return "table dated %s" % c.strip().title()
        return None
    if source_id == "worldbank_pop":
        with open(_raw(source_id, "sp_pop_totl.json"), encoding="utf-8") as f:
            return "last updated %s" % json.load(f)[0]["lastupdated"]
    if source_id == "epa_trends_tier1":
        import openpyxl

        ws = openpyxl.load_workbook(_raw(source_id, "national_tier1_caps.xlsx"), read_only=True)["README"]
        for row in ws.iter_rows(values_only=True):
            c = row[0] if row else None
            if isinstance(c, str) and c.startswith("Updated "):
                return "updated " + c.strip()[len("Updated "):]
        return None
    return None


def accessed(source_id):
    with open(MANIFEST, encoding="utf-8") as f:
        m = {e["id"]: e for e in json.load(f)["files"]}[source_id]
    d = dt.datetime.fromisoformat(m["retrieved_at_utc"])
    return "%d %s %d" % (d.day, d.strftime("%B"), d.year)


def citations():
    """One entry per source: text for the citation plus its parts."""
    out = []
    for s in SOURCES:
        ed = edition(s["id"])
        text = "%s. %s [data set]%s. %s. Retrieved %s. Licence: %s (%s)." % (
            s["author"], s["title"], (", " + ed) if ed else "", s["url"], accessed(s["id"]), s["licence"], s["licence_url"])
        out.append({"id": s["id"], "text": text, "edition": ed, "accessed": accessed(s["id"]), "changes": s.get("changes", "")})
    return out


def software_citation():
    h = HYDRADB
    return "%s %s, %s. Licence: %s (%s). Used self-hosted for this hackathon entry; not included in this repository." % (
        h["name"], h["version"], h["url"], h["licence"], h["licence_url"])

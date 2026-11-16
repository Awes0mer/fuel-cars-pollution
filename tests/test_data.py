"""Data check: re-read every raw file and confirm hashes, parsing and flags."""

import hashlib
import json
import os

import pytest

from fcp import learn as L
from fcp import parse as P
from fcp.fetch import MANIFEST, ROOT
from fcp.sources import SOURCES


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


MAN = {e["id"]: e for e in load(MANIFEST)["files"]}


def test_every_source_downloaded_and_recorded():
    assert set(MAN) == {s["id"] for s in SOURCES}
    for s in SOURCES:
        m = MAN[s["id"]]
        assert m["url"] == s["url"]
        assert m["http_status"] == 200
        assert m["retrieved_at_utc"].endswith("+00:00")
        assert s["licence"] and s["licence_url"].startswith("https://") and s["licence_evidence"]


@pytest.mark.parametrize("sid", sorted(MAN))
def test_raw_file_hash_and_size(sid):
    m = MAN[sid]
    path = os.path.join(ROOT, m["path"])
    with open(path, "rb") as f:
        body = f.read()
    assert len(body) == m["bytes"]
    assert hashlib.sha256(body).hexdigest() == m["sha256"]


def test_processed_series_reproduce_from_raw_files():
    fresh = {s["id"]: s for s in P.build()}
    stored = {s["id"]: s for s in load(P.PROCESSED)["series"]}
    assert fresh.keys() == stored.keys()
    for sid in fresh:
        assert fresh[sid]["values"] == stored[sid]["values"], sid
        assert fresh[sid]["flags"] == stored[sid]["flags"], sid


def test_spot_values_read_independently():
    import csv

    with open(os.path.join(ROOT, "data/raw/eia_mer_t1105/T11.05.csv"), encoding="utf-8-sig") as f:
        row = next(r for r in csv.DictReader(f) if r["MSN"] == "TEACEUS" and r["YYYYMM"] == "202013")
    stored = {s["id"]: s for s in load(P.PROCESSED)["series"]}
    assert stored["us_transport_co2"]["values"]["2020"] == float(row["Value"])


def test_epa_carried_forward_years_really_repeat_2023():
    stored = {s["id"]: s for s in load(P.PROCESSED)["series"]}
    for sid in ("us_highway_nox", "us_highway_co", "us_highway_voc", "us_highway_pm25"):
        v = stored[sid]["values"]
        for y in P.EPA_CARRIED_FORWARD_YEARS:
            assert v[str(y)] == v["2023"], (sid, y)
            assert stored[sid]["flags"][str(y)] == "carried_forward"


def test_regions_are_never_mixed():
    for s in load(P.PROCESSED)["series"]:
        assert s["region"] in ("US", "World")


def test_flagged_values_never_reach_the_model():
    series = L.load_series()
    ch = L.changes(series)
    for var, sid in L.VAR_SERIES.items():
        for y in series[sid]["flags"]:
            y = int(y)
            assert y not in ch[var] and (y + 1) not in ch[var], (var, y)


def test_missing_years_stay_missing():
    vmt = {s["id"]: s for s in load(P.PROCESSED)["series"]}["us_vmt"]["values"]
    assert "2009" not in vmt  # FHWA VM-203 footnote: data unavailable
    ch = L.changes(L.load_series())
    assert 2009 not in ch["VMT"] and 2010 not in ch["VMT"]


def test_office_files_carry_no_personal_names_and_data_parts_are_unchanged():
    import io
    import re
    import zipfile

    for sid, m in MAN.items():
        if not m["path"].endswith(".xlsx"):
            continue
        with open(os.path.join(ROOT, m["path"]), "rb") as f:
            z = zipfile.ZipFile(io.BytesIO(f.read()))
        from fcp.scrub import author_values

        assert not author_values(z.read("docProps/core.xml")), sid
        if "parts_crc32_as_downloaded" in m:
            for info in z.infolist():
                if info.filename != "docProps/core.xml":
                    assert info.CRC == m["parts_crc32_as_downloaded"][info.filename], (sid, info.filename)
            assert set(z.namelist()) == set(m["parts_crc32_as_downloaded"]), sid


def test_scrubber_handles_namespaces_attributes_and_character_references():
    from fcp.scrub import author_values, clear_authors

    xml = (b'<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
           b'xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:creator xmlns:dc="http://purl.org/dc/elements/1.1/">A&#108;ice &amp; Co</dc:creator>'
           b'<cp:lastModifiedBy>Bob</cp:lastModifiedBy><dc:title>Keep me</dc:title></cp:coreProperties>')
    assert author_values(xml) == ["Alice & Co", "Bob"]
    out = clear_authors(xml)
    assert author_values(out) == [] and b"Keep me" in out and b"Alice" not in out and b"A&#108;ice" not in out


def test_fetch_scrubs_before_storing(tmp_path, monkeypatch):
    import hashlib
    import io
    import pathlib
    import zipfile

    from fcp import fetch
    from fcp.scrub import author_values

    core = (b'<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            b'xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:creator>Some Person</dc:creator></cp:coreProperties>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("docProps/core.xml", core)
        z.writestr("xl/workbook.xml", b"<workbook/>")
    src_file = tmp_path / "in.xlsx"
    src_file.write_bytes(buf.getvalue())
    monkeypatch.setattr(fetch, "RAW", str(tmp_path / "raw"))
    entry = fetch.fetch_one({"id": "t", "url": pathlib.Path(src_file).as_uri(), "filename": "t.xlsx"})
    stored = (tmp_path / "raw" / "t" / "t.xlsx").read_bytes()
    assert author_values(zipfile.ZipFile(io.BytesIO(stored)).read("docProps/core.xml")) == []
    assert entry["sha256"] == hashlib.sha256(stored).hexdigest()
    assert entry["sha256_as_downloaded"] == hashlib.sha256(buf.getvalue()).hexdigest()
    assert not list((tmp_path / "raw" / "t").glob("*.part"))


def test_scrubber_leaves_author_like_text_in_cdata_and_comments():
    from fcp.scrub import author_values, clear_authors

    xml = (b'<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
           b'xmlns:dc="http://purl.org/dc/elements/1.1/">'
           b'<dc:description><![CDATA[<dc:creator>Template</dc:creator>]]></dc:description>'
           b'<!-- <cp:lastModifiedBy>Note</cp:lastModifiedBy> -->'
           b'<dc:creator>Real Person</dc:creator></cp:coreProperties>')
    out = clear_authors(xml)
    assert author_values(out) == []
    assert b"<![CDATA[<dc:creator>Template</dc:creator>]]>" in out and b"<cp:lastModifiedBy>Note</cp:lastModifiedBy>" in out
    assert b"Real Person" not in out


def test_scrubber_namespace_and_unmatched_cdata_cases():
    from fcp.scrub import author_values, clear_authors

    head = (b'<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            b'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:x="urn:other">')
    xml = (head + b'<x:creator>Not an author field</x:creator>'
           b'<dc:description><![CDATA[stray <dc:creator> text]]></dc:description>'
           b'<dc:creator>Real Person</dc:creator><cp:lastModifiedBy>Other Person</cp:lastModifiedBy></cp:coreProperties>')
    out = clear_authors(xml)
    assert author_values(out) == []
    assert b"<x:creator>Not an author field</x:creator>" in out
    assert b"<![CDATA[stray <dc:creator> text]]>" in out
    assert b"Real Person" not in out and b"Other Person" not in out


def _mer_fixture(tmp_path, monkeypatch, release, t_table, t_index):
    """Point cite at a fixed release page and fixed retrieval times (no real files involved)."""
    from fcp import cite

    page = tmp_path / "index.html"
    page.write_text('<span class="label">Release Date:</span> <span class="date">\n %s </span>' % release, encoding="utf-8")
    monkeypatch.setattr(cite, "_raw", lambda sid, name: str(page))
    times = {"eia_mer_t0901": t_table, "eia_mer_index": t_index}
    monkeypatch.setattr(cite, "_retrieved", times.get)
    return cite


def test_mer_edition_only_when_release_page_proves_the_association(tmp_path, monkeypatch):
    import datetime as dt

    utc = dt.timezone.utc
    cite = _mer_fixture(tmp_path, monkeypatch, "October 29, 2026",
                        dt.datetime(2026, 11, 16, 5, 54, tzinfo=utc), dt.datetime(2026, 11, 16, 7, 32, tzinfo=utc))
    assert cite.edition("eia_mer_t0901") == "release of October 29, 2026"  # page read after the table: proven
    cite = _mer_fixture(tmp_path, monkeypatch, "October 29, 2026",
                        dt.datetime(2026, 11, 16, 9, 0, tzinfo=utc), dt.datetime(2026, 11, 16, 7, 32, tzinfo=utc))
    assert cite.edition("eia_mer_t0901") is None  # table read after the page: a release could sit between


def test_scrubber_decodes_character_references_in_namespace_declarations():
    from fcp.scrub import author_values, clear_authors

    xml = (b'<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties">'
           b'<dc:creator xmlns:dc="http://purl.org/dc/elements/1.&#49;/">Alice</dc:creator></cp:coreProperties>')
    assert author_values(xml) == ["Alice"]
    out = clear_authors(xml)
    assert author_values(out) == [] and b"Alice" not in out


def test_mer_edition_withheld_for_same_day_release(tmp_path, monkeypatch):
    import datetime as dt

    utc = dt.timezone.utc
    cite = _mer_fixture(tmp_path, monkeypatch, "October 29, 2026",
                        dt.datetime(2026, 10, 29, 8, 0, tzinfo=utc), dt.datetime(2026, 10, 29, 20, 0, tzinfo=utc))
    assert cite.edition("eia_mer_t0901") is None  # released the same day: the table may predate it

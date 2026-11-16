"""Every declared third-party package has the licence its own metadata states."""

import importlib.metadata as md

import pytest

from fcp.sources import SOFTWARE


def declared_licence(pkg):
    meta = md.metadata(pkg)
    text = " ".join(filter(None, [meta.get("License-Expression"), meta.get("License")]))
    classifiers = " ".join(c for c in (meta.get_all("Classifier") or []) if c.startswith("License"))
    return text + " " + classifiers


@pytest.mark.parametrize("item", [s for s in SOFTWARE if s["package"]], ids=lambda s: s["name"])
def test_licence_matches_package_metadata(item):
    try:
        found = declared_licence(item["package"])
    except md.PackageNotFoundError:
        pytest.skip("%s not installed here" % item["package"])
    assert item["licence"] in found, (item["package"], found)


def test_requirements_cover_every_package():
    with open("requirements.txt", encoding="utf-8") as f:
        req = {line.split("==")[0].strip().lower() for line in f if line.strip()}
    for s in SOFTWARE:
        if s["package"] and s["package"] != "et-xmlfile":  # installed by openpyxl
            assert s["package"].lower() in req, s["package"]

"""Generated files must match the result files; the rule must predate the results."""

import json
import os
import subprocess

from fcp import readme, site
from fcp.fetch import ROOT
from fcp.learn import results_path


def git(*a):
    return subprocess.check_output(["git", *a], cwd=ROOT, text=True).strip()


def test_readme_matches_results():
    with open(readme.README, encoding="utf-8") as f:
        assert f.read() == readme.render(), "run: python -m fcp.readme"


def test_launch_kit_matches_results():
    with open(readme.LAUNCH, encoding="utf-8") as f:
        assert f.read() == readme.render_launch(), "run: python -m fcp.readme"


def test_site_matches_results(tmp_path, monkeypatch):
    monkeypatch.setattr(site, "SITE", str(tmp_path))
    site.build()
    for name in os.listdir(tmp_path):
        with open(tmp_path / name, encoding="utf-8") as f:
            fresh = f.read()
        with open(os.path.join(ROOT, "site", name), encoding="utf-8") as f:
            assert f.read() == fresh, "run: python -m fcp.site (%s)" % name


def test_share_image_exists():
    from PIL import Image

    with Image.open(os.path.join(ROOT, "site", "og.png")) as im:
        assert im.size == (1200, 630)


def test_verdict_follows_rule():
    with open(results_path(), encoding="utf-8") as f:
        r = json.load(f)
    assert r["verdict"] == ("PASS" if all(p["pass"] for p in r["rule"]) else "FAIL")
    assert len(r["rule"]) == 4


def test_preregistration_committed_once_and_before_results():
    import pytest

    if not os.path.exists(os.path.join(ROOT, ".git")):
        pytest.skip("no git history in a plain copy; checked in the repository")
    prereg = git("log", "--format=%H", "--", "PREREGISTRATION.md").splitlines()
    assert len(prereg) == 1, "PREREGISTRATION.md must never be edited after its first commit"
    first_results = git("log", "--diff-filter=A", "--format=%H", "--", "results/learning_results.json").splitlines()
    if os.path.exists(results_path()):
        assert first_results, "results file exists but was never committed: the ordering cannot be verified"
    if first_results:
        # merge-base --is-ancestor exits 0 when prereg is an ancestor of the results commit
        rc = subprocess.call(["git", "merge-base", "--is-ancestor", prereg[0], first_results[-1]], cwd=ROOT)
        assert rc == 0 and prereg[0] != first_results[-1]


def test_holdout_years_not_used_for_tuning():
    with open(results_path(), encoding="utf-8") as f:
        r = json.load(f)
    assert max(r["tuning"]["design_years"]) < min(r["config"]["holdout_years_scored"])


def test_flowchart_data_matches_results():
    import re

    with open(os.path.join(ROOT, "site", "index.html"), encoding="utf-8") as f:
        html = f.read()
    m = re.search(r'<script type="application/json" id="flow-data">(.*?)</script>', html, re.S)
    assert m, "flowchart data block missing"
    data = json.loads(m.group(1).replace("<\\/", "</"))
    with open(results_path(), encoding="utf-8") as f:
        r = json.load(f)
    assert data["weights"] == r["final_weights"]
    assert data["history"] == r["link_weights_by_year"]
    assert [y["year"] for y in data["years"]] == [p["year"] for p in r["per_year"]]
    assert all(y["pred"] == p["graph"] for y, p in zip(data["years"], r["per_year"]))
    with open(os.path.join(ROOT, "site", "flow.js"), encoding="utf-8") as f:
        js = f.read()
    js = js.replace("http://www.w3.org/2000/svg", "")  # SVG namespace name, not a request
    assert "http://" not in js and "https://" not in js, "flow.js must not load anything from another host"


def test_pages_load_nothing_from_other_hosts():
    import glob
    import re

    for path in glob.glob(os.path.join(ROOT, "site", "*.html")) + [os.path.join(ROOT, "site", "style.css")]:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        assert not re.search(r"""\bsrc=["']?(https?:)?//""", text), path
        for tag in re.findall(r"<link\b[^>]*>", text, re.I):
            rel = re.search(r"""\brel=["']?([^"'>\s]+)""", tag, re.I)
            href = re.search(r"""\bhref=["']?([^"'>\s]+)""", tag, re.I)
            if rel and href and rel.group(1).lower() in ("stylesheet", "preload", "modulepreload", "icon"):
                assert not re.match(r"(https?:)?//", href.group(1)), (path, tag)
        assert not re.search(r"""url\(\s*["']?(https?:)?//""", text), path
        assert "@import" not in text, path


def test_site_and_readme_build_from_memory_only_results(tmp_path, monkeypatch):
    """A result file without a HydraDB run (python -m fcp.experiment --memory-only) must still render."""
    with open(results_path(), encoding="utf-8") as f:
        r = json.load(f)
    r["hydradb"] = None
    r["graph_predictions_from"] = "memory"
    for p in r["rule"]:
        if p["part"] == 1:
            p.update(value=None, margin=None, **{"pass": False})
    r["verdict"] = "FAIL"
    fake = tmp_path / "learning_results.json"
    fake.write_text(json.dumps(r), encoding="utf-8")
    monkeypatch.setattr(site, "results_path", lambda: str(fake))
    monkeypatch.setattr(readme, "results_path", lambda: str(fake))
    monkeypatch.setattr(site, "SITE", str(tmp_path / "site"))
    site.build()
    html = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    assert "unavailable (no HydraDB run)" in html and "memory-only run" in html
    text = readme.render()
    assert "unavailable (no HydraDB run)" in text and "No HydraDB run in this result file" in text

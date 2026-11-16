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
    prereg = git("log", "--format=%H", "--", "PREREGISTRATION.md").splitlines()
    assert len(prereg) == 1, "PREREGISTRATION.md must never be edited after its first commit"
    first_results = git("log", "--diff-filter=A", "--format=%H", "--", "results/learning_results.json").splitlines()
    if first_results:
        # merge-base --is-ancestor exits 0 when prereg is an ancestor of the results commit
        rc = subprocess.call(["git", "merge-base", "--is-ancestor", prereg[0], first_results[-1]], cwd=ROOT)
        assert rc == 0 and prereg[0] != first_results[-1]


def test_holdout_years_not_used_for_tuning():
    with open(results_path(), encoding="utf-8") as f:
        r = json.load(f)
    assert max(r["tuning"]["design_years"]) < min(r["config"]["holdout_years_scored"])

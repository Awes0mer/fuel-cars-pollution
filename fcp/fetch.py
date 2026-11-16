"""Download every source file and record URL, retrieval time and SHA-256.

Usage: python -m fcp.fetch            (downloads all, rewrites the manifest)
       python -m fcp.fetch --only ID  (one source)
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import urllib.request

from fcp.sources import SOURCES

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
MANIFEST = os.path.join(ROOT, "data", "manifest.json")
USER_AGENT = "fuel-cars-pollution-data-fetch/1.0 (open-data research script)"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_one(src):
    out_dir = os.path.join(RAW, src["id"])
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, src["filename"])
    req = urllib.request.Request(src["url"], headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = resp.read()
        status = resp.status
        ctype = resp.headers.get("Content-Type", "")
    retrieved = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    with open(path, "wb") as f:
        f.write(body)
    return {
        "id": src["id"],
        "url": src["url"],
        "path": "data/raw/%s/%s" % (src["id"], src["filename"]),
        "retrieved_at_utc": retrieved,
        "http_status": status,
        "content_type": ctype,
        "bytes": len(body),
        "sha256": sha256_file(path),
    }


def load_manifest():
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding="utf-8") as f:
            return json.load(f)
    return {"files": []}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    args = ap.parse_args()
    manifest = load_manifest()
    by = {e["id"]: e for e in manifest.get("files", [])}
    for src in SOURCES:
        if args.only and src["id"] != args.only:
            continue
        try:
            entry = fetch_one(src)
            by[src["id"]] = entry
            print("ok   %-22s %9d bytes  %s" % (src["id"], entry["bytes"], entry["sha256"][:12]))
        except Exception as e:  # report and keep going; a failed file is simply absent
            print("FAIL %-22s %s" % (src["id"], e))
    manifest["files"] = [by[s["id"]] for s in SOURCES if s["id"] in by]
    with open(MANIFEST, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=1)
        f.write("\n")


if __name__ == "__main__":
    main()

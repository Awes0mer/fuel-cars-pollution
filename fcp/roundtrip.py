"""Measure how exactly HydraDB returns the floats it is given.

Writes results/hydradb_float_roundtrip.json. Explains why the parity check is
not bit-identical. Uses a throwaway id range and deletes it afterwards.

Usage: python -m fcp.roundtrip   (HydraDB must be running)
"""

import datetime as dt
import json
import os
import random

from fcp.fetch import ROOT
from fcp.hydra import HydraClient, default_token_path

OUT = os.path.join(ROOT, "results", "hydradb_float_roundtrip.json")
BASE_ID = 9_100_000
N, PER_NODE, SEED = 300, 50, 3


def ulps_apart(a, b):
    import struct

    ia = struct.unpack("<q", struct.pack("<d", a))[0]
    ib = struct.unpack("<q", struct.pack("<d", b))[0]
    return abs(ia - ib)


def main():
    c = HydraClient.from_token_file(default_token_path())
    rng = random.Random(SEED)
    vals = [rng.uniform(-1, 1) * 10 ** rng.uniform(-8, 7) for _ in range(N)]
    mismatches = []
    ids = []
    for i in range(0, N, PER_NODE):
        nid = BASE_ID + i
        ids.append(nid)
        row = {"id": nid}
        for k, v in enumerate(vals[i:i + PER_NODE]):
            row["v%d" % k] = v
        c.upsert_nodes("RoundTrip", [row], [k for k in row if k != "id"])
        got = c.query("MATCH (n {id: $id}) RETURN " + ", ".join("n.v%d AS v%d" % (k, k) for k in range(PER_NODE)), {"id": nid})[0]
        for k in range(PER_NODE):
            a, b = row["v%d" % k], got["v%d" % k]
            if a != b:
                mismatches.append({"sent": repr(a), "returned": repr(b), "ulps": ulps_apart(a, b)})
    c.query("UNWIND $rows AS row MATCH (n {id: row.id}) DETACH DELETE n", {"rows": [{"id": i} for i in ids]})
    out = {
        "generated_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "values_tested": N,
        "seed": SEED,
        "range": "uniform sign, magnitude 10^-8 to 10^7",
        "write_path": "UNWIND $rows AS row MERGE (n {id: row.id}) SET n:RoundTrip, n.v0 = row.v0, ...",
        "mismatches": len(mismatches),
        "max_ulps": max((m["ulps"] for m in mismatches), default=0),
        "examples": mismatches[:5],
    }
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    print("float round trip: %d of %d values changed, max %d ulp" % (out["mismatches"], N, out["max_ulps"]))


if __name__ == "__main__":
    main()

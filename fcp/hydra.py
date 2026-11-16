"""Minimal HTTP client for a self-hosted HydraDB v0.4.0 graph-node (local mode).

Only the documented JSON query API is used: POST /v1/graphs/{graph}/query with a
bearer token, a cell_id, an OpenCypher query and parameters. Cells come back
typed ({"type": ..., "value": ...}); a null cell has no "value" key.
"""

import json
import os
import urllib.error
import urllib.request

DEFAULT_URL = "http://127.0.0.1:8443/v1/graphs/default/query"


class HydraError(RuntimeError):
    pass


class HydraClient:
    def __init__(self, token, url=DEFAULT_URL, cell_id="cell-0", timeout=60):
        self.token = token
        self.url = url
        self.cell_id = cell_id
        self.timeout = timeout
        self.requests = 0

    @classmethod
    def from_token_file(cls, path, **kw):
        with open(path, encoding="utf-8") as f:
            return cls(f.read().strip(), **kw)

    def query(self, cypher, parameters=None):
        body = {"cell_id": self.cell_id, "query": cypher}
        if parameters:
            body["parameters"] = parameters
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            self.url,
            data=data,
            method="POST",
            headers={
                "Authorization": "Bearer " + self.token,
                "Content-Type": "application/json",
                "X-Graph-Namespace": "default",
            },
        )
        self.requests += 1
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                out = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise HydraError("HTTP %s: %s | query=%s" % (e.code, e.read().decode("utf-8", "replace")[:500], cypher)) from None
        if "error" in out:
            raise HydraError("%s | query=%s" % (out["error"], cypher))
        if "rows" not in out:
            raise HydraError("no rows and no error (HTTP 422 shape?) | query=%s" % cypher)
        cols = out.get("columns", [])
        return [{c: cell.get("value") for c, cell in zip(cols, row)} for row in out["rows"]]

    # --- write shapes documented in USING-HYDRADB.md -----------------------

    def upsert_nodes(self, label, rows, props):
        """UNWIND node batch: MERGE by id, then SET label and properties.

        Labels cannot go in the UNWIND pattern; they are SET instead.
        """
        assignments = ", ".join("n.%s = row.%s" % (p, p) for p in props)
        cypher = "UNWIND $rows AS row MERGE (n {id: row.id}) SET n:%s, %s" % (label, assignments)
        for i in range(0, len(rows), 1000):
            self.query(cypher, {"rows": rows[i:i + 1000]})

    def create_edges(self, rel_type, pairs):
        """UNWIND edge batch; deduplicated by (src, dst, type)."""
        rows = [{"src": a, "dst": b} for a, b in pairs]
        cypher = "UNWIND $rows AS row CREATE (a {id: row.src})-[:%s]->(b {id: row.dst})" % rel_type
        for i in range(0, len(rows), 1000):
            self.query(cypher, {"rows": rows[i:i + 1000]})


def default_token_path():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, ".hydradb", "token")

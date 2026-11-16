"""Two stores with one interface: in-memory and HydraDB.

The learner only talks to a store. Running the same learner on both and
comparing predictions is the parity check.

Graph model in the store (HydraDB node ids are non-negative integers):
  Variable nodes   id 1..99         label Variable  {name}
  Link nodes       id 101..199      label Link      {name, src, dst, w}
  Fit nodes        id 201..299      label Fit       {name, target, bias, p_<i>_<j>}
  LinkState nodes  id 1_000_000 + link_id*10_000 + year   label LinkState {link, year, w}
  Prediction nodes id 3_000_000 + target_var*10_000 + year label Prediction {target, year, value}
Edges: (Variable)-[:FEEDS]->(Link)-[:INTO]->(Variable), (Fit)-[:FITS]->(Variable),
       (Link)-[:HISTORY]->(LinkState), (Prediction)-[:OF]->(Variable).
"""


class MemoryStore:

    def __init__(self):
        self.nodes = {}
        self.edges = set()

    def put(self, label, rows):
        for r in rows:
            n = self.nodes.setdefault(r["id"], {"_label": label})
            n["_label"] = label
            n.update(r)

    def edge(self, rel, pairs):
        for a, b in pairs:
            self.edges.add((a, rel, b))

    def get(self, node_id, props):
        n = self.nodes[node_id]
        return {p: n.get(p) for p in props}

    def incoming(self, node_id, rel):
        """Ids of nodes with an edge (x)-[rel]->(node_id), sorted."""
        return sorted(a for (a, r, b) in self.edges if r == rel and b == node_id)

    def set_props(self, node_id, values):
        self.nodes[node_id].update(values)


class HydraStore:

    def __init__(self, client):
        self.c = client

    def put(self, label, rows):
        # One UNWIND batch per distinct property set (fit nodes differ in size).
        groups = {}
        for r in rows:
            groups.setdefault(tuple(k for k in r if k != "id"), []).append(r)
        for props, batch in groups.items():
            self.c.upsert_nodes(label, batch, list(props))

    def edge(self, rel, pairs):
        if pairs:
            self.c.create_edges(rel, pairs)

    def get(self, node_id, props):
        ret = ", ".join("n.%s AS %s" % (p, p) for p in props)
        rows = self.c.query("MATCH (n {id: $id}) RETURN %s" % ret, {"id": node_id})
        if len(rows) != 1:
            raise RuntimeError("expected one node %s, got %d rows" % (node_id, len(rows)))
        return rows[0]

    def incoming(self, node_id, rel):
        rows = self.c.query("MATCH (t {id: $id})<-[:%s]-(s) RETURN s.id AS sid" % rel, {"id": node_id})
        return sorted(int(r["sid"]) for r in rows)

    def set_props(self, node_id, values):
        sets = ", ".join("n.%s = $%s" % (k, k) for k in values)
        params = dict(values)
        params["id"] = node_id
        self.c.query("MATCH (n {id: $id}) SET %s" % sets, params)

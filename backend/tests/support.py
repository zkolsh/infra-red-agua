""" edge   cost  capacity
    A-B      1      10
    B-C      2       5
    A-C      5      10
    C-D      1       3
    B-D      4      10

MST = {A-B, B-C, C-D}, total cost 4. Demands: B=4, C=3, D=2 (total 9); the source A demands 0.
Flow over the MST from A:
    base : A-B carries 9 (util 0.9), B-C carries 5 (saturated), C-D carries 2 -> all demand met
    +10% : C+D need 5.5 through B-C (cap 5)      -> total_flow 9.4, unmet 0.5, B-C saturated
    +30% : demand 11.7, A-B (cap 10) is the cut   -> total_flow 10,  unmet 1.7, A-B saturated
    -50% : demand 4.5                             -> all met
Edges have no ids in the engine: an edge is its two endpoints, so tests compare unordered pairs.

The flow endpoints take final demands. In production they come from GET /demands (the ML model);
here `scaled` fabricates scenario demands, so the scaling lives only in the tests.
"""
from __future__ import annotations

from types import SimpleNamespace as NS

A, B, C, D = 1, 2, 3, 4
SOURCE_ID = A

NODES = [  # layout only: demand is not part of a node
    {"id": A, "lat": -32.950, "lon": -60.65},
    {"id": B, "lat": -32.951, "lon": -60.65},
    {"id": C, "lat": -32.952, "lon": -60.65},
    {"id": D, "lat": -32.953, "lon": -60.65},
]


def _edge(source, target, cost, capacity):
    return {"source": source, "target": target, "construction_cost": cost, "capacity": capacity}


EDGES = [_edge(A, B, 1, 10), _edge(B, C, 2, 5), _edge(A, C, 5, 10), _edge(C, D, 1, 3), _edge(B, D, 4, 10)]
GRAPH = {"nodes": NODES, "edges": EDGES}

DEMANDS = {A: 0, B: 4, C: 3, D: 2}

AB, BC, CD = frozenset((A, B)), frozenset((B, C)), frozenset((C, D))
MST_PAIRS = {AB, BC, CD}
MST_COST = 4


def scaled(demands, growth_pct):
    """Test-only scenario maker: every demand multiplied by (1 + growth_pct/100)."""
    return {vid: d * (1 + growth_pct / 100.0) for vid, d in demands.items()}


def label(growth_pct):
    return f"{growth_pct:+g}%"


def pair(source, target):
    return frozenset((source, target))


def by_pair(rows):
    """{frozenset(source, target): row}"""
    return {pair(r["source"], r["target"]): r for r in rows}


def by_vertex(rows):
    return {r["vertex_id"]: r for r in rows}


def _graph(edges):
    return {"nodes": [NS(**n) for n in NODES], "edges": [NS(**e) for e in edges]}


def mst_req(edges=EDGES, algorithm="kruskal"):
    return NS(**_graph(edges), algorithm=algorithm)


def flow_req(edges=EDGES, demands=DEMANDS, source_id=SOURCE_ID, mst_algorithm="kruskal",
             flow_algorithm="edmonds_karp"):
    return NS(**_graph(edges), demands=demands, source_id=source_id,
              mst_algorithm=mst_algorithm, flow_algorithm=flow_algorithm)


def scenarios_req_with(demand_sets, labels=None, edges=EDGES, source_id=SOURCE_ID, mst_algorithm="kruskal",
                       flow_algorithm="edmonds_karp"):
    labels = labels or [None] * len(demand_sets)
    return NS(
        **_graph(edges), source_id=source_id, mst_algorithm=mst_algorithm, flow_algorithm=flow_algorithm,
        scenarios=[NS(label=lb, demands=d) for lb, d in zip(labels, demand_sets)],
    )


def scenarios_req(growth_pcts, **kw):
    """One scenario per growth value, demands = DEMANDS scaled and labelled like the frontend would."""
    return scenarios_req_with(
        [scaled(DEMANDS, p) for p in growth_pcts], labels=[label(p) for p in growth_pcts], **kw
    )


def validate_req(edges=EDGES):
    return NS(**_graph(edges))

from __future__ import annotations
 
import math
from functools import lru_cache
 
from fastapi import HTTPException
 
from app.schemas.v1.network import Edge, FlowRequest, Graph, MSTRequest, Node
from app.services import graph_service, zone_service
 
NEIGHBORS = 5                  # each zone is a candidate to connect with its N nearest zones
COST_PER_KM = 1.0              # construction cost units per km of pipe
CAPACITY_MARGIN = 0.02         # extra capacity over the base flow
FIRST_PIPE = 20e6              # smallest standard pipe, in gallons/month
PIPE_STEP = 1.5                # each pipe size is PIPE_STEP times the previous one
GROWTH_OPTIONS = (0, 10, 30, 50, 100)
_UNLIMITED = 1e15              # capacity used only to measure the base flow
 
 
def _km(a: dict, b: dict) -> float:
    """Haversine distance between two zones."""
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dlat, dlon = p2 - p1, math.radians(b["lon"] - a["lon"])
    h = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(h))
 
 
def _pipe_size(flow: float) -> float:
    """Smallest standard pipe that carries `flow` plus the margin."""
    needed, size = flow * (1 + CAPACITY_MARGIN), FIRST_PIPE
    while size < needed:
        size *= PIPE_STEP
    return size
 
 
def _central_zone(zones: list[dict]) -> int:
    """The zone with the smallest total distance to all others: the default water source."""
    return min(zones, key=lambda a: sum(_km(a, b) for b in zones))["id"]
 
 
def _candidate_pairs(zones: list[dict], neighbors: int) -> set[tuple[int, int]]:
    pairs = set()
    for a in zones:
        nearest = sorted((z for z in zones if z["id"] != a["id"]), key=lambda b: _km(a, b))[:neighbors]
        pairs.update((min(a["id"], b["id"]), max(a["id"], b["id"])) for b in nearest)
    return pairs
 
 
def _connected_candidates(zones: list[dict], nodes: list[Node]) -> set[tuple[int, int]]:
    """Nearest-neighbour pipes; the neighbourhood grows until every zone can be reached."""
    for k in range(NEIGHBORS, len(zones)):
        pairs = _candidate_pairs(zones, k)
        edges = [Edge(source=a, target=b, construction_cost=0, capacity=1) for a, b in pairs]
        if graph_service.validate(Graph(nodes=nodes, edges=edges))["connected"]:
            return pairs
    return _candidate_pairs(zones, len(zones) - 1)
 
 
def _without_source(demands: dict[int, float], source_id: int) -> dict[int, float]:
    """The source supplies the water; it does not consume it (same convention as the tests)."""
    return {vid: d for vid, d in demands.items() if vid != source_id}
 
 
@lru_cache(maxsize=64)
def build_base(source_id: int | None = None) -> dict:
    zones = zone_service.layout()
    by_id = {z["id"]: z for z in zones}
    if source_id is None:
        source_id = _central_zone(zones)
    elif source_id not in by_id:
        raise HTTPException(status_code=422, detail="The source refers to a vertex that does not exist")
 
    nodes = [Node(id=z["id"], lat=z["lat"], lon=z["lon"]) for z in zones]
    pairs = sorted(_connected_candidates(zones, nodes))
    km = {p: _km(by_id[p[0]], by_id[p[1]]) for p in pairs}
 
    measuring = [Edge(source=a, target=b, construction_cost=km[(a, b)] * COST_PER_KM, capacity=_UNLIMITED)
                 for a, b in pairs]
    base_demands = _without_source(zone_service.project_demands(0.0), source_id)

    # 1. Se incluye source_id en ambas peticiones para forzar la reorientación desde el nuevo origen
    flow = graph_service.compute_flow(
        FlowRequest(nodes=nodes, edges=measuring, source_id=source_id, demands=base_demands))
    
    mst = graph_service.compute_mst(
        MSTRequest(nodes=nodes, edges=measuring, source_id=source_id))  # <--- CAMBIO 1: Se pasa source_id
    
    # Conjunto de aristas pertenecientes al MST recalculado desde source_id
    mst_edges_set = {frozenset((e["source"], e["target"])) for e in mst["edges"]}
    mst_flow = {frozenset((e["source"], e["target"])): e["flow"] for e in flow["edges"]}
 
    # 2. Asignación de capacidades e in_mst basado explícitamente en el nuevo árbol
    edges = []
    for a, b in pairs:
        pair_key = frozenset((a, b))
        carried = mst_flow.get(pair_key)
        
        edges.append({
            "source": a, 
            "target": b,
            "construction_cost": round(km[(a, b)] * COST_PER_KM, 4),
            "capacity": _pipe_size(carried) if carried is not None else FIRST_PIPE,
            "in_mst": pair_key in mst_edges_set,  # <--- CAMBIO 2: Evaluado directamente sobre el MST
        })
 
    demand_now = base_demands
    return {
        "source_id": source_id,
        "mst_total_cost": mst["total_cost"],
        "nodes": [{**z, "demand": demand_now.get(z["id"], 0.0)} for z in zones],
        "edges": edges,
        "scenarios": [
            {"growth_pct": g, "demands": _without_source(zone_service.project_demands(float(g)), source_id)}
            for g in GROWTH_OPTIONS
        ],
    }
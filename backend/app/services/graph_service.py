"""Marshalling layer between C and Python.  Algorithms and validations do not
live here, this module only loads requests into a C graph, calls the native
function, cleans up after, and converts status codes into HTTP errors."""
from __future__ import annotations

import ctypes
from contextlib import contextmanager

from fastapi import HTTPException

from app import graph_engine as ge

# engine status -> (HTTP status, message)
_STATUS = {
    ge.GRAPH_STATUS_INVALID_ARGUMENT: (422, "Invalid argument"),
    ge.GRAPH_STATUS_OUT_OF_MEMORY: (500, "The graph engine ran out of memory"),
    ge.GRAPH_STATUS_VERTEX_NOT_FOUND: (422, "An edge or the source refers to a vertex that does not exist"),
    ge.GRAPH_STATUS_EDGE_NOT_FOUND: (422, "Edge not found"),
    ge.GRAPH_STATUS_EDGE_ALREADY_EXISTS: (422, "There is more than one edge between the same two vertices"),
    ge.GRAPH_STATUS_INVALID_GRAPH: (422, "Invalid graph"),
    ge.GRAPH_STATUS_DISCONNECTED: (422, "The drawn edges do not connect every node"),
    ge.GRAPH_STATUS_INVALID_RESULT: (500, "The graph engine produced an invalid result"),
}


class GraphEngineError(HTTPException):
    def __init__(self, status: int):
        code, detail = _STATUS.get(
            status, (500, f"Graph engine failed with status {status}"))
        super().__init__(status_code=code, detail=detail)
        self.engine_status = status


def _ok(status: int) -> None:
    if status != ge.GRAPH_STATUS_OK:
        raise GraphEngineError(status)


@contextmanager
def _owned(handle, deinit):
    if not handle:  # (NULL)
        raise GraphEngineError(ge.GRAPH_STATUS_OUT_OF_MEMORY)
    try:
        yield handle
    finally:
        deinit(handle)


@contextmanager
def _produced(fn, deinit, handle_type, *args):
    """Call an engine function of the form fn(..., T** out) and own the resulting handle."""
    out = ctypes.POINTER(handle_type)()
    _ok(fn(*args, ctypes.byref(out)))
    with _owned(out, deinit) as handle:
        yield handle


@contextmanager
def _graph(req):
    lib = ge.get_library()
    with _owned(lib.graph_empty(), lib.graph_deinit) as g:
        for n in req.nodes:
            _ok(lib.graph_add_vertex(g, n.id))
        for e in req.edges:
            _ok(lib.graph_add_edge(g, e.source, e.target,
                e.construction_cost, e.capacity))
        yield g


@contextmanager
def _mst_and_tree(lib, g, algorithm: str):
    """The MST result plus the subgraph made of exactly its edges."""
    mst_fn = {"kruskal": lib.graph_kruskal, "prim": lib.graph_prim}[algorithm]
    with _produced(mst_fn, lib.mst_deinit, ge.MstResult, g) as mst:
        edges, count = _fetch(mst, lib.mst_get_edge_count,
                              lib.mst_get_edges, ge.Edge)
        with _produced(lib.graph_subgraph_from_edges, lib.graph_deinit, ge.Graph, g, edges, count) as tree:
            yield mst, tree


def _fetch(handle, count_fn, fill_fn, ctype):
    n = count_fn(handle)
    buf = (ctype * n)()
    return buf, fill_fn(handle, buf, n)


def _rows(handle, count_fn, fill_fn, ctype) -> list[dict]:
    buf, n = _fetch(handle, count_fn, fill_fn, ctype)
    return [{name: getattr(item, name) for name, _ in ctype._fields_} for item in buf[:n]]


def _mst_result(lib, mst) -> dict:
    return {
        "total_cost": lib.mst_get_total_cost(mst),
        "edges": _rows(mst, lib.mst_get_edge_count, lib.mst_get_edges, ge.Edge),
    }


def _flow_result(lib, tree, req, demands: dict[int, float]) -> dict:
    wanted = [(vid, d) for vid, d in demands.items() if d > 0]
    demands = (ge.VertexDemand * len(wanted))(*(ge.VertexDemand(i, d)
                                                for i, d in wanted))
    flow_fn = {"edmonds_karp": lib.graph_edmonds_karp,
               "ford_fulkerson": lib.graph_ford_fulkerson}[req.flow_algorithm]
    with _produced(flow_fn, lib.flow_deinit, ge.FlowResult, tree, req.source_id, demands, len(demands)) as f:
        return {
            "total_flow": lib.flow_get_total(f),
            "total_demand": lib.flow_get_total_demand(f),
            "unmet_demand": lib.flow_get_unmet_demand(f),
            "demand_satisfied": bool(lib.flow_is_demand_satisfied(f)),
            # each edge carries capacity, flow, residual_capacity, utilization and `saturated`
            "edges": _rows(f, lib.flow_get_edge_count, lib.flow_get_edge_flows, ge.EdgeFlow),
            "vertices": _rows(f, lib.flow_get_vertex_count, lib.flow_get_vertex_flows, ge.VertexFlow),
        }


# service API:

def validate(req) -> dict:
    """Live feedback while the user draws: never raises for a bad drawing, reports it instead."""
    lib = ge.get_library()
    try:
        with _graph(req) as g:
            _ok(lib.graph_validate(g))
            return {"valid": True, "connected": bool(lib.graph_is_connected(g)), "error": None}
    except GraphEngineError as exc:
        if exc.status_code >= 500:
            raise
        return {"valid": False, "connected": False, "error": exc.detail}


def compute_mst(req) -> dict:
    lib = ge.get_library()
    source_id = getattr(req, "source_id", None)
    with _graph(req) as g, _produced(lib.graph_prim, lib.mst_deinit, ge.MstResult, g, source_id) as mst:
        return _mst_result(lib, mst)

def compute_flow(req) -> dict:
    lib = ge.get_library()
    with _graph(req) as g, _mst_and_tree(lib, g, req.mst_algorithm) as (_, tree):
        return _flow_result(lib, tree, req, req.demands)


def compute_scenarios(req) -> dict:
    lib = ge.get_library()
    with _graph(req) as g, _mst_and_tree(lib, g, req.mst_algorithm) as (mst, tree):
        return {
            "mst": _mst_result(lib, mst),
            "scenarios": [{**_flow_result(lib, tree, req, s.demands), "label": s.label} for s in req.scenarios],
        }

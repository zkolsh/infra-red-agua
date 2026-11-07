import ctypes
import os
import sys

from app.config import get_settings


def load_graph_library():
    return ctypes.CDLL(str(get_settings().libgraph_engine_loc))


GRAPH_STATUS_OK = 0
GRAPH_STATUS_INVALID_ARGUMENT = 1
GRAPH_STATUS_OUT_OF_MEMORY = 2
GRAPH_STATUS_VERTEX_NOT_FOUND = 3
GRAPH_STATUS_EDGE_NOT_FOUND = 4
GRAPH_STATUS_EDGE_ALREADY_EXISTS = 5
GRAPH_STATUS_INVALID_GRAPH = 6
GRAPH_STATUS_DISCONNECTED = 7
GRAPH_STATUS_INVALID_RESULT = 8

vertex_id_t = ctypes.c_uint32
graph_status_t = ctypes.c_uint32


class Vertex(ctypes.Structure):
    _fields_ = [("id", vertex_id_t)]


class Edge(ctypes.Structure):
    _fields_ = [
        ("source", vertex_id_t),
        ("target", vertex_id_t),
        ("construction_cost", ctypes.c_double),
        ("capacity", ctypes.c_double),
    ]


class VertexDemand(ctypes.Structure):
    _fields_ = [
        ("vertex_id", vertex_id_t),
        ("demand", ctypes.c_double),
    ]


class EdgeFlow(ctypes.Structure):
    _fields_ = [
        ("source", vertex_id_t),
        ("target", vertex_id_t),
        ("capacity", ctypes.c_double),
        ("flow", ctypes.c_double),
        ("residual_capacity", ctypes.c_double),
        ("utilization", ctypes.c_double),
        ("saturated", ctypes.c_bool),
    ]


class VertexFlow(ctypes.Structure):
    _fields_ = [
        ("vertex_id", vertex_id_t),
        ("demand", ctypes.c_double),
        ("delivered", ctypes.c_double),
        ("unmet", ctypes.c_double),
    ]


class Graph(ctypes.Structure):
    pass


class MstResult(ctypes.Structure):
    pass


class FlowResult(ctypes.Structure):
    pass


def bind_functions(lib):
    """Configures argtypes and restypes for all library functions."""

    lib.graph_empty.argtypes = []
    lib.graph_empty.restype = ctypes.POINTER(Graph)

    lib.graph_init_capacity.argtypes = [ctypes.c_size_t, ctypes.c_size_t]
    lib.graph_init_capacity.restype = ctypes.POINTER(Graph)

    lib.graph_deinit.argtypes = [ctypes.POINTER(Graph)]
    lib.graph_deinit.restype = None

    lib.graph_add_vertex.argtypes = [ctypes.POINTER(Graph), vertex_id_t]
    lib.graph_add_vertex.restype = graph_status_t

    lib.graph_add_edge.argtypes = [
        ctypes.POINTER(Graph),
        vertex_id_t,
        vertex_id_t,
        ctypes.c_double,
        ctypes.c_double,
    ]
    lib.graph_add_edge.restype = graph_status_t

    lib.graph_set_edge.argtypes = [
        ctypes.POINTER(Graph),
        vertex_id_t,
        vertex_id_t,
        ctypes.c_double,
        ctypes.c_double,
    ]
    lib.graph_set_edge.restype = graph_status_t

    lib.graph_remove_edge.argtypes = [
        ctypes.POINTER(Graph),
        vertex_id_t,
        vertex_id_t,
    ]
    lib.graph_remove_edge.restype = graph_status_t

    lib.graph_get_vertex_count.argtypes = [ctypes.POINTER(Graph)]
    lib.graph_get_vertex_count.restype = ctypes.c_size_t

    lib.graph_get_edge_count.argtypes = [ctypes.POINTER(Graph)]
    lib.graph_get_edge_count.restype = ctypes.c_size_t

    lib.graph_get_vertex_by_id.argtypes = [
        ctypes.POINTER(Graph),
        vertex_id_t,
        ctypes.POINTER(Vertex),
    ]
    lib.graph_get_vertex_by_id.restype = graph_status_t

    lib.graph_get_edge.argtypes = [
        ctypes.POINTER(Graph),
        vertex_id_t,
        vertex_id_t,
        ctypes.POINTER(Edge),
    ]
    lib.graph_get_edge.restype = graph_status_t

    lib.graph_get_vertices.argtypes = [
        ctypes.POINTER(Graph),
        ctypes.POINTER(Vertex),
        ctypes.c_size_t,
    ]
    lib.graph_get_vertices.restype = ctypes.c_size_t

    lib.graph_get_edges.argtypes = [
        ctypes.POINTER(Graph),
        ctypes.POINTER(Edge),
        ctypes.c_size_t,
    ]
    lib.graph_get_edges.restype = ctypes.c_size_t

    lib.graph_validate.argtypes = [ctypes.POINTER(Graph)]
    lib.graph_validate.restype = graph_status_t

    lib.graph_is_connected.argtypes = [ctypes.POINTER(Graph)]
    lib.graph_is_connected.restype = ctypes.c_bool

    lib.graph_subgraph_from_edges.argtypes = [
        ctypes.POINTER(Graph),
        ctypes.POINTER(Edge),
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.POINTER(Graph)),
    ]
    lib.graph_subgraph_from_edges.restype = graph_status_t

    lib.graph_kruskal.argtypes = [
        ctypes.POINTER(Graph),
        ctypes.POINTER(ctypes.POINTER(MstResult)),
    ]
    lib.graph_kruskal.restype = graph_status_t

    lib.graph_prim.argtypes = [
        ctypes.POINTER(Graph),
        ctypes.POINTER(ctypes.POINTER(MstResult)),
    ]
    lib.graph_prim.restype = graph_status_t

    lib.mst_get_total_cost.argtypes = [ctypes.POINTER(MstResult)]
    lib.mst_get_total_cost.restype = ctypes.c_double

    lib.mst_get_edge_count.argtypes = [ctypes.POINTER(MstResult)]
    lib.mst_get_edge_count.restype = ctypes.c_size_t

    lib.mst_get_edges.argtypes = [
        ctypes.POINTER(MstResult),
        ctypes.POINTER(Edge),
        ctypes.c_size_t,
    ]
    lib.mst_get_edges.restype = ctypes.c_size_t

    lib.mst_deinit.argtypes = [ctypes.POINTER(MstResult)]
    lib.mst_deinit.restype = None

    lib.graph_ford_fulkerson.argtypes = [
        ctypes.POINTER(Graph),
        vertex_id_t,
        ctypes.POINTER(VertexDemand),
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.POINTER(FlowResult)),
    ]
    lib.graph_ford_fulkerson.restype = graph_status_t

    lib.graph_edmonds_karp.argtypes = [
        ctypes.POINTER(Graph),
        vertex_id_t,
        ctypes.POINTER(VertexDemand),
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.POINTER(FlowResult)),
    ]
    lib.graph_edmonds_karp.restype = graph_status_t

    lib.flow_get_total.argtypes = [ctypes.POINTER(FlowResult)]
    lib.flow_get_total.restype = ctypes.c_double

    lib.flow_get_total_demand.argtypes = [ctypes.POINTER(FlowResult)]
    lib.flow_get_total_demand.restype = ctypes.c_double

    lib.flow_get_unmet_demand.argtypes = [ctypes.POINTER(FlowResult)]
    lib.flow_get_unmet_demand.restype = ctypes.c_double

    lib.flow_is_demand_satisfied.argtypes = [ctypes.POINTER(FlowResult)]
    lib.flow_is_demand_satisfied.restype = ctypes.c_bool

    lib.flow_get_edge_count.argtypes = [ctypes.POINTER(FlowResult)]
    lib.flow_get_edge_count.restype = ctypes.c_size_t

    lib.flow_get_edge_flows.argtypes = [
        ctypes.POINTER(FlowResult),
        ctypes.POINTER(EdgeFlow),
        ctypes.c_size_t,
    ]
    lib.flow_get_edge_flows.restype = ctypes.c_size_t

    lib.flow_get_saturated_edge_count.argtypes = [ctypes.POINTER(FlowResult)]
    lib.flow_get_saturated_edge_count.restype = ctypes.c_size_t

    lib.flow_get_saturated_edges.argtypes = [
        ctypes.POINTER(FlowResult),
        ctypes.POINTER(EdgeFlow),
        ctypes.c_size_t,
    ]
    lib.flow_get_saturated_edges.restype = ctypes.c_size_t

    lib.flow_get_vertex_count.argtypes = [ctypes.POINTER(FlowResult)]
    lib.flow_get_vertex_count.restype = ctypes.c_size_t

    lib.flow_get_vertex_flows.argtypes = [
        ctypes.POINTER(FlowResult),
        ctypes.POINTER(VertexFlow),
        ctypes.c_size_t,
    ]
    lib.flow_get_vertex_flows.restype = ctypes.c_size_t

    lib.flow_deinit.argtypes = [ctypes.POINTER(FlowResult)]
    lib.flow_deinit.restype = None


try:
    _lib = load_graph_library()
    bind_functions(_lib)
except Exception:
    _lib = None


def get_library():
    if _lib is None:
        raise RuntimeError("!!! graph_engine could not be loaded")
    return _lib

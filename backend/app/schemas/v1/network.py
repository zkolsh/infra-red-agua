from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

VertexId = Annotated[int, Field(ge=0, le=2**32 - 1)]  # vertex_id_t is a uint32
GrowthPct = Annotated[float, Field(gt=-100)]
MSTAlgorithm = Literal["kruskal", "prim"]
FlowAlgorithm = Literal["edmonds_karp", "ford_fulkerson"]


class Node(BaseModel):
    id: VertexId
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    demand: float = Field(0.0, ge=0)  # FIXME:  ML projection missing


class Edge(BaseModel):
    source: VertexId
    target: VertexId
    construction_cost: float = Field(ge=0)
    capacity: float = Field(gt=0)


class Graph(BaseModel):
    nodes: list[Node] = Field(min_length=1)
    edges: list[Edge] = []


class MSTRequest(Graph):
    algorithm: MSTAlgorithm = "kruskal"


class _FlowParams(BaseModel):
    source_id: VertexId
    mst_algorithm: MSTAlgorithm = "kruskal"
    flow_algorithm: FlowAlgorithm = "edmonds_karp"


class FlowRequest(Graph, _FlowParams):
    growth_pct: GrowthPct = 0.0  # demand growth scenario, e.g. 30 for +30%


class ScenariosRequest(Graph, _FlowParams):
    growth_pcts: list[GrowthPct] = Field(min_length=1, max_length=20)


class EdgeOut(BaseModel):
    source: int
    target: int
    construction_cost: float
    capacity: float


class MSTResponse(BaseModel):
    total_cost: float
    edges: list[EdgeOut]


class EdgeFlow(BaseModel):
    source: int
    target: int
    capacity: float
    flow: float
    residual_capacity: float
    utilization: float
    saturated: bool


class VertexFlow(BaseModel):
    vertex_id: int
    demand: float
    delivered: float
    unmet: float


class FlowResponse(BaseModel):
    growth_pct: float
    total_flow: float
    total_demand: float
    unmet_demand: float
    demand_satisfied: bool
    edges: list[EdgeFlow]  # MST edges only
    vertices: list[VertexFlow]


class ScenariosResponse(BaseModel):
    mst: MSTResponse
    scenarios: list[FlowResponse]


class ValidateResponse(BaseModel):
    valid: bool
    connected: bool
    error: str | None

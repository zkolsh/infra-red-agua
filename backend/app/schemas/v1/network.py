from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

VertexId = Annotated[int, Field(ge=0, le=2**32 - 1)]  # vertex_id_t is a uint32
MSTAlgorithm = Literal["kruskal", "prim"]
FlowAlgorithm = Literal["edmonds_karp", "ford_fulkerson"]

Demands = dict[VertexId, Annotated[float, Field(ge=0)]]


class Node(BaseModel):
    id: VertexId
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class Edge(BaseModel):
    source: VertexId
    target: VertexId
    construction_cost: float = Field(ge=0)
    capacity: float = Field(gt=0)


class Graph(BaseModel):
    nodes: list[Node] = Field(min_length=1)
    edges: list[Edge] = []


class NodeLayout(BaseModel):
    id: int
    zcta:int
    lat: float
    lon: float
    zone_type: str
    population: float


class NodesResponse(BaseModel):
    nodes: list[NodeLayout]


class DemandsResponse(BaseModel):
    demands: Demands


class MSTRequest(Graph):
    algorithm: MSTAlgorithm = "kruskal"
    source_id: VertexId | None = None


class _FlowParams(BaseModel):
    source_id: VertexId
    mst_algorithm: MSTAlgorithm = "kruskal"
    flow_algorithm: FlowAlgorithm = "edmonds_karp"


class FlowRequest(Graph, _FlowParams):
    demands: Demands


class Scenario(BaseModel):
    label: str | None = None
    demands: Demands


class ScenariosRequest(Graph, _FlowParams):
    scenarios: list[Scenario] = Field(min_length=1, max_length=20)


class ScenarioResult(BaseModel):
    label: str | None
    demand_satisfied: bool
    edges: list[EdgeFlow]
    total_flow: float
    total_demand: float
    unmet_demand: float


class ScenariosResponse(BaseModel):
    mst: MSTResponse
    scenarios: list[ScenarioResult]


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
    total_flow: float
    total_demand: float
    unmet_demand: float
    demand_satisfied: bool
    edges: list[EdgeFlow]  # MST edges only
    vertices: list[VertexFlow]


class ValidateResponse(BaseModel):
    valid: bool
    connected: bool
    error: str | None

class BaseNode(NodeLayout):
    demand: float  # base scenario (0 % growth), predicted by the ML model; 0 for the source
 
 
class BaseEdge(EdgeOut):
    in_mst: bool
 
 
class GrowthDemands(BaseModel):
    growth_pct: float
    demands: Demands  # ready to be sent as a Scenario of POST /scenarios
 
 
class BaseNetworkResponse(BaseModel):
    source_id: VertexId
    mst_total_cost: float
    nodes: list[BaseNode]
    edges: list[BaseEdge]  # every candidate pipe; capacities are the fixed design of the network
    scenarios: list[GrowthDemands]
 
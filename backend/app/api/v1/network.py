import pandas as pd
from fastapi import APIRouter, Query

from app.schemas.v1.network import MSTRequest, MSTResponse, FlowRequest, FlowResponse, ScenariosRequest, ScenariosResponse, ValidateResponse, Graph, DemandsResponse, NodesResponse
from app.services import graph_service, zone_service

router = APIRouter(prefix="/network", tags=["network"])


@router.get("/nodes", response_model=NodesResponse)
def nodes(): return {"nodes": zone_service.layout()}


@router.get("/demands", response_model=DemandsResponse)
def demands(growth_pct: float = Query(0.0, ge=-100)
            ): return {"demands": zone_service.project_demands(growth_pct)}


@router.post("/mst", response_model=MSTResponse)
def mst(req: MSTRequest): return graph_service.compute_mst(req)


@router.post("/flow", response_model=FlowResponse)
def flow(req: FlowRequest): return graph_service.compute_flow(req)


@router.post("/validate", response_model=ValidateResponse)
def validate(graph: Graph): return graph_service.validate(graph)


@router.post("/scenarios", response_model=ScenariosResponse)
def scenarios(
    req: ScenariosRequest): return graph_service.compute_scenarios(req)

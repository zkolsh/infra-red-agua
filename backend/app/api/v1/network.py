from typing import Annotated

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.schemas.v1.network import MSTRequest, MSTResponse, FlowRequest, FlowResponse, ScenariosRequest, ScenariosResponse, ValidateResponse, Graph
from app.services import graph_service

router = APIRouter(prefix="/network", tags=["network"])


@router.post("/mst", response_model=MSTResponse)
def mst(req: MSTRequest): return graph_service.compute_mst(req)


@router.post("/flow", response_model=FlowResponse)
def flow(req: FlowRequest): return graph_service.compute_flow(req)


@router.post("/validate", response_model=ValidateResponse)
def validate(graph: Graph): return graph_service.validate(graph)


@router.post("/scenarios", response_model=ScenariosResponse)
def scenarios(
    req: ScenariosRequest): return graph_service.compute_scenarios(req)

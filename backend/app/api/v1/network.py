import pandas as pd
from fastapi import APIRouter

from app.schemas.v1.network import MSTRequest, MSTResponse, FlowRequest, FlowResponse, ScenariosRequest, ScenariosResponse, ValidateResponse, Graph
from app.services import graph_service
from app.ml.predict import predecir_demanda_escenario, RUTA_NODOS

router = APIRouter(prefix="/network", tags=["network"])

_nodos_df = pd.read_csv(RUTA_NODOS)


@router.get("/demands")
def demands(growth_pct: float = 0.0):
    """Devuelve la demanda predicha por ML para cada nodo según el % de crecimiento."""
    serie = predecir_demanda_escenario(_nodos_df, X=growth_pct / 100.0)
    return {"demands": {int(k): round(float(v), 2) for k, v in serie.items()}}


@router.post("/mst", response_model=MSTResponse)
def mst(req: MSTRequest): return graph_service.compute_mst(req)


@router.post("/flow", response_model=FlowResponse)
def flow(req: FlowRequest): return graph_service.compute_flow(req)


@router.post("/validate", response_model=ValidateResponse)
def validate(graph: Graph): return graph_service.validate(graph)


@router.post("/scenarios", response_model=ScenariosResponse)
def scenarios(
    req: ScenariosRequest): return graph_service.compute_scenarios(req)

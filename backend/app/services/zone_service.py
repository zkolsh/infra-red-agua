import pandas as pd
from app.ml.predict import RUTA_NODOS, predecir_demanda_escenario

_NODOS = pd.read_csv(RUTA_NODOS)


def layout() -> list[dict]:
    return [
        {"id": int(r.nodo_id), "lat": float(r.latitud), "lon": float(r.longitud),
         "zone_type": str(r.tipo_zona), "population": float(r.poblacion)}
        for r in _NODOS.itertuples()
    ]


def project_demands(growth_pct: float) -> dict[int, float]:
    serie = predecir_demanda_escenario(_NODOS, X=growth_pct / 100.0)
    return {int(k): round(max(float(v), 0.0), 2) for k, v in serie.items()}

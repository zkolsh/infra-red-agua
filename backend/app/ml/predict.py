
import pandas as pd
import os
import joblib


BASE_DIR = os.path.dirname(os.path.abspath(__file__))                       # .../backend/app/ml
BACKEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))           # .../backend
RUTA_MODELO = os.path.join(BACKEND_DIR, "models", "modelo_consumo.joblib")
RUTA_NODOS = os.path.join(BACKEND_DIR, "data", "nodos_red_agua_austin.csv")


paquete = joblib.load(RUTA_MODELO)
modelo = paquete["modelo"]
scaler = paquete["scaler"]
columnas_modelo = paquete["columnas_modelo"]
columnas_numericas = paquete["columnas_numericas"]

def predecir_demanda_escenario(nodos, X=0.0):
  
    n = nodos.copy()     
 
    n["crecimiento_poblacional_estimado"] = n["crecimiento_poblacional_estimado"] * (1 + X)

 
    n = pd.get_dummies(n, columns=['tipo_zona'])
    n[columnas_numericas] = scaler.transform(n[columnas_numericas])
    demanda = modelo.predict(n[columnas_modelo])
 
    return pd.Series(demanda, index=nodos["nodo_id"], name="demanda")
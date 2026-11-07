import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from pathlib import Path
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
from pathlib import Path

BASE = Path(__file__).resolve().parents[3]   # sube de app/ml/train.py hasta infra-red-agua
df = pd.read_csv(BASE / "backend" / "data" / "train_red_agua_austin.csv")



df = pd.get_dummies(df, columns=['tipo_zona'])


columnas_numericas = ["consumo_historico_mensual","consumo_por_habitante", "poblacion", "crecimiento_poblacional_estimado"]
scaler = StandardScaler()

target = "consumo_futuro_target"

columnas_modelo = ["consumo_historico_mensual","consumo_por_habitante", "poblacion", "crecimiento_poblacional_estimado", "tipo_zona_Multi-Family", "tipo_zona_Residential"]
zonas = df["zcta"].unique()
zonas_train, zonas_test = train_test_split(zonas, test_size=0.25, random_state=42)

train = df[df["zcta"].isin(zonas_train)].copy()
test = df[df["zcta"].isin(zonas_test)].copy()

scaler = StandardScaler()
train[columnas_numericas] = scaler.fit_transform(train[columnas_numericas])
test[columnas_numericas] = scaler.transform(test[columnas_numericas])


X_train, y_train = train[columnas_modelo], train[target]
X_test, y_test = test[columnas_modelo], test[target]

modelo = LinearRegression()
modelo.fit(X_train, y_train)

pred = modelo.predict(X_test)
modelo.score(X_test, y_test)

mae = mean_absolute_error(y_test, pred)
rmse = np.sqrt(mean_squared_error(y_test, pred))

print(f"Score del modelo: {modelo.score(X_test, y_test)}")
print(f"MAE:  {mae/1e6:.2f} M galones/mes")
print(f"RMSE: {rmse/1e6:.2f} M galones/mes")

# Ahora a ver cuanto da en los valores promedio que se usaran en el grafo

BASE = Path(__file__).resolve().parents[3]   # sube de app/ml/train.py hasta infra-red-agua
df = pd.read_csv(BASE / "backend" / "data" / "nodos_red_agua_austin.csv")

df = pd.get_dummies(df, columns=['tipo_zona'])


columnas_numericas = ["consumo_historico_mensual","consumo_por_habitante", "poblacion", "crecimiento_poblacional_estimado"]

target = "consumo_futuro"

columnas_modelo = ["consumo_historico_mensual","consumo_por_habitante", "poblacion", "crecimiento_poblacional_estimado", "tipo_zona_Multi-Family", "tipo_zona_Residential"]
df[columnas_numericas] = scaler.transform(df[columnas_numericas])

pred = modelo.predict(df[columnas_modelo])
modelo.score(df[columnas_modelo], df[target])
mae = mean_absolute_error(df[target], pred)
rmse = np.sqrt(mean_squared_error(df[target], pred))

print(f"Score del modelo en el dataset completo: {modelo.score(df[columnas_modelo], df[target])}")
print(f"MAE:  {mae/1e6:.2f} M galones/mes")
print(f"RMSE: {rmse/1e6:.2f} M galones/mes")

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"   # backend/models
MODELS_DIR.mkdir(exist_ok=True)

joblib.dump({
    "modelo": modelo,
    "scaler": scaler,
    "columnas_modelo": columnas_modelo,
    "columnas_numericas": columnas_numericas,
}, MODELS_DIR / "modelo_consumo.joblib")
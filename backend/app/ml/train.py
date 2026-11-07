import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from pathlib import Path
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
from pathlib import Path
from sklearn.tree import DecisionTreeRegressor, plot_tree
from sklearn.neighbors import KNeighborsRegressor

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

modelo_reg_lineal = LinearRegression()
modelo_reg_lineal.fit(X_train, y_train)

pred = modelo_reg_lineal.predict(X_test)

mae = mean_absolute_error(y_test, pred)
rmse = np.sqrt(mean_squared_error(y_test, pred))

print(f"Con modelo de Regresion Lineal")
print(f"Score del modelo: {modelo_reg_lineal.score(X_test, y_test)}")
print(f"MAE:  {mae/1e6:.2f} M galones/mes")
print(f"RMSE: {rmse/1e6:.2f} M galones/mes")

arbol = DecisionTreeRegressor(max_depth=3,random_state = 0)
arbol.fit(X_train, y_train)

pred_arbol = arbol.predict(X_test)

mae = mean_absolute_error(y_test, pred_arbol)
rmse = np.sqrt(mean_squared_error(y_test, pred_arbol))
print (f"Con modelo arbol de decision con profundidad 3")
print(f"Score del modelo : {arbol.score(X_test, y_test)}")
print(f"MAE:  {mae/1e6:.2f} M galones/mes")
print(f"RMSE: {rmse/1e6:.2f} M galones/mes")

modelo_KNN = KNeighborsRegressor(n_neighbors=42)

modelo_KNN.fit(X_train, y_train)

pred_KNN = modelo_KNN.predict(X_test)
mae = mean_absolute_error(y_test, pred_KNN)
rmse = np.sqrt(mean_squared_error(y_test, pred_KNN))
print (f"Con modelo de KNN con 42 vecinos")
print(f"Score del modelo : {modelo_KNN.score(X_test, y_test)}")
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

pred = modelo_reg_lineal.predict(df[columnas_modelo])
modelo_reg_lineal.score(df[columnas_modelo], df[target])
mae = mean_absolute_error(df[target], pred)
rmse = np.sqrt(mean_squared_error(df[target], pred))

print(f"Score del modelo en el dataset completo:" )
print(f"Regresion Lineal {modelo_reg_lineal.score(df[columnas_modelo], df[target])}")
print(f"MAE:  {mae/1e6:.2f} M galones/mes")
print(f"RMSE: {rmse/1e6:.2f} M galones/mes")

pred_arbol = arbol.predict(df[columnas_modelo])

mae = mean_absolute_error(df[target], pred_arbol)
rmse = np.sqrt(mean_squared_error(df[target], pred_arbol))
print (f"Con modelo arbol de decision con profundidad 3")
print(f"Score del modelo : {arbol.score(df[columnas_modelo], df[target])}")
print(f"MAE:  {mae/1e6:.2f} M galones/mes")
print(f"RMSE: {rmse/1e6:.2f} M galones/mes")

pred_KNN = modelo_KNN.predict(df[columnas_modelo])
mae = mean_absolute_error(df[target], pred_KNN)
rmse = np.sqrt(mean_squared_error(df[target], pred_KNN))
print (f"Con modelo de KNN con 42 vecinos")
print(f"Score del modelo : {modelo_KNN.score(df[columnas_modelo], df[target])}")
print(f"MAE:  {mae/1e6:.2f} M galones/mes")
print(f"RMSE: {rmse/1e6:.2f} M galones/mes")

#Resulto como ganador la regresion lineal, asi que la guardo para usarla en el backend
MODELS_DIR = Path(__file__).resolve().parents[2] / "models"   # backend/models
MODELS_DIR.mkdir(exist_ok=True)

joblib.dump({
    "modelo": modelo_reg_lineal,
    "scaler": scaler,
    "columnas_modelo": columnas_modelo,
    "columnas_numericas": columnas_numericas,
}, MODELS_DIR / "modelo_consumo.joblib")
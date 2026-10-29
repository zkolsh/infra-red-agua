# Diseño de infraestructura de red

## Contexto

Una cooperativa de servicios de agua necesita planificar el tendido de su red en una zona nueva.  Quiere decidir qué conexiones construir para llegar a todos los barrios con el menor costo posible, y verificar si la capacidad de esa red alcanza para la demanda que va a haber en unos años.  La cooperativa los contrata para construir un sistema que proyecte la demanda futura de cada barrio y use esa proyección para diseñar y validar la red.

## Objetivo

Construir un sistema que combine un modelo de regresión (para proyectar la demanda futura de cada zona) con algoritmos de grafos (para diseñar la red de menor costo y verificar si su capacidad alcanza para esa demanda.)

## Datos

Se puede modelar la zona como un grafo no dirigido:

* Nodo: barrio, manzana o edificio con coordenadas.
* Arista: posible tendido entre dos nodos cercanos, con un costo de construcción (por ejemplo, en función de la distancia) y una capacidad máxima de transporte.

El grupo debe generar (o conseguir) un dataset de zonas con, al menos, estas columnas:

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| nodo_id | id | --- |
| latitud | numérico | --- |
| longitud | numérico | --- |
| población | numérico | habitantes o unidades servidas |
| tipo_zona | categórico | residencial / comercial / industrial |
| consumo_historico_mensual | numérico | consumo promedio actual |
| crecimiento_poblacional_estimado | numérico | porcentaje anual proyectado |
| consumo_futuro | numérico | **variable a predecir** |

## Requisitos

1. **Modelo predictivo**:  entrenar un modelo de regresión que, a partir de las características de cada zona, proyecte su consumo futuro (por ejemplo, a 5 años.)  Analizar métricas (MAE, RMSE, R^2) sobre un conjunto de test separado.
1. **Demanda en el grafo**:  usar la demanda proyectada por el modelo como la demanda de cada nodo.
3. **Grafos**:  implementar Kruskal o Prim para calcular la red de menor costo que conecte todos los nodos, y Ford-Fulkerson (o Edmonds-Karp) sobre esa red para verificar si su capacidad cubre la demanda proyectada, identificando las aristas saturadas.

## Frontend

* Visualización de los tendidos posibles, con la red de menor costo resaltada.
* Vista de la red con el flujo sobre cada arista, resaltando las aristas saturadas o cerca de su capacidad máxima.
* Selector de escenario de crecimiento (por ejemplo, +10%, +30%) para ver cómo cambia el diagnóstico de capacidad.

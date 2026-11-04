# Diseño de infraestructura de red

Integrantes del grupo:

* Mateo Delmagro
* Benicio Sánchez Mandato

# Estructura del backend 


## Árbol de carpetas

```
backend/
├── data/
├── models/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── errors.py
│   ├── api/
│   ├── schemas/
│   ├── services/
│   ├── repositories/
│   ├── ml/
│   └── grafos/
├── requirements.txt
└── README.md
```

## Qué hay en cada carpeta

### `data/`
Archivos de datos del proyecto (el CSV de zonas con `nodo_id`, `latitud`, `longitud`, `poblacion`, `tipo_zona`, `consumo_historico_mensual`, `crecimiento_poblacional_estimado`, `consumo_futuro`).


### `models/`
El modelo de regresión ya entrenado y guardado.



### `app/api/`
Es la puerta de entrada de tu backend: donde el frontend “toca la puerta”. Cada archivo define los endpoints (las URLs) y qué hacer cuando llega un pedido.


### `app/schemas/`
Modelos Pydantic de lo que entra y sale de la API (por ejemplo `EscenarioRequest`, `NodoOut`, `AristaOut`, `ResultadoFlujoOut`). Validan el formato de los datos.


### `app/services/`
Es el cerebro del backend. Recibe un pedido ya validado desde api/ y decide en qué orden hay que hacer las cosas para responderlo. Orquesta todo el flujo.

### `app/repositories/`
Es el encargado de ir a buscar los datos a su lugar de origen. Los demás no necesitan saber dónde están guardados ni en qué formato: le piden “dame las zonas” y reciben los datos listos.Lee el CSV de zonas y devuelve los datos crudos.


### `app/ml/`
La parte de Machine Learning.

### `app/grafos/`
En esta carpeta estaran los algoritmos de grafos.
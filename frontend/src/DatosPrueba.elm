module DatosPrueba exposing (aristasPrueba, nodosPrueba, simularCrecimiento)

{-| Módulo separado con datos y simulación de prueba para interactuar sin backend.
-}

import Tipos exposing (Edge, Node)


nodosPrueba : List Node
nodosPrueba =
    [ { id = 1, lat = 30.2906, lon = -97.7397, demanda = 53.2, nombre = "Planta Central (78705)" }
    , { id = 2, lat = 30.2713, lon = -97.7426, demanda = 25.8, nombre = "Downtown (78701)" }
    , { id = 3, lat = 30.2625, lon = -97.7164, demanda = 49.3, nombre = "East Austin (78702)" }
    , { id = 4, lat = 30.2452, lon = -97.7686, demanda = 113.5, nombre = "South Congress (78704)" }
    , { id = 5, lat = 30.2828, lon = -97.7618, demanda = 74.1, nombre = "Clarksville (78703)" }
    , { id = 6, lat = 30.3093, lon = -97.7259, demanda = 30.0, nombre = "Hyde Park (78751)" }
    , { id = 7, lat = 30.3135, lon = -97.7402, demanda = 20.8, nombre = "Rosedale (78756)" }
    ]


aristasPrueba : List Edge
aristasPrueba =
    [ { origen = 1, destino = 2, capacidad = 228.0, flujo = 188.6, saturado = False, flujoBase = 188.6 }
    , { origen = 2, destino = 3, capacidad = 68.0, flujo = 49.3, saturado = False, flujoBase = 49.3 }
    , { origen = 2, destino = 4, capacidad = 152.0, flujo = 113.5, saturado = False, flujoBase = 113.5 }
    , { origen = 1, destino = 5, capacidad = 101.0, flujo = 74.1, saturado = False, flujoBase = 74.1 }
    , { origen = 1, destino = 6, capacidad = 68.0, flujo = 50.8, saturado = False, flujoBase = 50.8 }
    , { origen = 6, destino = 7, capacidad = 30.0, flujo = 20.8, saturado = False, flujoBase = 20.8 }
    ]


simularCrecimiento : Float -> List Edge -> ( List Edge, Float, Float )
simularCrecimiento pct edges =
    let
        factor =
            1.0 + pct / 100.0

        actualizadas =
            List.map
                (\e ->
                    let
                        flujoSimulado =
                            e.flujoBase * factor

                        estaSaturado =
                            flujoSimulado >= e.capacidad
                    in
                    { e
                        | flujo = flujoSimulado
                        , saturado = estaSaturado
                    }
                )
                edges

        saturadas =
            List.filter .saturado actualizadas

        unmet =
            List.map (\e -> e.flujo - e.capacidad) saturadas |> List.sum
    in
    ( actualizadas, 367.0 * factor, unmet )


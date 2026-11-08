module Api exposing (errorTexto, pedirBase, pedirEscenarios)

import Http
import Json.Decode as D
import Json.Encode as E
import Tipos exposing (Arista, Base, Escenario, FlujoArista, Nodo, Resultado)

apiUrl : String
apiUrl =
    "http://127.0.0.1:8000/api/v1/network"


{-| GET /network/base : nodos, tendidos posibles, red de menor costo y capacidades.
-}
pedirBase : (Result Http.Error Base -> msg) -> Maybe Int -> Cmd msg
pedirBase toMsg fuente =
    let
        query =
            case fuente of
                Just id ->
                    "?source_id=" ++ String.fromInt id

                Nothing ->
                    ""
    in
    Http.get
        { url = apiUrl ++ "/base" ++ query
        , expect = Http.expectJson toMsg decodeBase
        }


{-| POST /network/scenarios : un resultado de flujo por cada escenario de crecimiento.
-}
pedirEscenarios : (Result Http.Error (List Resultado) -> msg) -> Base -> Cmd msg
pedirEscenarios toMsg base =
    Http.post
        { url = apiUrl ++ "/scenarios"
        , body = Http.jsonBody (encodeEscenarios base)
        , expect =
            Http.expectJson toMsg
                (decodeResultados (List.map .crecimiento base.escenarios))
        }


errorTexto : Http.Error -> String
errorTexto e =
    case e of
        Http.BadUrl u ->
            "URL inválida: " ++ u

        Http.Timeout ->
            "La API tardó demasiado en responder"

        Http.NetworkError ->
            "No se pudo conectar con la API (¿está corriendo en " ++ apiUrl ++ "? ¿CORS?)"

        Http.BadStatus codigo ->
            "La API respondió con error " ++ String.fromInt codigo

        Http.BadBody detalle ->
            "Respuesta inesperada de la API: " ++ detalle



-- -----------------------------------------------------------------------------
-- JSON ENCODERS / DECODERS
-- -----------------------------------------------------------------------------


encodeEscenarios : Base -> E.Value
encodeEscenarios base =
    E.object
        [ ( "nodes"
          , E.list
                (\n ->
                    E.object
                        [ ( "id", E.int n.id )
                        , ( "lat", E.float n.lat )
                        , ( "lon", E.float n.lon )
                        ]
                )
                base.nodos
          )
        , ( "edges"
          , E.list
                (\a ->
                    E.object
                        [ ( "source", E.int a.origen )
                        , ( "target", E.int a.destino )
                        , ( "construction_cost", E.float a.costo )
                        , ( "capacity", E.float a.capacidad )
                        ]
                )
                base.aristas
          )
        , ( "source_id", E.int base.fuente )
        , ( "scenarios", E.list encodeEscenario base.escenarios )
        ]


encodeEscenario : Escenario -> E.Value
encodeEscenario e =
    E.object
        [ ( "label", E.string ("+" ++ String.fromFloat e.crecimiento ++ " %") )
        , ( "demands"
          , E.object (List.map (\( id, d ) -> ( String.fromInt id, E.float d )) e.demandas)
          )
        ]


decodeBase : D.Decoder Base
decodeBase =
    D.map5 Base
        (D.field "source_id" D.int)
        (D.field "mst_total_cost" D.float)
        (D.field "nodes" (D.list decodeNodo))
        (D.field "edges" (D.list decodeArista))
        (D.field "scenarios" (D.list decodeEscenario))


decodeNodo : D.Decoder Nodo
decodeNodo =
    D.map7 Nodo
        (D.field "id" D.int)
        (D.field "zcta" D.int)
        (D.field "lat" D.float)
        (D.field "lon" D.float)
        (D.field "zone_type" D.string)
        (D.field "population" D.float)
        (D.field "demand" D.float)


decodeArista : D.Decoder Arista
decodeArista =
    D.map6 Arista
        (D.field "source" D.int)
        (D.field "target" D.int)
        (D.field "construction_cost" D.float)
        (D.field "capacity" D.float)
        (D.field "in_mst" D.bool)
        (D.oneOf
            [ D.field "flow" D.float
            , D.succeed 0.0
            ]
        )


decodeEscenario : D.Decoder Escenario
decodeEscenario =
    D.map2 Escenario
        (D.field "growth_pct" D.float)
        (D.field "demands" decodeDemandas)


{-| JSON no admite claves numéricas: la API manda { "12": 3.4e7, ... }
-}
decodeDemandas : D.Decoder (List ( Int, Float ))
decodeDemandas =
    D.keyValuePairs D.float
        |> D.map (List.filterMap (\( k, v ) -> String.toInt k |> Maybe.map (\id -> ( id, v ))))


{-| Los resultados vuelven en el mismo orden en que se mandaron los escenarios,
así que se les asigna el crecimiento de cada uno.
-}
decodeResultados : List Float -> D.Decoder (List Resultado)
decodeResultados crecimientos =
    D.field "scenarios" (D.list decodeResultado)
        |> D.map (List.map2 (\pct r -> { r | crecimiento = pct }) crecimientos)


decodeResultado : D.Decoder Resultado
decodeResultado =
    D.map5 (Resultado 0)
        (D.field "total_demand" D.float)
        (D.field "total_flow" D.float)
        (D.field "unmet_demand" D.float)
        (D.field "demand_satisfied" D.bool)
        (D.field "edges" (D.list decodeFlujo))


decodeFlujo : D.Decoder FlujoArista
decodeFlujo =
    D.map6 FlujoArista
        (D.field "source" D.int)
        (D.field "target" D.int)
        (D.field "capacity" D.float)
        (D.field "flow" D.float)
        (D.field "utilization" D.float)
        (D.field "saturated" D.bool)
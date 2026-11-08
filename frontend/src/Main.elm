module Main exposing (main)

import Browser
import DatosPrueba exposing (aristasPrueba, nodosPrueba, simularCrecimiento)
import Html exposing (Html, div, h1, input, label, p, span, text)
import Html.Attributes exposing (style, type_, value)
import Html.Events exposing (onClick, onInput)
import Http
import Json.Decode as D
import Svg exposing (Svg, circle, g, line, svg, text_)
import Svg.Attributes as SvgAttr
import Tipos exposing (Edge, Node)


-- -----------------------------------------------------------------------------
-- MAIN
-- -----------------------------------------------------------------------------

main : Program () Model Msg
main =
    Browser.element
        { init = init
        , update = update
        , subscriptions = \_ -> Sub.none
        , view = view
        }


-- -----------------------------------------------------------------------------
-- MODEL
-- -----------------------------------------------------------------------------

type alias Model =
    { porcentajeCrecimiento : Float
    , nodoFuente : Int
    , nodos : List Node
    , aristas : List Edge
    , flujoTotal : Float
    , aguaFaltante : Float
    , mensajeEstado : String
    }


init : () -> ( Model, Cmd Msg )
init _ =
    ( { porcentajeCrecimiento = 0.0
      , nodoFuente = 1
      , nodos = nodosPrueba
      , aristas = aristasPrueba
      , flujoTotal = 367.0
      , aguaFaltante = 0.0
      , mensajeEstado = "Grafo de prueba activo (slider hasta 100%)"
      }
    , fetchBaseNetwork
    )


-- -----------------------------------------------------------------------------
-- UPDATE
-- -----------------------------------------------------------------------------

type Msg
    = MovidoSlider String
    | NodoClickeado Int
    | RedInicialObtenida (Result Http.Error (List Node, List Edge))
    | ResultadoFlujoObtenido (Result Http.Error FlowResultData)
    | DemandasObtenidas (Result Http.Error (List ( Int, Float )))


type alias FlowResultData =
    { flujoTotal : Float
    , aguaFaltante : Float
    , aristas : List Edge
    }


update : Msg -> Model -> ( Model, Cmd Msg )
update msg model =
    case msg of
        MovidoSlider val ->
            let
                pct =
                    String.toFloat val |> Maybe.withDefault model.porcentajeCrecimiento

                ( nuevasAristas, tot, faltante ) =
                    simularCrecimiento pct model.aristas
            in
            ( { model
                | porcentajeCrecimiento = pct
                , aristas = nuevasAristas
                , flujoTotal = tot
                , aguaFaltante = faltante
              }
            , fetchDemands pct
            )

        NodoClickeado id ->
            let
                aristasReset =
                    List.map (\e -> { e | flujoBase = e.flujo }) model.aristas

                ( nuevasAristas, tot, faltante ) =
                    simularCrecimiento model.porcentajeCrecimiento aristasReset
            in
            ( { model
                | nodoFuente = id
                , aristas = nuevasAristas
                , flujoTotal = tot
                , aguaFaltante = faltante
                , mensajeEstado = "Nodo fuente: " ++ String.fromInt id ++ " (simulación local)"
              }
            , requestFlowCalculation id model.porcentajeCrecimiento
            )

        RedInicialObtenida result ->
            case result of
                Ok ( nodos, aristas ) ->
                    ( { model | nodos = nodos, aristas = aristas, mensajeEstado = "Red cargada desde la API" }
                    , requestFlowCalculation model.nodoFuente model.porcentajeCrecimiento
                    )

                Err _ ->
                    ( { model | mensajeEstado = "Modo simulación local (API no conectada)" }, Cmd.none )

        ResultadoFlujoObtenido result ->
            case result of
                Ok data ->
                    ( { model
                        | aristas = data.aristas
                        , flujoTotal = data.flujoTotal
                        , aguaFaltante = data.aguaFaltante
                        , mensajeEstado = "Listo"
                      }
                    , Cmd.none
                    )

                Err _ ->
                    ( model, Cmd.none )


        DemandasObtenidas result ->
            case result of
                Ok pares ->
                    let
                        nuevosNodos =
                            List.map
                                (\n ->
                                    case List.filter (\( id, _ ) -> id == n.id) pares |> List.head of
                                        Just ( _, d ) ->
                                            { n | demanda = d }

                                        Nothing ->
                                            n
                                )
                                model.nodos

                        demandaTotal =
                            List.map .demanda nuevosNodos |> List.sum
                    in
                    ( { model
                        | nodos = nuevosNodos
                        , flujoTotal = demandaTotal
                        , mensajeEstado = "Demandas ML actualizadas"
                      }
                    , Cmd.none
                    )

                Err _ ->
                    ( { model | mensajeEstado = "API no conectada — simulación local activa" }, Cmd.none )


-- -----------------------------------------------------------------------------
-- COMANDOS HTTP
-- -----------------------------------------------------------------------------

apiBaseUrl : String
apiBaseUrl =
    "http://localhost:8000/api/v1/network"


fetchBaseNetwork : Cmd Msg
fetchBaseNetwork =
    Http.get
        { url = apiBaseUrl ++ "/base"
        , expect = Http.expectJson RedInicialObtenida decodeBaseNetwork
        }


requestFlowCalculation : Int -> Float -> Cmd Msg
requestFlowCalculation sourceId growth =
    Cmd.none


fetchDemands : Float -> Cmd Msg
fetchDemands pct =
    Http.get
        { url = apiBaseUrl ++ "/demands?growth_pct=" ++ String.fromFloat pct
        , expect = Http.expectJson DemandasObtenidas decodeDemands
        }


-- -----------------------------------------------------------------------------
-- DECODIFICADORES JSON
-- -----------------------------------------------------------------------------


decodeDemands : D.Decoder (List ( Int, Float ))
decodeDemands =
    D.field "demands"
        (D.keyValuePairs D.float
            |> D.map (List.filterMap (\( k, v ) -> String.toInt k |> Maybe.map (\id -> ( id, v ))))
        )

decodeBaseNetwork : D.Decoder ( List Node, List Edge )
decodeBaseNetwork =
    D.map2 Tuple.pair
        (D.field "nodes" (D.list decodeNode))
        (D.field "edges" (D.list decodeEdge))


decodeNode : D.Decoder Node
decodeNode =
    D.map5 Node
        (D.field "id" D.int)
        (D.field "lat" D.float)
        (D.field "lon" D.float)
        (D.field "demand" D.float)
        (D.succeed "Zona")


decodeEdge : D.Decoder Edge
decodeEdge =
    D.map6 Edge
        (D.field "source" D.int)
        (D.field "target" D.int)
        (D.field "capacity" D.float)
        (D.succeed 0.0)
        (D.succeed False)
        (D.succeed 0.0)


-- -----------------------------------------------------------------------------
-- VIEW
-- -----------------------------------------------------------------------------

view : Model -> Html Msg
view model =
    let
        cantSaturadas =
            List.filter .saturado model.aristas |> List.length
    in
    div [ style "display" "flex", style "flex-direction" "column", style "gap" "20px" ]
        [ -- Panel Superior: Título y Controles
          div
            [ style "background" "#1e293b"
            , style "padding" "20px"
            , style "border-radius" "8px"
            , style "display" "flex"
            , style "justify-content" "space-between"
            , style "align-items" "center"
            ]
            [ div []
                [ h1 [ style "margin" "0 0 6px 0", style "font-size" "1.5rem" ]
                    [ text "Diseño de Red de Agua" ]
                , p [ style "margin" "0", style "color" "#94a3b8", style "font-size" "0.9rem" ]
                    [ text ("Planta (Fuente): Nodo " ++ String.fromInt model.nodoFuente ++ " | " ++ model.mensajeEstado) ]
                ]

            -- Medidor de Crecimiento (0% a 100%)
            , div [ style "display" "flex", style "flex-direction" "column", style "align-items" "flex-end", style "gap" "6px" ]
                [ div [ style "display" "flex", style "gap" "10px", style "align-items" "center" ]
                    [ span [ style "color" "#cbd5e1", style "font-size" "0.9rem" ] [ text "Crecimiento:" ]
                    , span
                        [ style "font-size" "1.3rem"
                        , style "font-weight" "bold"
                        , style "color" (if model.porcentajeCrecimiento > 30 then "#ef4444" else "#38bdf8")
                        ]
                        [ text ("+" ++ String.fromFloat model.porcentajeCrecimiento ++ " %") ]
                    ]
                , input
                    [ type_ "range"
                    , Html.Attributes.min "0"
                    , Html.Attributes.max "100" -- Medidor hasta 100%
                    , Html.Attributes.step "5"
                    , value (String.fromFloat model.porcentajeCrecimiento)
                    , onInput MovidoSlider
                    , style "width" "220px"
                    , style "cursor" "pointer"
                    ]
                    []
                ]
            ]

        -- Métricas de Capacidad
        , div
            [ style "display" "grid"
            , style "grid-template-columns" "repeat(3, 1fr)"
            , style "gap" "15px"
            ]
            [ div [ style "background" "#1e293b", style "padding" "15px", style "border-radius" "8px", style "text-align" "center" ]
                [ div [ style "color" "#94a3b8", style "font-size" "0.85rem" ] [ text "Demanda Total" ]
                , div [ style "font-size" "1.4rem", style "font-weight" "bold", style "color" "#38bdf8" ]
                    [ text (String.fromFloat (round2 model.flujoTotal) ++ " M gal/mes") ]
                ]
            , div [ style "background" "#1e293b", style "padding" "15px", style "border-radius" "8px", style "text-align" "center" ]
                [ div [ style "color" "#94a3b8", style "font-size" "0.85rem" ] [ text "Cañerías Saturadas" ]
                , div [ style "font-size" "1.4rem", style "font-weight" "bold", style "color" (if cantSaturadas > 0 then "#ef4444" else "#10b981") ]
                    [ text (String.fromInt cantSaturadas ++ " aristas") ]
                ]
            , div [ style "background" "#1e293b", style "padding" "15px", style "border-radius" "8px", style "text-align" "center" ]
                [ div [ style "color" "#94a3b8", style "font-size" "0.85rem" ] [ text "Déficit de Agua" ]
                , div [ style "font-size" "1.4rem", style "font-weight" "bold", style "color" (if model.aguaFaltante > 0 then "#ef4444" else "#10b981") ]
                    [ text (String.fromFloat (round2 model.aguaFaltante) ++ " M gal/mes") ]
                ]
            ]

        -- Lienzo SVG: El Grafo
        , div
            [ style "background" "#1e293b"
            , style "border-radius" "8px"
            , style "padding" "15px"
            , style "display" "flex"
            , style "flex-direction" "column"
            , style "align-items" "center"
            ]
            [ svg
                [ SvgAttr.viewBox "0 0 900 600"
                , SvgAttr.width "100%"
                , SvgAttr.height "600"
                , style "background" "#0f172a"
                , style "border-radius" "6px"
                ]
                [ g [] (List.map (viewEdge model.nodos) model.aristas)
                , g [] (List.map (viewNode model.nodoFuente) model.nodos)
                ]
            , p [ style "color" "#64748b", style "font-size" "0.85rem", style "margin" "10px 0 0 0" ]
                [ text "Azul: Cañería con capacidad | Rojo: Cañería saturada (100%) | Amarillo: Planta seleccionada" ]
            ]
        ]


round2 : Float -> Float
round2 x =
    toFloat (round (x * 100.0)) / 100.0


viewEdge : List Node -> Edge -> Svg Msg
viewEdge nodos edge =
    let
        maybeSrc =
            List.filter (\n -> n.id == edge.origen) nodos |> List.head

        maybeTgt =
            List.filter (\n -> n.id == edge.destino) nodos |> List.head
    in
    case ( maybeSrc, maybeTgt ) of
        ( Just src, Just tgt ) ->
            let
                x1_ = lonToX src.lon
                y1_ = latToY src.lat
                x2_ = lonToX tgt.lon
                y2_ = latToY tgt.lat
                midX = (x1_ + x2_) / 2.0
                midY = (y1_ + y2_) / 2.0
            in
            g []
                [ line
                    [ SvgAttr.x1 (String.fromFloat x1_)
                    , SvgAttr.y1 (String.fromFloat y1_)
                    , SvgAttr.x2 (String.fromFloat x2_)
                    , SvgAttr.y2 (String.fromFloat y2_)
                    , SvgAttr.stroke (if edge.saturado then "#ef4444" else "#38bdf8")
                    , SvgAttr.strokeWidth (if edge.saturado then "4.5" else "2.5")
                    , SvgAttr.strokeLinecap "round"
                    ]
                    []
                , Svg.text_
                    [ SvgAttr.x (String.fromFloat midX)
                    , SvgAttr.y (String.fromFloat (midY - 6.0))
                    , SvgAttr.fill (if edge.saturado then "#ef4444" else "#94a3b8")
                    , SvgAttr.fontSize "11"
                    , SvgAttr.textAnchor "middle"
                    ]
                    [ Svg.text (String.fromInt (round edge.flujo) ++ " / " ++ String.fromInt (round edge.capacidad) ++ " M") ]
                ]

        _ ->
            g [] []


viewNode : Int -> Node -> Svg Msg
viewNode nodoFuente node =
    let
        isSource =
            node.id == nodoFuente

        x = lonToX node.lon
        y = latToY node.lat
    in
    g [ SvgAttr.cursor "pointer", onClick (NodoClickeado node.id) ]
        [ circle
            [ SvgAttr.cx (String.fromFloat x)
            , SvgAttr.cy (String.fromFloat y)
            , SvgAttr.r (if isSource then "14" else "9")
            , SvgAttr.fill (if isSource then "#f59e0b" else "#10b981")
            , SvgAttr.stroke "#ffffff"
            , SvgAttr.strokeWidth "2"
            ]
            []
        , Svg.text_
            [ SvgAttr.x (String.fromFloat x)
            , SvgAttr.y (String.fromFloat (y + 22.0))
            , SvgAttr.fill "#f8fafc"
            , SvgAttr.fontSize "12"
            , SvgAttr.fontWeight "bold"
            , SvgAttr.textAnchor "middle"
            ]
            [ Svg.text (node.nombre ++ " (" ++ String.fromFloat node.demanda ++ "M)") ]
        ]


-- Proyección de coordenadas al SVG
minLat : Float
minLat = 30.235

maxLat : Float
maxLat = 30.325

minLon : Float
minLon = -97.775

maxLon : Float
maxLon = -97.710

lonToX : Float -> Float
lonToX lon =
    (lon - minLon) / (maxLon - minLon) * 760 + 70

latToY : Float -> Float
latToY lat =
    560 - ((lat - minLat) / (maxLat - minLat) * 480 + 40)

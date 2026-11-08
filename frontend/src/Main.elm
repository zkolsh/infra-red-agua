module Main exposing (main)

import Api exposing (errorTexto, pedirBase, pedirEscenarios)
import Browser
import Html exposing (Html, button, div, h1, p, span, text)
import Html.Attributes exposing (style)
import Html.Events exposing (onClick)
import Http
import Mapa exposing (millones, viewMapa)
import Svg exposing (Svg)
import Svg.Attributes
import Svg.Events
import Tipos exposing (Arista, Base, Nodo, Resultado, Position)


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


type Estado
    = Cargando
    | Listo
    | Fallo String


type alias Model =
    { estado : Estado
    , base : Maybe Base
    , resultados : List Resultado
    , seleccionado : Float
    , zoom : Float
    , panX : Float
    , panY : Float
    , isDragging : Bool
    , dragStart : Position
    , selectedEdge : Maybe Arista
    }


init : () -> ( Model, Cmd Msg )
init _ =
    ( {estado = Cargando
      , base = Nothing
      , resultados = []
      , seleccionado = 0
      , zoom = 1.0
      , panX = 0.0
      , panY = 0.0
      , isDragging = False
      , dragStart = { x = 0, y = 0 }
      , selectedEdge = Nothing}
    , pedirBase BaseObtenida Nothing
    )


-- -----------------------------------------------------------------------------
-- UPDATE
-- -----------------------------------------------------------------------------


type Msg
    = BaseObtenida (Result Http.Error Base)
    | ResultadosObtenidos (Result Http.Error (List Resultado))
    | ElegirCrecimiento Float
    | ElegirFuente Int
    | Reintentar
    | ZoomIn
    | ZoomOut
    | ResetZoom
    | DragStart Position
    | DragMove Position
    | DragEnd
    | SelectEdge (Maybe Arista)

update : Msg -> Model -> ( Model, Cmd Msg )
update msg model =
    case msg of
        BaseObtenida (Ok base) ->
            ( { model | base = Just base, resultados = [], estado = Cargando }
            , pedirEscenarios ResultadosObtenidos base
            )

        BaseObtenida (Err e) ->
            ( { model | estado = Fallo (errorTexto e) }, Cmd.none )

        ResultadosObtenidos (Ok resultados) ->
            let
                existe pct =
                    List.any (\r -> r.crecimiento == pct) resultados

                elegido =
                    if existe model.seleccionado then
                        model.seleccionado

                    else
                        List.head resultados |> Maybe.map .crecimiento |> Maybe.withDefault 0
            in
            ( { model | resultados = resultados, seleccionado = elegido, estado = Listo }
            , Cmd.none
            )

        ResultadosObtenidos (Err e) ->
            ( { model | estado = Fallo (errorTexto e) }, Cmd.none )

        ElegirCrecimiento pct ->
            ( { model | seleccionado = pct }, Cmd.none )

        ElegirFuente id ->
            ( { model | estado = Cargando, resultados = [] }, pedirBase BaseObtenida (Just id) )

        Reintentar ->
            ( { model | estado = Cargando }, pedirBase BaseObtenida (Maybe.map .fuente model.base) )
        
        ZoomIn ->
            ( { model | zoom = Basics.min 3.0 (model.zoom + 0.25) }, Cmd.none )

        ZoomOut ->
            ( { model | zoom = Basics.max 0.5 (model.zoom - 0.25) }, Cmd.none )

        ResetZoom ->
            ( { model | zoom = 1.0, panX = 0.0, panY = 0.0 }, Cmd.none )

        DragStart pos ->
            ( { model | isDragging = True, dragStart = pos }, Cmd.none )

        DragMove pos ->
            if model.isDragging then
                let
                    dx =
                        (pos.x - model.dragStart.x) / model.zoom

                    dy =
                        (pos.y - model.dragStart.y) / model.zoom
                in
                ( { model
                    | panX = model.panX - dx
                    , panY = model.panY - dy
                    , dragStart = pos
                  }
                , Cmd.none
                )

            else
                ( model, Cmd.none )

        DragEnd ->
            ( { model | isDragging = False }, Cmd.none )

        SelectEdge maybeEdge ->
            ( { model | selectedEdge = maybeEdge }, Cmd.none )

getZcta : Maybe Base -> Int -> String
getZcta maybeBase id =
    case maybeBase of
        Just base ->
            base.nodos
                |> List.filter (\n -> n.id == id)
                |> List.head
                |> Maybe.map (\n -> String.fromInt n.zcta)
                |> Maybe.withDefault (String.fromInt id)

        Nothing ->
            String.fromInt id

-- -----------------------------------------------------------------------------
-- VIEW
-- -----------------------------------------------------------------------------


tarjeta : List (Html.Attribute msg)
tarjeta =
    [ style "background" "#1e293b"
    , style "padding" "15px"
    , style "border-radius" "8px"
    ]


view : Model -> Html Msg
view model =
    let
        actual =
            List.filter (\r -> r.crecimiento == model.seleccionado) model.resultados
                |> List.head
    in
    div [ style "display" "flex", style "flex-direction" "row", style "gap" "20px", style "height" "calc(100vh - 40px)" ]
        [ -- Columna Izquierda: Controles y Métricas Apilados Verticalmente
          div [ style "display" "flex", style "flex-direction" "column", style "gap" "15px", style "width" "320px", style "flex-shrink" "0" ]
            [ viewEncabezado model
            , viewSelectorVertical model
            , viewMetricasVertical actual
            ]
        , -- Columna Derecha: Mapa ocupando todo el alto restante
          div [ style "flex-grow" "1", style "height" "100%" ]
            [ viewMapSection model actual ]
        ]


{-| Selector ajustado para columna lateral
-}
viewSelectorVertical : Model -> Html Msg
viewSelectorVertical model =
    let
        opciones =
            case model.base of
                Just b ->
                    List.map .crecimiento b.escenarios

                Nothing ->
                    []

        boton pct =
            let
                activo =
                    pct == model.seleccionado
            in
            button
                [ onClick (ElegirCrecimiento pct)
                , style "cursor" "pointer"
                , style "padding" "8px 12px"
                , style "border-radius" "6px"
                , style "border" "1px solid #38bdf8"
                , style "font-size" "0.9rem"
                , style "font-weight" "bold"
                , style "background" (if activo then "#38bdf8" else "transparent")
                , style "color" (if activo then "#0f172a" else "#38bdf8")
                ]
                [ text ("+" ++ String.fromFloat pct ++ " %") ]
    in
    div (tarjeta ++ [ style "display" "flex", style "flex-direction" "column", style "gap" "10px" ])
        (span [ style "color" "#cbd5e1", style "font-size" "0.9rem" ] [ text "Escenario de crecimiento:" ]
            :: [ div [ style "display" "flex", style "flex-wrap" "wrap", style "gap" "8px" ] (List.map boton opciones) ]
        )


{-| Métricas globales apiladas en columna vertical
-}
viewMetricasVertical : Maybe Resultado -> Html Msg
viewMetricasVertical actual =
    let
        saturadas =
            actual
                |> Maybe.map (\r -> List.length (List.filter .saturada r.aristas))
                |> Maybe.withDefault 0

        demanda =
            actual |> Maybe.map .demandaTotal |> Maybe.withDefault 0

        faltante =
            actual |> Maybe.map .faltante |> Maybe.withDefault 0

        metrica titulo valor color =
            div (tarjeta ++ [ style "text-align" "left", style "padding" "12px 15px" ])
                [ div [ style "color" "#94a3b8", style "font-size" "0.8rem" ] [ text titulo ]
                , div [ style "font-size" "1.2rem", style "font-weight" "bold", style "color" color, style "margin-top" "4px" ] [ text valor ]
                ]
    in
    div [ style "display" "flex", style "flex-direction" "column", style "gap" "10px" ]
        [ metrica "Demanda total predicha" (millones demanda ++ " gal/mes") "#38bdf8"
        , metrica "Cañerías saturadas" (String.fromInt saturadas ++ " aristas") (if saturadas > 0 then "#ef4444" else "#10b981")
        , metrica "Demanda sin cubrir" (millones faltante ++ " gal/mes") (if faltante > 0 then "#ef4444" else "#10b981")
        ]

viewEncabezado : Model -> Html Msg
viewEncabezado model =
    let
        ( mensaje, color ) =
            case model.estado of
                Cargando ->
                    ( "Calculando con el backend…", "#94a3b8" )

                Listo ->
                    ( "Datos cargados desde la API", "#10b981" )

                Fallo e ->
                    ( e, "#ef4444" )

        fuente =
            case model.base of
                Just b ->
                    case List.filter (\n -> n.id == b.fuente) b.nodos |> List.head of
                        Just n ->
                            "Fuente: zona " ++ String.fromInt n.zcta ++ " (clic en otra zona para cambiarla)"

                        Nothing ->
                            ""

                Nothing ->
                    ""
    in
    div (tarjeta ++ [ style "display" "flex", style "justify-content" "space-between", style "align-items" "center" ])
        [ div []
            [ h1 [ style "margin" "0 0 6px 0", style "font-size" "1.5rem" ] [ text "Diseño de Red de Agua" ]
            , p [ style "margin" "0", style "color" "#94a3b8", style "font-size" "0.9rem" ] [ text fuente ]
            ]
        , div [ style "display" "flex", style "gap" "12px", style "align-items" "center" ]
            [ span [ style "color" color, style "font-size" "0.9rem" ] [ text mensaje ]
            , case model.estado of
                Fallo _ ->
                    button [ onClick Reintentar, style "cursor" "pointer" ] [ text "Reintentar" ]

                _ ->
                    text ""
            ]
        ]


viewSelector : Model -> Html Msg
viewSelector model =
    let
        opciones =
            case model.base of
                Just b ->
                    List.map .crecimiento b.escenarios

                Nothing ->
                    []

        boton pct =
            let
                activo =
                    pct == model.seleccionado
            in
            button
                [ onClick (ElegirCrecimiento pct)
                , style "cursor" "pointer"
                , style "padding" "10px 18px"
                , style "border-radius" "6px"
                , style "border" "1px solid #38bdf8"
                , style "font-size" "1rem"
                , style "font-weight" "bold"
                , style "background"
                    (if activo then
                        "#38bdf8"

                     else
                        "transparent"
                    )
                , style "color"
                    (if activo then
                        "#0f172a"

                     else
                        "#38bdf8"
                    )
                ]
                [ text ("+" ++ String.fromFloat pct ++ " %") ]
    in
    div (tarjeta ++ [ style "display" "flex", style "gap" "12px", style "align-items" "center", style "flex-wrap" "wrap" ])
        (span [ style "color" "#cbd5e1" ] [ text "Escenario de crecimiento:" ]
            :: List.map boton opciones
        )


viewMetricas : Maybe Resultado -> Html Msg
viewMetricas actual =
    let
        saturadas =
            actual
                |> Maybe.map (\r -> List.length (List.filter .saturada r.aristas))
                |> Maybe.withDefault 0

        demanda =
            actual |> Maybe.map .demandaTotal |> Maybe.withDefault 0

        faltante =
            actual |> Maybe.map .faltante |> Maybe.withDefault 0

        metrica titulo valor color =
            div (tarjeta ++ [ style "text-align" "center" ])
                [ div [ style "color" "#94a3b8", style "font-size" "0.85rem" ] [ text titulo ]
                , div [ style "font-size" "1.4rem", style "font-weight" "bold", style "color" color ] [ text valor ]
                ]
    in
    div [ style "display" "grid", style "grid-template-columns" "repeat(3, 1fr)", style "gap" "15px" ]
        [ metrica "Demanda total (predicha por el modelo)" (millones demanda ++ " gal/mes") "#38bdf8"
        , metrica "Cañerías saturadas"
            (String.fromInt saturadas ++ " aristas")
            (if saturadas > 0 then
                "#ef4444"

             else
                "#10b981"
            )
        , metrica "Demanda sin cubrir"
            (millones faltante ++ " gal/mes")
            (if faltante > 0 then
                "#ef4444"

             else
                "#10b981"
            )
        ]


viewMapSection : Model -> Maybe Resultado -> Html Msg
viewMapSection model actual =
    Html.div
        [ Html.Attributes.style "position" "relative"
        , Html.Attributes.style "width" "100%"
        , Html.Attributes.style "border" "1px solid #334155"
        , Html.Attributes.style "border-radius" "8px"
        , Html.Attributes.style "overflow" "hidden"
        , Html.Attributes.style "background-color" "#0f172a"
        ]
        [ viewZoomControls model
        , viewEdgeMetricsOverlay model
        , viewMapa ElegirFuente SelectEdge DragStart DragMove DragEnd model.zoom model.panX model.panY model.base actual
        ]

viewZoomControls : Model -> Html Msg
viewZoomControls model =
    Html.div
        [ Html.Attributes.style "position" "absolute"
        , Html.Attributes.style "top" "16px"
        , Html.Attributes.style "left" "16px"
        , Html.Attributes.style "z-index" "10"
        , Html.Attributes.style "display" "flex"
        , Html.Attributes.style "flex-direction" "column"
        , Html.Attributes.style "gap" "6px"
        ]
        [ button
            [ onClick ZoomIn
            , Html.Attributes.style "padding" "8px 12px"
            , Html.Attributes.style "background" "#1e293b"
            , Html.Attributes.style "color" "#f8fafc"
            , Html.Attributes.style "border" "1px solid #475569"
            , Html.Attributes.style "border-radius" "6px"
            , Html.Attributes.style "font-weight" "bold"
            , Html.Attributes.style "cursor" "pointer"
            ]
            [ text "🔍 +" ]
        , button
            [ onClick ZoomOut
            , Html.Attributes.style "padding" "8px 12px"
            , Html.Attributes.style "background" "#1e293b"
            , Html.Attributes.style "color" "#f8fafc"
            , Html.Attributes.style "border" "1px solid #475569"
            , Html.Attributes.style "border-radius" "6px"
            , Html.Attributes.style "font-weight" "bold"
            , Html.Attributes.style "cursor" "pointer"
            ]
            [ text "🔍 -" ]
        , button
            [ onClick ResetZoom
            , Html.Attributes.style "padding" "4px 8px"
            , Html.Attributes.style "background" "#334155"
            , Html.Attributes.style "color" "#cbd5e1"
            , Html.Attributes.style "border" "1px solid #475569"
            , Html.Attributes.style "border-radius" "6px"
            , Html.Attributes.style "font-size" "11px"
            , Html.Attributes.style "cursor" "pointer"
            ]
            [ text "100%" ]
        ]


viewEdgeMetricsOverlay : Model -> Html Msg
viewEdgeMetricsOverlay model =
    case model.selectedEdge of
        Just edge ->
            let
                sat =
                    if edge.capacidad > 0 then
                        round ((edge.flujo / edge.capacidad) * 100.0)

                    else
                        0
            in
            Html.div
                [ Html.Attributes.style "position" "absolute"
                , Html.Attributes.style "top" "16px"
                , Html.Attributes.style "right" "16px"
                , Html.Attributes.style "z-index" "10"
                , Html.Attributes.style "background" "rgba(30, 41, 59, 0.95)"
                , Html.Attributes.style "color" "#f8fafc"
                , Html.Attributes.style "padding" "12px 16px"
                , Html.Attributes.style "border-radius" "8px"
                , Html.Attributes.style "box-shadow" "0 4px 12px rgba(0,0,0,0.4)"
                , Html.Attributes.style "border" "1px solid #475569"
                , Html.Attributes.style "display" "flex"
                , Html.Attributes.style "flex-direction" "column"
                , Html.Attributes.style "gap" "4px"
                , Html.Attributes.style "font-size" "13px"
                , Html.Attributes.style "min-width" "220px"
                ]
                [ Html.div
                    [ Html.Attributes.style "font-weight" "bold"
                    , Html.Attributes.style "margin-bottom" "4px"
                    , Html.Attributes.style "border-bottom" "1px solid #334155"
                    , Html.Attributes.style "padding-bottom" "4px"
                    ]
                    [ text ("Tubería: C.P. " ++ getZcta model.base edge.origen ++ " ➔ C.P. " ++ getZcta model.base edge.destino) ]
                , Html.div [ Html.Attributes.style "color" "#38bdf8" ]
                    [ text ("1. Caudal ocupado: " ++ millones edge.flujo ++ " gal/mes") ]
                , Html.div [ Html.Attributes.style "color" "#94a3b8" ]
                    [ text ("2. Capacidad máxima: " ++ millones edge.capacidad ++ " gal/mes") ]
                , Html.div
                    [ Html.Attributes.style "color"
                        (if sat > 80 then
                            "#ef4444"

                         else
                            "#10b981"
                        )
                    , Html.Attributes.style "font-weight" "bold"
                    ]
                    [ text ("3. Saturación: " ++ String.fromInt sat ++ "%") ]
                ]

        Nothing ->
            Html.div
                [ Html.Attributes.style "position" "absolute"
                , Html.Attributes.style "top" "16px"
                , Html.Attributes.style "right" "16px"
                , Html.Attributes.style "z-index" "10"
                , Html.Attributes.style "background" "rgba(30, 41, 59, 0.85)"
                , Html.Attributes.style "padding" "8px 12px"
                , Html.Attributes.style "border-radius" "6px"
                , Html.Attributes.style "font-size" "12px"
                , Html.Attributes.style "color" "#94a3b8"
                , Html.Attributes.style "border" "1px solid #334155"
                ]
                [ text "Pasá el mouse o hacé clic en una arista para inspeccionarla." ]
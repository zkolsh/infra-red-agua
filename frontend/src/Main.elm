module Main exposing (main)

import Api exposing (errorTexto, pedirBase, pedirEscenarios)
import Browser
import Dict
import Html exposing (Html, button, div, h1, p, span, text)
import Html.Attributes exposing (style)
import Html.Events exposing (onClick)
import Http
import Mapa exposing (decodePosition, millones, proyector, viewMapa, viewNodo)
import ModoManual exposing (viewMapaManual, viewMetricasManual)
import Svg exposing (Svg)
import Svg.Attributes
import Svg.Events
import Tipos exposing (Arista, Base, ModoTab(..), Nodo, Position, Resultado)


main : Program () Model Msg
main =
    Browser.element
        { init = init
        , update = update
        , subscriptions = \_ -> Sub.none
        , view = view
        }


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
    , tabActual : ModoTab
    , selectedEdge : Maybe Arista
    , selectedNode : Maybe Nodo
    , aristasManuales : List ( Int, Int )
    }


init : () -> ( Model, Cmd Msg )
init _ =
    ( { estado = Cargando
      , base = Nothing
      , resultados = []
      , seleccionado = 0
      , zoom = 1.0
      , panX = 0.0
      , panY = 0.0
      , isDragging = False
      , dragStart = { x = 0, y = 0 }
      , selectedEdge = Nothing
      , selectedNode = Nothing
      , tabActual = ModoAutomatico
      , aristasManuales = []
      }
    , pedirBase BaseObtenida Nothing
    )


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
    | SelectNode (Maybe Nodo)
    | CambiarTab ModoTab
    | ToggleAristaManual ( Int, Int )


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
            ( { model | zoom = Basics.min 5.0 (model.zoom + 0.35) }, Cmd.none )

        ZoomOut ->
            ( { model | zoom = Basics.max 0.5 (model.zoom - 0.35) }, Cmd.none )

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
            ( { model | selectedEdge = maybeEdge, selectedNode = if maybeEdge /= Nothing then Nothing else model.selectedNode }, Cmd.none )

        SelectNode maybeNode ->
            ( { model | selectedNode = maybeNode, selectedEdge = if maybeNode /= Nothing then Nothing else model.selectedEdge }, Cmd.none )

        CambiarTab modo ->
            ( { model | tabActual = modo }, Cmd.none )

        ToggleAristaManual ( origen, destino ) ->
            let
                yaExiste =
                    List.any (\( o, d ) -> (o == origen && d == destino) || (o == destino && d == origen)) model.aristasManuales

                nuevas =
                    if yaExiste then
                        List.filter (\( o, d ) -> not ((o == origen && d == destino) || (o == destino && d == origen))) model.aristasManuales

                    else
                        ( origen, destino ) :: model.aristasManuales
            in
            ( { model | aristasManuales = nuevas }, Cmd.none )


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
    div [ style "display" "flex", style "flex-direction" "row", style "gap" "20px", style "height" "calc(100vh - 40px)", style "padding" "20px" ]
        [ div [ style "display" "flex", style "flex-direction" "column", style "gap" "15px", style "width" "320px", style "flex-shrink" "0" ]
            [ viewEncabezado model
            , viewTabsSelector model.tabActual
            , viewSelectorVertical model
            , case model.tabActual of
                ModoAutomatico ->
                    viewMetricasVertical actual

                ModoManual ->
                    viewMetricasManual model.base model.seleccionado model.aristasManuales
            ]
        , div [ style "flex-grow" "1", style "height" "100%" ]
            [ viewMapSection model actual ]
        ]


viewTabsSelector : ModoTab -> Html Msg
viewTabsSelector tabActual =
    div [ style "display" "flex", style "gap" "8px", style "background" "#1e293b", style "padding" "6px", style "border-radius" "8px" ]
        [ button
            [ onClick (CambiarTab ModoAutomatico)
            , style "flex" "1"
            , style "padding" "8px"
            , style "border" "none"
            , style "border-radius" "6px"
            , style "cursor" "pointer"
            , style "font-weight" "bold"
            , style "background"
                (if tabActual == ModoAutomatico then
                    "#38bdf8"

                 else
                    "transparent"
                )
            , style "color"
                (if tabActual == ModoAutomatico then
                    "#0f172a"

                 else
                    "#cbd5e1"
                )
            ]
            [ text "1. Prim (Auto)" ]
        , button
            [ onClick (CambiarTab ModoManual)
            , style "flex" "1"
            , style "padding" "8px"
            , style "border" "none"
            , style "border-radius" "6px"
            , style "cursor" "pointer"
            , style "font-weight" "bold"
            , style "background"
                (if tabActual == ModoManual then
                    "#38bdf8"

                 else
                    "transparent"
                )
            , style "color"
                (if tabActual == ModoManual then
                    "#0f172a"

                 else
                    "#cbd5e1"
                )
            ]
            [ text "2. Diseño Manual" ]
        ]


viewEncabezado : Model -> Html Msg
viewEncabezado model =
    let
        ( mensaje, color ) =
            case model.estado of
                Cargando ->
                    ( "Calculando…", "#94a3b8" )

                Listo ->
                    ( "API Conectada", "#10b981" )

                Fallo e ->
                    ( e, "#ef4444" )
    in
    div (tarjeta ++ [ style "display" "flex", style "flex-direction" "column", style "gap" "4px" ])
        [ h1 [ style "margin" "0", style "font-size" "1.3rem", style "color" "#f8fafc" ] [ text "Diseño Red de Agua" ]
        , span [ style "color" color, style "font-size" "0.85rem" ] [ text mensaje ]
        ]


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
                , style "padding" "6px 10px"
                , style "border-radius" "6px"
                , style "border" "1px solid #38bdf8"
                , style "font-size" "0.85rem"
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
                [ text ("+" ++ String.fromFloat pct ++ "%") ]
    in
    div (tarjeta ++ [ style "display" "flex", style "flex-direction" "column", style "gap" "8px" ])
        (span [ style "color" "#cbd5e1", style "font-size" "0.85rem" ] [ text "Escenario de crecimiento:" ]
            :: [ div [ style "display" "flex", style "flex-wrap" "wrap", style "gap" "6px" ] (List.map boton opciones) ]
        )


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
            div (tarjeta ++ [ style "text-align" "left", style "padding" "10px 12px" ])
                [ div [ style "color" "#94a3b8", style "font-size" "0.75rem" ] [ text titulo ]
                , div [ style "font-size" "1.1rem", style "font-weight" "bold", style "color" color, style "margin-top" "2px" ] [ text valor ]
                ]
    in
    div [ style "display" "flex", style "flex-direction" "column", style "gap" "8px" ]
        [ metrica "Demanda total predicha" (millones demanda ++ " gal/mes") "#38bdf8"
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
    div
        [ style "position" "relative"
        , style "width" "100%"
        , style "height" "100%"
        , style "border" "1px solid #334155"
        , style "border-radius" "8px"
        , style "overflow" "hidden"
        , style "background-color" "#0f172a"
        ]
        [ viewZoomControls model
        , viewInspectorOverlay model
        , case model.tabActual of
            ModoAutomatico ->
                viewMapa ElegirFuente SelectEdge SelectNode DragStart DragMove DragEnd model.zoom model.panX model.panY model.base actual

            ModoManual ->
                viewMapaManualCanvas model
        ]


viewMapaManualCanvas : Model -> Html Msg
viewMapaManualCanvas model =
    case model.base of
        Nothing ->
            div [ style "background" "#1e293b", style "padding" "15px", style "color" "#94a3b8", style "text-align" "center" ]
                [ text "Esperando la red base de la API…" ]

        Just base ->
            let
                posicion =
                    proyector base.nodos

                porId =
                    Dict.fromList (List.map (\n -> ( n.id, n )) base.nodos)

                w =
                    900.0 / model.zoom

                h =
                    620.0 / model.zoom

                x =
                    ((900.0 - w) / 2.0) + model.panX

                y =
                    ((620.0 - h) / 2.0) + model.panY

                viewBoxStr =
                    String.fromFloat x ++ " " ++ String.fromFloat y ++ " " ++ String.fromFloat w ++ " " ++ String.fromFloat h
            in
            div [ style "background" "#1e293b", style "padding" "15px", style "border-radius" "8px", style "display" "flex", style "flex-direction" "column", style "align-items" "center" ]
                [ Svg.svg
                    [ Svg.Attributes.viewBox viewBoxStr
                    , Svg.Attributes.width "100%"
                    , Svg.Attributes.height "620"
                    , style "background" "#0f172a"
                    , style "border-radius" "6px"
                    , style "cursor" "grab"
                    , Svg.Events.on "mousedown" (decodePosition DragStart)
                    , Svg.Events.on "mousemove" (decodePosition DragMove)
                    , Svg.Events.onMouseUp DragEnd
                    , Svg.Events.onMouseOut DragEnd
                    ]
                    [ viewMapaManual ToggleAristaManual SelectEdge model.aristasManuales porId posicion base.aristas model.seleccionado base model.selectedEdge
                    , Svg.g [] (List.map (viewNodo ElegirFuente SelectNode posicion base.fuente model.seleccionado) base.nodos)
                    ]
                , p [ style "color" "#64748b", style "font-size" "0.85rem", style "margin" "10px 0 0 0" ]
                    [ text "Hacé clic en cualquier cañería para activarla/desactivarla. El caudal se distribuye en vivo desde la fuente." ]
                ]


viewZoomControls : Model -> Html Msg
viewZoomControls model =
    div
        [ style "position" "absolute"
        , style "top" "16px"
        , style "left" "16px"
        , style "z-index" "10"
        , style "display" "flex"
        , style "flex-direction" "column"
        , style "gap" "6px"
        ]
        [ button
            [ onClick ZoomIn
            , style "padding" "8px 12px"
            , style "background" "#1e293b"
            , style "color" "#f8fafc"
            , style "border" "1px solid #475569"
            , style "border-radius" "6px"
            , style "font-weight" "bold"
            , style "cursor" "pointer"
            ]
            [ text "🔍 +" ]
        , button
            [ onClick ZoomOut
            , style "padding" "8px 12px"
            , style "background" "#1e293b"
            , style "color" "#f8fafc"
            , style "border" "1px solid #475569"
            , style "border-radius" "6px"
            , style "font-weight" "bold"
            , style "cursor" "pointer"
            ]
            [ text "🔍 -" ]
        , button
            [ onClick ResetZoom
            , style "padding" "4px 8px"
            , style "background" "#334155"
            , style "color" "#cbd5e1"
            , style "border" "1px solid #475569"
            , style "border-radius" "6px"
            , style "font-size" "11px"
            , style "cursor" "pointer"
            ]
            [ text "100%" ]
        ]


viewInspectorOverlay : Model -> Html Msg
viewInspectorOverlay model =
    case model.selectedNode of
        Just node ->
            let
                demandaFutura =
                    node.demanda * (1.0 + (model.seleccionado / 100.0))
            in
            div
                [ style "position" "absolute"
                , style "top" "16px"
                , style "right" "16px"
                , style "z-index" "10"
                , style "background" "rgba(30, 41, 59, 0.95)"
                , style "color" "#f8fafc"
                , style "padding" "12px 16px"
                , style "border-radius" "8px"
                , style "box-shadow" "0 4px 12px rgba(0,0,0,0.4)"
                , style "border" "1px solid #38bdf8"
                , style "display" "flex"
                , style "flex-direction" "column"
                , style "gap" "4px"
                , style "font-size" "13px"
                , style "min-width" "230px"
                ]
                [ div
                    [ style "font-weight" "bold"
                    , style "margin-bottom" "4px"
                    , style "border-bottom" "1px solid #334155"
                    , style "padding-bottom" "4px"
                    , style "color" "#38bdf8"
                    ]
                    [ text ("Vértice: C.P. " ++ String.fromInt node.zcta ++ " (" ++ node.tipoZona ++ ")") ]
                , div [ style "color" "#10b981", style "font-weight" "bold" ]
                    [ text ("• Demanda futura (+" ++ String.fromFloat model.seleccionado ++ "%): " ++ millones demandaFutura ++ " gal/mes") ]
                , div [ style "color" "#94a3b8" ]
                    [ text ("• Demanda base: " ++ millones node.demanda ++ " gal/mes") ]
                , div [ style "color" "#cbd5e1" ]
                    [ text ("• Población estimada: " ++ String.fromInt (round node.poblacion) ++ " hab.") ]
                ]

        Nothing ->
            case model.selectedEdge of
                Just edge ->
                    let
                        sat =
                            if edge.capacidad > 0 then
                                round ((edge.flujo / edge.capacidad) * 100.0)

                            else
                                0
                    in
                    div
                        [ style "position" "absolute"
                        , style "top" "16px"
                        , style "right" "16px"
                        , style "z-index" "10"
                        , style "background" "rgba(30, 41, 59, 0.95)"
                        , style "color" "#f8fafc"
                        , style "padding" "12px 16px"
                        , style "border-radius" "8px"
                        , style "box-shadow" "0 4px 12px rgba(0,0,0,0.4)"
                        , style "border" "1px solid #475569"
                        , style "display" "flex"
                        , style "flex-direction" "column"
                        , style "gap" "4px"
                        , style "font-size" "13px"
                        , style "min-width" "230px"
                        ]
                        [ div
                            [ style "font-weight" "bold"
                            , style "margin-bottom" "4px"
                            , style "border-bottom" "1px solid #334155"
                            , style "padding-bottom" "4px"
                            ]
                            [ text ("Tubería: C.P. " ++ getZcta model.base edge.origen ++ " ➔ C.P. " ++ getZcta model.base edge.destino) ]
                        , div [ style "color" "#38bdf8" ]
                            [ text ("1. Caudal ocupado: " ++ millones edge.flujo ++ " gal/mes") ]
                        , div [ style "color" "#94a3b8" ]
                            [ text ("2. Capacidad máxima: " ++ millones edge.capacidad ++ " gal/mes") ]
                        , div
                            [ style "color"
                                (if sat > 80 then
                                    "#ef4444"

                                 else
                                    "#10b981"
                                )
                            , style "font-weight" "bold"
                            ]
                            [ text ("3. Saturación: " ++ String.fromInt sat ++ "%") ]
                        ]

                Nothing ->
                    div
                        [ style "position" "absolute"
                        , style "top" "16px"
                        , style "right" "16px"
                        , style "z-index" "10"
                        , style "background" "rgba(30, 41, 59, 0.85)"
                        , style "padding" "8px 12px"
                        , style "border-radius" "6px"
                        , style "font-size" "12px"
                        , style "color" "#94a3b8"
                        , style "border" "1px solid #334155"
                        ]
                        [ text "Pasá el mouse sobre un nodo o tubería para inspeccionar." ]
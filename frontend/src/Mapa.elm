module Mapa exposing (decodePosition, millones, proyector, viewMapa, viewNodo)

import Dict exposing (Dict)
import Html exposing (Html, div, p, text)
import Html.Attributes exposing (style)
import Html.Events exposing (onClick)
import Json.Decode as Decode
import Svg exposing (Svg, circle, g, line, svg)
import Svg.Attributes as SvgAttr
import Svg.Events as SvgEvents
import Tipos exposing (Arista, Base, FlujoArista, Nodo, Position, Resultado)


tarjeta : List (Html.Attribute msg)
tarjeta =
    [ style "background" "#1e293b"
    , style "padding" "15px"
    , style "border-radius" "8px"
    ]


viewMapa : (Int -> msg) -> (Maybe Arista -> msg) -> (Maybe Nodo -> msg) -> (Position -> msg) -> (Position -> msg) -> msg -> Float -> Float -> Float -> Maybe Base -> Maybe Resultado -> Html msg
viewMapa onElegirFuente onSelectEdge onSelectNode onDragStart onDragMove onDragEnd zoom panX panY maybeBase actual =
    case maybeBase of
        Nothing ->
            div (tarjeta ++ [ style "color" "#94a3b8", style "text-align" "center" ])
                [ text "Esperando la red base de la API…" ]

        Just base ->
            let
                posicion =
                    proyector base.nodos

                porId =
                    Dict.fromList (List.map (\n -> ( n.id, n )) base.nodos)

                flujos =
                    actual |> Maybe.map .aristas |> Maybe.withDefault []

                posibles =
                    List.filter (\a -> not a.enMst) base.aristas

                w =
                    900.0 / zoom

                h =
                    620.0 / zoom

                x =
                    ((900.0 - w) / 2.0) + panX

                y =
                    ((620.0 - h) / 2.0) + panY

                viewBoxStr =
                    String.fromFloat x ++ " " ++ String.fromFloat y ++ " " ++ String.fromFloat w ++ " " ++ String.fromFloat h

                pct =
                    actual |> Maybe.map .crecimiento |> Maybe.withDefault 0.0
            in
            div (tarjeta ++ [ style "display" "flex", style "flex-direction" "column", style "align-items" "center" ])
                [ svg
                    [ SvgAttr.viewBox viewBoxStr
                    , SvgAttr.width "100%"
                    , SvgAttr.height "620"
                    , style "background" "#0f172a"
                    , style "border-radius" "6px"
                    , style "cursor" "grab"
                    , SvgEvents.on "mousedown" (decodePosition onDragStart)
                    , SvgEvents.on "mousemove" (decodePosition onDragMove)
                    , SvgEvents.onMouseUp onDragEnd
                    , SvgEvents.onMouseOut onDragEnd
                    ]
                    [ g [] (List.filterMap (viewPosible onSelectEdge porId posicion) posibles)
                    , g [] (List.filterMap (viewFlujo onSelectEdge porId posicion) flujos)
                    , g [] (List.map (viewNodo onElegirFuente onSelectNode posicion base.fuente pct) base.nodos)
                    ]
                , p [ style "color" "#64748b", style "font-size" "0.85rem", style "margin" "10px 0 0 0" ]
                    [ text "Gris punteado: tendido posible | Azul: red de menor costo | Naranja: uso ≥ 80 % | Rojo: saturada | Amarillo: fuente" ]
                ]


flujoToArista : FlujoArista -> Arista
flujoToArista f =
    { origen = f.origen
    , destino = f.destino
    , costo = 0.0
    , capacidad = f.capacidad
    , enMst = True
    , flujo = f.flujo
    }


viewPosible : (Maybe Arista -> msg) -> Dict Int Nodo -> (Nodo -> ( Float, Float )) -> Arista -> Maybe (Svg msg)
viewPosible onSelectEdge porId posicion a =
    Maybe.map2
        (\o d ->
            let
                ( x1, y1 ) =
                    posicion o

                ( x2, y2 ) =
                    posicion d
            in
            line
                [ SvgAttr.x1 (String.fromFloat x1)
                , SvgAttr.y1 (String.fromFloat y1)
                , SvgAttr.x2 (String.fromFloat x2)
                , SvgAttr.y2 (String.fromFloat y2)
                , SvgAttr.stroke "#334155"
                , SvgAttr.strokeWidth "1.5"
                , SvgAttr.strokeDasharray "4 4"
                , SvgAttr.cursor "pointer"
                , SvgEvents.onMouseOver (onSelectEdge (Just a))
                , SvgEvents.onMouseOut (onSelectEdge Nothing)
                , SvgEvents.onClick (onSelectEdge (Just a))
                ]
                []
        )
        (Dict.get a.origen porId)
        (Dict.get a.destino porId)


viewFlujo : (Maybe Arista -> msg) -> Dict Int Nodo -> (Nodo -> ( Float, Float )) -> FlujoArista -> Maybe (Svg msg)
viewFlujo onSelectEdge porId posicion f =
    Maybe.map2
        (\o d ->
            let
                ( x1, y1 ) =
                    posicion o

                ( x2, y2 ) =
                    posicion d

                color =
                    if f.saturada then
                        "#ef4444"

                    else if f.utilizacion >= 0.8 then
                        "#f59e0b"

                    else
                        "#38bdf8"

                detalle =
                    millones f.flujo ++ " / " ++ millones f.capacidad ++ " gal/mes (" ++ String.fromInt (round (f.utilizacion * 100)) ++ " %)"

                aristaEquiv =
                    flujoToArista f
            in
            g []
                [ line
                    [ SvgAttr.x1 (String.fromFloat x1)
                    , SvgAttr.y1 (String.fromFloat y1)
                    , SvgAttr.x2 (String.fromFloat x2)
                    , SvgAttr.y2 (String.fromFloat y2)
                    , SvgAttr.stroke color
                    , SvgAttr.strokeWidth (String.fromFloat (2 + 4 * clamp 0 1 f.utilizacion))
                    , SvgAttr.strokeLinecap "round"
                    , SvgAttr.cursor "pointer"
                    , SvgEvents.onMouseOver (onSelectEdge (Just aristaEquiv))
                    , SvgEvents.onMouseOut (onSelectEdge Nothing)
                    , SvgEvents.onClick (onSelectEdge (Just aristaEquiv))
                    ]
                    [ Svg.title [] [ Svg.text (String.fromInt o.zcta ++ " – " ++ String.fromInt d.zcta ++ ": " ++ detalle) ] ]
                , if f.saturada then
                    Svg.text_
                        [ SvgAttr.x (String.fromFloat ((x1 + x2) / 2))
                        , SvgAttr.y (String.fromFloat ((y1 + y2) / 2 - 7))
                        , SvgAttr.fill "#ef4444"
                        , SvgAttr.fontSize "11"
                        , SvgAttr.fontWeight "bold"
                        , SvgAttr.textAnchor "middle"
                        ]
                        [ Svg.text (millones f.flujo ++ " / " ++ millones f.capacidad) ]

                  else
                    text ""
                ]
        )
        (Dict.get f.origen porId)
        (Dict.get f.destino porId)


viewNodo : (Int -> msg) -> (Maybe Nodo -> msg) -> (Nodo -> ( Float, Float )) -> Int -> Float -> Nodo -> Svg msg
viewNodo onElegirFuente onSelectNode posicion fuente incrementoPct n =
    let
        ( x, y ) =
            posicion n

        esFuente =
            n.id == fuente

        demandaEscenario =
            n.demanda * (1.0 + (incrementoPct / 100.0))
    in
    g
        [ SvgAttr.cursor "pointer"
        , onClick (onElegirFuente n.id)
        , SvgEvents.onMouseOver (onSelectNode (Just n))
        , SvgEvents.onMouseOut (onSelectNode Nothing)
        ]
        [ circle
            [ SvgAttr.cx (String.fromFloat x)
            , SvgAttr.cy (String.fromFloat y)
            , SvgAttr.r
                (if esFuente then
                    "11"

                 else
                    "7"
                )
            , SvgAttr.fill
                (if esFuente then
                    "#f59e0b"

                 else
                    "#10b981"
                )
            , SvgAttr.stroke "#ffffff"
            , SvgAttr.strokeWidth "1.5"
            ]
            [ Svg.title []
                [ Svg.text
                    ("Zona C.P. "
                        ++ String.fromInt n.zcta
                        ++ " ("
                        ++ n.tipoZona
                        ++ ")\n• Población estimada: "
                        ++ String.fromInt (round n.poblacion)
                        ++ " hab.\n• Demanda proyectada (+"
                        ++ String.fromFloat incrementoPct
                        ++ "%): "
                        ++ millones demandaEscenario
                        ++ " gal/mes"
                    )
                ]
            ]
        , Svg.text_
            [ SvgAttr.x (String.fromFloat x)
            , SvgAttr.y (String.fromFloat (y + 19))
            , SvgAttr.fill "#cbd5e1"
            , SvgAttr.fontSize "10"
            , SvgAttr.textAnchor "middle"
            , SvgAttr.pointerEvents "none"
            ]
            [ Svg.text (String.fromInt n.zcta) ]
        ]


millones : Float -> String
millones x =
    String.fromFloat (toFloat (round (x / 1.0e5)) / 10) ++ " M"


proyector : List Nodo -> (Nodo -> ( Float, Float ))
proyector nodos =
    let
        lats =
            List.map .lat nodos

        lons =
            List.map .lon nodos

        minLat =
            List.minimum lats |> Maybe.withDefault 0

        maxLat =
            List.maximum lats |> Maybe.withDefault 1

        minLon =
            List.minimum lons |> Maybe.withDefault 0

        maxLon =
            List.maximum lons |> Maybe.withDefault 1

        ancho =
            900

        alto =
            620

        margen =
            55

        factorLon =
            cos (degrees ((minLat + maxLat) / 2))

        rangoX =
            max 1.0e-9 ((maxLon - minLon) * factorLon)

        rangoY =
            max 1.0e-9 (maxLat - minLat)

        escala =
            min ((ancho - 2 * margen) / rangoX) ((alto - 2 * margen) / rangoY)

        sobranteX =
            (ancho - 2 * margen) - rangoX * escala

        sobranteY =
            (alto - 2 * margen) - rangoY * escala
    in
    \n ->
        ( margen + sobranteX / 2 + (n.lon - minLon) * factorLon * escala
        , alto - margen - sobranteY / 2 - (n.lat - minLat) * escala
        )


decodePosition : (Position -> msg) -> Decode.Decoder msg
decodePosition tag =
    Decode.map2 Position
        (Decode.field "pageX" Decode.float)
        (Decode.field "pageY" Decode.float)
        |> Decode.map tag
module Mapa exposing (millones, viewMapa)

import Dict exposing (Dict)
import Html exposing (Html, div, p, text)
import Html.Attributes exposing (style)
import Html.Events exposing (onClick)
import Svg exposing (Svg, circle, g, line, svg)
import Svg.Attributes as SvgAttr
import Tipos exposing (Arista, Base, FlujoArista, Nodo, Resultado)


tarjeta : List (Html.Attribute msg)
tarjeta =
    [ style "background" "#1e293b"
    , style "padding" "15px"
    , style "border-radius" "8px"
    ]


viewMapa : (Int -> msg) -> Maybe Base -> Maybe Resultado -> Html msg
viewMapa onElegirFuente maybeBase actual =
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
                    actual
                        |> Maybe.map .aristas
                        |> Maybe.withDefault []

                posibles =
                    List.filter (\a -> not a.enMst) base.aristas
            in
            div (tarjeta ++ [ style "display" "flex", style "flex-direction" "column", style "align-items" "center" ])
                [ svg
                    [ SvgAttr.viewBox "0 0 900 620"
                    , SvgAttr.width "100%"
                    , SvgAttr.height "620"
                    , style "background" "#0f172a"
                    , style "border-radius" "6px"
                    ]
                    [ g [] (List.filterMap (viewPosible porId posicion) posibles)
                    , g [] (List.filterMap (viewFlujo porId posicion) flujos)
                    , g [] (List.map (viewNodo onElegirFuente posicion base.fuente) base.nodos)
                    ]
                , p [ style "color" "#64748b", style "font-size" "0.85rem", style "margin" "10px 0 0 0" ]
                    [ text "Gris punteado: tendido posible | Azul: red de menor costo | Naranja: uso ≥ 80 % | Rojo: saturada | Amarillo: fuente" ]
                ]


{-| Tendido posible que la red de menor costo no eligió.
-}
viewPosible : Dict Int Nodo -> (Nodo -> ( Float, Float )) -> Arista -> Maybe (Svg msg)
viewPosible porId posicion a =
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
                , SvgAttr.strokeWidth "1"
                , SvgAttr.strokeDasharray "4 4"
                ]
                []
        )
        (Dict.get a.origen porId)
        (Dict.get a.destino porId)


{-| Arista de la red de menor costo con su flujo en el escenario elegido.
-}
viewFlujo : Dict Int Nodo -> (Nodo -> ( Float, Float )) -> FlujoArista -> Maybe (Svg msg)
viewFlujo porId posicion f =
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


viewNodo : (Int -> msg) -> (Nodo -> ( Float, Float )) -> Int -> Nodo -> Svg msg
viewNodo onElegirFuente posicion fuente n =
    let
        ( x, y ) =
            posicion n

        esFuente =
            n.id == fuente
    in
    g [ SvgAttr.cursor "pointer", onClick (onElegirFuente n.id) ]
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
                    (String.fromInt n.zcta
                        ++ " ("
                        ++ n.tipoZona
                        ++ ") – población "
                        ++ String.fromInt (round n.poblacion)
                        ++ " – demanda base "
                        ++ millones n.demanda
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
            ]
            [ Svg.text (String.fromInt n.zcta) ]
        ]


{-| 24045015 -> "24 M" (la API trabaja en galones por mes).
-}
millones : Float -> String
millones x =
    String.fromFloat (toFloat (round (x / 1.0e5)) / 10) ++ " M"


{-| Proyecta lat/lon al lienzo SVG a partir de los límites de los propios nodos,
conservando la proporción (un grado de longitud mide menos que uno de latitud).
-}
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
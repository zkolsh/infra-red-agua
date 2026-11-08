module ModoManual exposing (calcularFlujosManual, viewMapaManual, viewMetricasManual)

import Dict exposing (Dict)
import Html exposing (Html, div, text)
import Html.Attributes exposing (style)
import Html.Events exposing (custom)
import Json.Decode as Decode
import Mapa exposing (millones)
import Set exposing (Set)
import Svg exposing (Svg, g, line)
import Svg.Attributes as SvgAttr
import Svg.Events as SvgEvents
import Tipos exposing (Arista, Base, FlujoArista, Nodo)


type alias BfsState =
    { parents : Dict Int Int
    , order : List Int
    , visited : Set Int
    }


{-| Traza el árbol de flujo dinámicamente mediante BFS a partir del nodo fuente seleccionado.
-}
calcularFlujosManual : Base -> Float -> List ( Int, Int ) -> List FlujoArista
calcularFlujosManual base pct aristasElegidas =
    let
        factor =
            1.0 + (pct / 100.0)

        demandasMap =
            List.map (\n -> ( n.id, n.demanda * factor )) base.nodos
                |> Dict.fromList

        adj =
            List.foldl
                (\a acc ->
                    if esSeleccionada a.origen a.destino aristasElegidas then
                        acc
                            |> Dict.update a.origen (\m -> Just (a.destino :: Maybe.withDefault [] m))
                            |> Dict.update a.destino (\m -> Just (a.origen :: Maybe.withDefault [] m))

                    else
                        acc
                )
                Dict.empty
                base.aristas

        bfsState =
            runBfs [ base.fuente ] (Set.singleton base.fuente) Dict.empty [] adj

        subtreeDemands =
            List.foldl
                (\node acc ->
                    let
                        demandaPropia =
                            Dict.get node demandasMap |> Maybe.withDefault 0.0

                        hijosSuma =
                            Dict.foldl
                                (\hijo padre suma ->
                                    if padre == node then
                                        suma + (Dict.get hijo acc |> Maybe.withDefault 0.0)

                                    else
                                        suma
                                )
                                0.0
                                bfsState.parents
                    in
                    Dict.insert node (demandaPropia + hijosSuma) acc
                )
                Dict.empty
                (List.reverse bfsState.order)
    in
    List.filterMap
        (\a ->
            if esSeleccionada a.origen a.destino aristasElegidas then
                let
                    esHijoDestino =
                        Dict.get a.destino bfsState.parents == Just a.origen

                    esHijoOrigen =
                        Dict.get a.origen bfsState.parents == Just a.destino

                    flujoCalculado =
                        if esHijoDestino then
                            Dict.get a.destino subtreeDemands |> Maybe.withDefault 0.0

                        else if esHijoOrigen then
                            Dict.get a.origen subtreeDemands |> Maybe.withDefault 0.0

                        else
                            0.0

                    util =
                        if a.capacidad > 0 then
                            flujoCalculado / a.capacidad

                        else
                            0.0
                in
                Just
                    { origen = a.origen
                    , destino = a.destino
                    , capacidad = a.capacidad
                    , flujo = flujoCalculado
                    , utilizacion = util
                    , saturada = flujoCalculado > a.capacidad
                    }

            else
                Nothing
        )
        base.aristas


runBfs : List Int -> Set Int -> Dict Int Int -> List Int -> Dict Int (List Int) -> BfsState
runBfs queue visited parents order adj =
    case queue of
        [] ->
            { parents = parents, order = order, visited = visited }

        curr :: rest ->
            let
                vecinos =
                    Dict.get curr adj |> Maybe.withDefault []

                ( newQueue, newVisited, newParents ) =
                    List.foldl
                        (\v ( qAcc, vAcc, pAcc ) ->
                            if Set.member v vAcc then
                                ( qAcc, vAcc, pAcc )

                            else
                                ( qAcc ++ [ v ]
                                , Set.insert v vAcc
                                , Dict.insert v curr pAcc
                                )
                        )
                        ( rest, visited, parents )
                        vecinos
            in
            runBfs newQueue newVisited newParents (order ++ [ curr ]) adj


viewMetricasManual : Maybe Base -> Float -> List ( Int, Int ) -> Html msg
viewMetricasManual maybeBase incrementoPct aristasSeleccionadas =
    case maybeBase of
        Nothing ->
            div [ style "color" "#94a3b8" ] [ text "Cargando métricas..." ]

        Just base ->
            let
                flujosManuales =
                    calcularFlujosManual base incrementoPct aristasSeleccionadas

                factor =
                    1.0 + (incrementoPct / 100.0)

                demandaTotal =
                    (List.map .demanda base.nodos |> List.sum) * factor

                flujoCirculante =
                    flujosManuales
                        |> List.map .flujo
                        |> List.maximum
                        |> Maybe.withDefault 0.0

                saturadasCount =
                    List.length (List.filter .saturada flujosManuales)

                excesoEnSaturadas =
                    flujosManuales
                        |> List.filter .saturada
                        |> List.map (\f -> f.flujo - f.capacidad)
                        |> List.sum

                faltante =
                    max 0.0 (demandaTotal - flujoCirculante + excesoEnSaturadas)

                metrica titulo valor color =
                    div [ style "background" "#1e293b", style "padding" "10px 12px", style "border-radius" "8px" ]
                        [ div [ style "color" "#94a3b8", style "font-size" "0.75rem" ] [ text titulo ]
                        , div [ style "font-size" "1.1rem", style "font-weight" "bold", style "color" color, style "margin-top" "2px" ] [ text valor ]
                        ]
            in
            div [ style "display" "flex", style "flex-direction" "column", style "gap" "8px" ]
                [ metrica "Cañerías activadas" (String.fromInt (List.length aristasSeleccionadas) ++ " aristas") "#38bdf8"
                , metrica "Caudal total desde la fuente" (millones flujoCirculante ++ " gal/mes") "#10b981"
                , metrica "Cañerías saturadas" (String.fromInt saturadasCount ++ " aristas") (if saturadasCount > 0 then "#ef4444" else "#10b981")
                , metrica "Demanda sin cubrir estimada" (millones faltante ++ " gal/mes") (if faltante > 0 then "#ef4444" else "#10b981")
                ]


viewMapaManual : (( Int, Int ) -> msg) -> (Maybe Arista -> msg) -> List ( Int, Int ) -> Dict Int Nodo -> (Nodo -> ( Float, Float )) -> List Arista -> Float -> Base -> Maybe Arista -> Svg msg
viewMapaManual onToggleManual onSelectEdge aristasElegidas porId posicion todasAristas incrementoPct base maybeSelectedEdge =
    let
        flujosCalculados =
            calcularFlujosManual base incrementoPct aristasElegidas

        flujosDict =
            List.map (\f -> ( claveArista f.origen f.destino, f )) flujosCalculados
                |> Dict.fromList
    in
    g []
        (List.filterMap
            (\a ->
                Maybe.map2
                    (\o d ->
                        let
                            ( x1, y1 ) =
                                posicion o

                            ( x2, y2 ) =
                                posicion d

                            -- Recorte de 12px en los extremos para dejar libre el área del círculo del nodo
                            dx =
                                x2 - x1

                            dy =
                                y2 - y1

                            dist =
                                max 1.0 (sqrt (dx * dx + dy * dy))

                            offX =
                                (dx / dist) * 12.0

                            offY =
                                (dy / dist) * 12.0

                            hx1 =
                                x1 + offX

                            hy1 =
                                y1 + offY

                            hx2 =
                                x2 - offX

                            hy2 =
                                y2 - offY

                            activa =
                                esSeleccionada a.origen a.destino aristasElegidas

                            esApuntada =
                                case maybeSelectedEdge of
                                    Just s ->
                                        esMismaArista a s

                                    Nothing ->
                                        False

                            maybeFlujo =
                                Dict.get (claveArista a.origen a.destino) flujosDict

                            estilo =
                                if esApuntada then
                                    { color = "#facc15", ancho = "5", punteado = "none", arista = a }

                                else if activa then
                                    case maybeFlujo of
                                        Just f ->
                                            let
                                                c =
                                                    if f.saturada then
                                                        "#ef4444"

                                                    else if f.utilizacion >= 0.8 then
                                                        "#f59e0b"

                                                    else
                                                        "#38bdf8"

                                                w =
                                                    String.fromFloat (2 + 4 * clamp 0 1 f.utilizacion)
                                            in
                                            { color = c, ancho = w, punteado = "none", arista = { a | flujo = f.flujo } }

                                        Nothing ->
                                            { color = "#38bdf8", ancho = "2.5", punteado = "none", arista = a }

                                else
                                    { color = "#334155", ancho = "1.5", punteado = "4 4", arista = a }
                        in
                        g []
                            [ line
                                [ SvgAttr.x1 (String.fromFloat hx1)
                                , SvgAttr.y1 (String.fromFloat hy1)
                                , SvgAttr.x2 (String.fromFloat hx2)
                                , SvgAttr.y2 (String.fromFloat hy2)
                                , SvgAttr.stroke "transparent"
                                , SvgAttr.strokeWidth "20"
                                , SvgAttr.cursor "pointer"
                                , onMouseDownStop (onToggleManual ( a.origen, a.destino ))
                                , SvgEvents.onMouseOver (onSelectEdge (Just estilo.arista))
                                , SvgEvents.onMouseOut (onSelectEdge Nothing)
                                ]
                                []
                            , line
                                [ SvgAttr.x1 (String.fromFloat x1)
                                , SvgAttr.y1 (String.fromFloat y1)
                                , SvgAttr.x2 (String.fromFloat x2)
                                , SvgAttr.y2 (String.fromFloat y2)
                                , SvgAttr.stroke estilo.color
                                , SvgAttr.strokeWidth estilo.ancho
                                , SvgAttr.strokeDasharray estilo.punteado
                                , SvgAttr.pointerEvents "none"
                                ]
                                []
                            , case maybeFlujo of
                                Just f ->
                                    if f.saturada then
                                        Svg.text_
                                            [ SvgAttr.x (String.fromFloat ((x1 + x2) / 2))
                                            , SvgAttr.y (String.fromFloat ((y1 + y2) / 2 - 7))
                                            , SvgAttr.fill "#ef4444"
                                            , SvgAttr.fontSize "11"
                                            , SvgAttr.fontWeight "bold"
                                            , SvgAttr.textAnchor "middle"
                                            , SvgAttr.pointerEvents "none"
                                            ]
                                            [ Svg.text (millones f.flujo ++ " / " ++ millones f.capacidad) ]

                                    else
                                        text ""

                                Nothing ->
                                    text ""
                            ]
                    )
                    (Dict.get a.origen porId)
                    (Dict.get a.destino porId)
            )
            todasAristas
        )


onMouseDownStop : msg -> Svg.Attribute msg
onMouseDownStop msg =
    custom "mousedown"
        (Decode.succeed
            { message = msg
            , stopPropagation = True
            , preventDefault = True
            }
        )


claveArista : Int -> Int -> String
claveArista o d =
    if o < d then
        String.fromInt o ++ "-" ++ String.fromInt d

    else
        String.fromInt d ++ "-" ++ String.fromInt o


esSeleccionada : Int -> Int -> List ( Int, Int ) -> Bool
esSeleccionada origen destino lista =
    List.any (\( o, d ) -> (o == origen && d == destino) || (o == destino && d == origen)) lista


esMismaArista : Arista -> Arista -> Bool
esMismaArista a1 a2 =
    (a1.origen == a2.origen && a1.destino == a2.destino) || (a1.origen == a2.destino && a1.destino == a2.origen)
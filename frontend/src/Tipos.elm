module Tipos exposing (Edge, Node)

{-| Tipos compartidos entre Main y DatosPrueba.
-}


type alias Node =
    { id : Int
    , lat : Float
    , lon : Float
    , demanda : Float
    , nombre : String
    }


type alias Edge =
    { origen : Int
    , destino : Int
    , capacidad : Float
    , flujo : Float
    , saturado : Bool
    , flujoBase : Float
    }


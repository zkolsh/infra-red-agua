module Tipos exposing (Arista, Base, Escenario, FlujoArista, ModoTab(..), Nodo, Position, Resultado)

{-| Tipos compartidos en la aplicación.
-}


type ModoTab
    = ModoAutomatico
    | ModoManual


type alias Nodo =
    { id : Int
    , zcta : Int
    , lat : Float
    , lon : Float
    , tipoZona : String
    , poblacion : Float
    , demanda : Float
    }


type alias Arista =
    { origen : Int
    , destino : Int
    , costo : Float
    , capacidad : Float
    , enMst : Bool
    , flujo : Float
    }


type alias Escenario =
    { crecimiento : Float
    , demandas : List ( Int, Float )
    }


type alias Base =
    { fuente : Int
    , costoMst : Float
    , nodos : List Nodo
    , aristas : List Arista
    , escenarios : List Escenario
    }


type alias FlujoArista =
    { origen : Int
    , destino : Int
    , capacidad : Float
    , flujo : Float
    , utilizacion : Float
    , saturada : Bool
    }


type alias Resultado =
    { crecimiento : Float
    , demandaTotal : Float
    , flujoTotal : Float
    , faltante : Float
    , satisfecha : Bool
    , aristas : List FlujoArista
    }


type alias Position =
    { x : Float
    , y : Float
    }
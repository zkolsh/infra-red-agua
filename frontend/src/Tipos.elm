module Tipos exposing (Arista, Base, Escenario, FlujoArista, Nodo, Resultado, Position)
 
{-| Tipos compartidos. Los nombres de los campos siguen la respuesta de la API
(`GET /network/base` y `POST /network/scenarios`).
-}
 
 
type alias Nodo =
    { id : Int
    , zcta : Int
    , lat : Float
    , lon : Float
    , tipoZona : String
    , poblacion : Float
    , demanda : Float
    }
 
 
{-| Tendido posible entre dos zonas. `enMst` marca los que forman la red de menor costo.
La capacidad es fija: sale de la demanda base y no cambia con el escenario.
-}
type alias Arista =
    { origen : Int
    , destino : Int
    , costo : Float
    , capacidad : Float
    , enMst : Bool
    , flujo : Float
    }
 
 
{-| Demandas predichas por el modelo de ML para un crecimiento dado (en %).
-}
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
 
 
{-| Flujo sobre una arista de la red de menor costo en un escenario.
-}
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
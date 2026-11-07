"""HTTP layer: routing, request validation, response shapes, error mapping."""
import pytest

from tests.support import AB, BC, CD, GRAPH, MST_COST, MST_PAIRS, NODES, SOURCE_ID, by_pair, by_vertex

P = "/api/v1/network"

DISCONNECTED = {**GRAPH, "edges": GRAPH["edges"][:1]}
UNKNOWN_VERTEX = {**GRAPH, "edges": [{"source": 1, "target": 99, "construction_cost": 1, "capacity": 1}]}
DUPLICATE_EDGE = {**GRAPH, "edges": [*GRAPH["edges"], {"source": 2, "target": 1, "construction_cost": 1, "capacity": 1}]}


def flow_body(**extra):
    return {**GRAPH, "source_id": SOURCE_ID, **extra}


# ---- routing -----------------------------------------------------------------------------------

def test_routes_are_registered_under_v1(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "get" in paths["/api/v1/health"]
    for route in ("mst", "flow", "validate", "scenarios"):
        assert "post" in paths[f"{P}/{route}"], route


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


# ---- POST /network/mst -------------------------------------------------------------------------

@pytest.mark.parametrize("extra", [{}, {"algorithm": "kruskal"}, {"algorithm": "prim"}])
def test_mst(client, extra):
    r = client.post(f"{P}/mst", json={**GRAPH, **extra})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_cost"] == pytest.approx(MST_COST)
    assert set(by_pair(body["edges"])) == MST_PAIRS
    assert set(body["edges"][0]) >= {"source", "target", "construction_cost", "capacity"}


# ---- POST /network/flow ------------------------------------------------------------------------

@pytest.mark.parametrize("flow_algorithm", ["edmonds_karp", "ford_fulkerson"])
def test_flow_baseline(client, flow_algorithm):
    r = client.post(f"{P}/flow", json=flow_body(flow_algorithm=flow_algorithm))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_flow"] == pytest.approx(9) and body["demand_satisfied"] is True
    edges = by_pair(body["edges"])
    assert set(edges) == MST_PAIRS
    assert edges[BC]["saturated"] is True and edges[BC]["utilization"] == pytest.approx(1.0)
    assert edges[AB]["utilization"] == pytest.approx(0.9)
    assert by_vertex(body["vertices"])[2]["delivered"] == pytest.approx(4)


@pytest.mark.parametrize(
    "growth_pct, unmet, satisfied, bottleneck",
    [(0, 0.0, True, None), (10, 0.5, False, BC), (30, 1.7, False, AB)],
)
def test_flow_growth_scenario(client, growth_pct, unmet, satisfied, bottleneck):
    r = client.post(f"{P}/flow", json=flow_body(growth_pct=growth_pct))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["growth_pct"] == growth_pct
    assert body["unmet_demand"] == pytest.approx(unmet)
    assert body["demand_satisfied"] is satisfied
    if bottleneck:
        assert by_pair(body["edges"])[bottleneck]["saturated"] is True


# ---- POST /network/scenarios -------------------------------------------------------------------

def test_scenarios(client):
    r = client.post(f"{P}/scenarios", json=flow_body(growth_pcts=[0, 10, 30]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(by_pair(body["mst"]["edges"])) == MST_PAIRS
    assert [s["growth_pct"] for s in body["scenarios"]] == [0, 10, 30]
    assert [s["demand_satisfied"] for s in body["scenarios"]] == [True, False, False]
    assert by_pair(body["scenarios"][2]["edges"])[AB]["saturated"] is True


# ---- POST /network/validate --------------------------------------------------------------------

def test_validate_complete_drawing(client):
    r = client.post(f"{P}/validate", json=GRAPH)
    assert r.status_code == 200 and r.json() == {"valid": True, "connected": True, "error": None}


def test_validate_incomplete_drawing(client):
    r = client.post(f"{P}/validate", json=DISCONNECTED)
    assert r.status_code == 200 and r.json() == {"valid": True, "connected": False, "error": None}


@pytest.mark.parametrize("body", [UNKNOWN_VERTEX, DUPLICATE_EDGE])
def test_validate_reports_bad_drawings_with_a_200(client, body):
    r = client.post(f"{P}/validate", json=body)
    assert r.status_code == 200
    assert r.json()["valid"] is False and r.json()["error"]


# ---- engine errors surface as 422 with a readable detail --------------------------------------------

@pytest.mark.parametrize("route, body", [
    ("mst", DISCONNECTED),
    ("flow", {**DISCONNECTED, "source_id": SOURCE_ID}),
    ("scenarios", {**DISCONNECTED, "source_id": SOURCE_ID, "growth_pcts": [0, 10]}),
])
def test_disconnected_drawing_is_422(client, route, body):
    r = client.post(f"{P}/{route}", json=body)
    assert r.status_code == 422
    assert "connect" in r.json()["detail"].lower()


@pytest.mark.parametrize("body", [UNKNOWN_VERTEX, DUPLICATE_EDGE])
def test_invalid_graph_is_422(client, body):
    r = client.post(f"{P}/mst", json=body)
    assert r.status_code == 422 and isinstance(r.json()["detail"], str)


def test_unknown_source_is_422(client):
    assert client.post(f"{P}/flow", json=flow_body(source_id=99)).status_code == 422


# ---- request validation (rejected before reaching the engine) ----------------------------------

def _edge(**over):
    return {"source": 1, "target": 2, "construction_cost": 1, "capacity": 1, **over}


@pytest.mark.parametrize("bad_edge", [
    {k: v for k, v in _edge().items() if k != "construction_cost"},  # cost is required
    _edge(construction_cost=-1),
    _edge(capacity=0),
    _edge(source="A"),  # vertex ids are integers
])
def test_malformed_edges_are_rejected(client, bad_edge):
    assert client.post(f"{P}/mst", json={**GRAPH, "edges": [bad_edge]}).status_code == 422


@pytest.mark.parametrize("body", [
    {"nodes": [], "edges": []},
    {"nodes": [{**NODES[0], "id": "A"}], "edges": []},
    {"nodes": [{**NODES[0], "demand": -1}], "edges": []},
    {"nodes": [{"id": 1, "lat": 95, "lon": 0}], "edges": []},
    {"edges": []},
])
def test_malformed_nodes_are_rejected(client, body):
    assert client.post(f"{P}/mst", json=body).status_code == 422


@pytest.mark.parametrize("route, extra", [
    ("flow", {}),  # source_id missing
    ("flow", {"source_id": SOURCE_ID, "growth_pct": -100}),
    ("flow", {"source_id": SOURCE_ID, "flow_algorithm": "dijkstra"}),
    ("mst", {"algorithm": "boruvka"}),
    ("scenarios", {"source_id": SOURCE_ID, "growth_pcts": "10"}),
])
def test_bad_parameters_are_rejected(client, route, extra):
    assert client.post(f"{P}/{route}", json={**GRAPH, **extra}).status_code == 422


@pytest.mark.parametrize("route", ["mst", "flow", "validate", "scenarios"])
def test_get_is_not_allowed(client, route):
    assert client.get(f"{P}/{route}").status_code == 405

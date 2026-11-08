"""HTTP layer: routing, request validation, response shapes, error mapping."""
import pytest

from tests.support import (
    AB, B, BC, DEMANDS, GRAPH, MST_COST, MST_PAIRS, NODES, SOURCE_ID,
    by_pair, by_vertex, label, scaled,
)

P = "/api/v1/network"

DISCONNECTED_EDGES = GRAPH["edges"][:1]
UNKNOWN_VERTEX = {
    **GRAPH, "edges": [{"source": 1, "target": 99, "construction_cost": 1, "capacity": 1}]}
DUPLICATE_EDGE = {**GRAPH, "edges": [*GRAPH["edges"], {
    "source": 2, "target": 1, "construction_cost": 1, "capacity": 1}]}
DISCONNECTED = {**GRAPH, "edges": DISCONNECTED_EDGES}


def flow_body(**extra):
    return {**GRAPH, "source_id": SOURCE_ID, "demands": DEMANDS, **extra}


def scenarios_body(growth_pcts, **extra):
    return {
        **GRAPH, "source_id": SOURCE_ID,
        "scenarios": [{"label": label(p), "demands": scaled(DEMANDS, p)} for p in growth_pcts],
        **extra,
    }


def without(body, key):
    return {k: v for k, v in body.items() if k != key}


def test_routes_are_registered_under_v1(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "get" in paths["/api/v1/health"]
    for route in ("nodes", "demands"):
        assert "get" in paths[f"{P}/{route}"], route
    for route in ("mst", "flow", "validate", "scenarios"):
        assert "post" in paths[f"{P}/{route}"], route


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


# GET /network/nodes

def test_nodes_layout(client):
    r = client.get(f"{P}/nodes")
    assert r.status_code == 200, r.text
    nodes = r.json()["nodes"]
    assert nodes
    assert len({n["id"] for n in nodes}) == len(nodes)
    for n in nodes:
        assert set(n) >= {"id", "lat", "lon", "zone_type", "population"}
        assert -90 <= n["lat"] <= 90 and -180 <= n["lon"] <= 180
        assert "demand" not in n  # demand is scenario data: GET /demands


# GET /network/demands

def test_demands_cover_every_node(client):
    ids = {n["id"] for n in client.get(f"{P}/nodes").json()["nodes"]}
    r = client.get(f"{P}/demands")
    assert r.status_code == 200, r.text
    demands = r.json()["demands"]
    assert {int(k) for k in demands} == ids
    assert all(v >= 0 for v in demands.values())


def test_demands_default_scenario_is_zero_growth(client):
    assert client.get(
        f"{P}/demands").json() == client.get(f"{P}/demands", params={"growth_pct": 0}).json()


@pytest.mark.parametrize("growth_pct", [-100, -50, 10, 30])
def test_demands_accept_growth_scenarios(client, growth_pct):
    ids = {n["id"] for n in client.get(f"{P}/nodes").json()["nodes"]}
    r = client.get(f"{P}/demands", params={"growth_pct": growth_pct})
    assert r.status_code == 200, r.text
    assert {int(k) for k in r.json()["demands"]} == ids


@pytest.mark.parametrize("growth_pct", [-100.1, -500, "abc"])
def test_demands_reject_bad_growth(client, growth_pct):
    assert client.get(
        f"{P}/demands", params={"growth_pct": growth_pct}).status_code == 422


def test_dataset_demands_feed_the_flow_endpoint(client):
    """The frontend's real sequence: nodes -> draw edges -> demands for a scenario -> flow."""
    nodes = client.get(f"{P}/nodes").json()["nodes"]
    ids = sorted(n["id"] for n in nodes)
    source = ids[0]
    demands = {int(k): v for k, v in client.get(
        f"{P}/demands", params={"growth_pct": 10}).json()["demands"].items()}
    demands.pop(source)  # the source supplies water; it does not consume it
    total = sum(demands.values())
    body = {
        "nodes": [{"id": n["id"], "lat": n["lat"], "lon": n["lon"]} for n in nodes],
        "edges": [
            {"source": a, "target": b, "construction_cost": 1,
                "capacity": total * 10 + 1}
            for a, b in zip(ids, ids[1:])
        ],
        "source_id": source,
        "demands": demands,
    }
    r = client.post(f"{P}/flow", json=body)
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["total_demand"] == pytest.approx(total)
    assert res["unmet_demand"] == pytest.approx(
        0) and res["demand_satisfied"] is True


# POST /network/mst

@pytest.mark.parametrize("extra", [{}, {"algorithm": "kruskal"}, {"algorithm": "prim"}])
def test_mst(client, extra):
    r = client.post(f"{P}/mst", json={**GRAPH, **extra})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_cost"] == pytest.approx(MST_COST)
    assert set(by_pair(body["edges"])) == MST_PAIRS
    assert set(body["edges"][0]) >= {
        "source", "target", "construction_cost", "capacity"}


# POST /network/flow

@pytest.mark.parametrize("flow_algorithm", ["edmonds_karp", "ford_fulkerson"])
def test_flow_baseline(client, flow_algorithm):
    r = client.post(f"{P}/flow", json=flow_body(flow_algorithm=flow_algorithm))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_flow"] == pytest.approx(
        9) and body["demand_satisfied"] is True
    edges = by_pair(body["edges"])
    assert set(edges) == MST_PAIRS
    assert edges[BC]["saturated"] is True and edges[BC]["utilization"] == pytest.approx(
        1.0)
    assert edges[AB]["utilization"] == pytest.approx(0.9)
    assert by_vertex(body["vertices"])[B]["delivered"] == pytest.approx(4)


@pytest.mark.parametrize(
    "growth_pct, unmet, satisfied, bottleneck",
    [(0, 0.0, True, None), (10, 0.5, False, BC), (30, 1.7, False, AB)],
)
def test_flow_with_scenario_demands(client, growth_pct, unmet, satisfied, bottleneck):
    r = client.post(
        f"{P}/flow", json=flow_body(demands=scaled(DEMANDS, growth_pct)))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["unmet_demand"] == pytest.approx(unmet)
    assert body["demand_satisfied"] is satisfied
    if bottleneck:
        assert by_pair(body["edges"])[bottleneck]["saturated"] is True


# POST /network/scenarios

def test_scenarios(client):
    r = client.post(f"{P}/scenarios", json=scenarios_body([0, 10, 30]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(by_pair(body["mst"]["edges"])) == MST_PAIRS
    assert [s["label"] for s in body["scenarios"]] == [
        label(0), label(10), label(30)]
    assert [s["demand_satisfied"]
            for s in body["scenarios"]] == [True, False, False]
    assert by_pair(body["scenarios"][2]["edges"])[AB]["saturated"] is True


def test_scenario_label_is_optional(client):
    body = scenarios_body([0])
    del body["scenarios"][0]["label"]
    r = client.post(f"{P}/scenarios", json=body)
    assert r.status_code == 200, r.text
    assert r.json()["scenarios"][0]["label"] is None


# POST /network/validate

def test_validate_complete_drawing(client):
    r = client.post(f"{P}/validate", json=GRAPH)
    assert r.status_code == 200 and r.json(
    ) == {"valid": True, "connected": True, "error": None}


def test_validate_incomplete_drawing(client):
    r = client.post(f"{P}/validate", json=DISCONNECTED)
    assert r.status_code == 200 and r.json(
    ) == {"valid": True, "connected": False, "error": None}


@pytest.mark.parametrize("body", [UNKNOWN_VERTEX, DUPLICATE_EDGE])
def test_validate_reports_bad_drawings_with_a_200(client, body):
    r = client.post(f"{P}/validate", json=body)
    assert r.status_code == 200
    assert r.json()["valid"] is False and r.json()["error"]


@pytest.mark.parametrize("route, body", [
    ("mst", DISCONNECTED),
    ("flow", {**flow_body(), "edges": DISCONNECTED_EDGES}),
    ("scenarios", {**scenarios_body([0, 10]), "edges": DISCONNECTED_EDGES}),
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
    assert client.post(
        f"{P}/flow", json=flow_body(source_id=99)).status_code == 422


def test_demand_for_an_unknown_vertex_is_422(client):
    r = client.post(f"{P}/flow", json=flow_body(demands={**DEMANDS, 99: 5}))
    assert r.status_code == 422


# request validation

def _edge(**over):
    return {"source": 1, "target": 2, "construction_cost": 1, "capacity": 1, **over}


@pytest.mark.parametrize("bad_edge", [
    {k: v for k, v in _edge().items() if k != "construction_cost"},  # cost is required
    _edge(construction_cost=-1),
    _edge(capacity=0),
    _edge(source="A"),  # vertex ids are integers
])
def test_malformed_edges_are_rejected(client, bad_edge):
    assert client.post(
        f"{P}/mst", json={**GRAPH, "edges": [bad_edge]}).status_code == 422


@pytest.mark.parametrize("body", [
    {"nodes": [], "edges": []},
    {"nodes": [{**NODES[0], "id": "A"}], "edges": []},
    {"nodes": [{**NODES[0], "lat": 95}], "edges": []},
    {"nodes": [{**NODES[0], "lon": 181}], "edges": []},
    {"nodes": [{"id": 1, "lat": 0}], "edges": []},  # lon missing
    {"edges": []},
])
def test_malformed_nodes_are_rejected(client, body):
    assert client.post(f"{P}/mst", json=body).status_code == 422


@pytest.mark.parametrize("route, body", [
    ("mst", {**GRAPH, "algorithm": "boruvka"}),
    ("flow", without(flow_body(), "source_id")),
    ("flow", without(flow_body(), "demands")),
    ("flow", flow_body(flow_algorithm="dijkstra")),
    ("flow", flow_body(mst_algorithm="boruvka")),
    ("flow", flow_body(demands={B: -1})),  # demands are not negative
    ("flow", flow_body(demands={"B": 1})),  # keys are vertex ids (integers)
    ("flow", flow_body(demands={2**32: 1})),  # ...within uint32
    ("flow", flow_body(demands=[1, 2])),  # a mapping, not a list
    ("scenarios", scenarios_body([])),  # at least one scenario
    ("scenarios", scenarios_body(range(21))),  # at most 20
    ("scenarios", {**scenarios_body([0]), "scenarios": "+10%"}),
    # demands missing
    ("scenarios", {**scenarios_body([0]), "scenarios": [{"label": "x"}]}),
    ("scenarios", {**scenarios_body([0]),
     "scenarios": [{"demands": {B: -1}}]}),
    ("scenarios", without(scenarios_body([0]), "source_id")),
])
def test_bad_parameters_are_rejected(client, route, body):
    assert client.post(f"{P}/{route}", json=body).status_code == 422


@pytest.mark.parametrize("route", ["mst", "flow", "validate", "scenarios"])
def test_get_is_not_allowed(client, route):
    assert client.get(f"{P}/{route}").status_code == 405


@pytest.mark.parametrize("route", ["nodes", "demands"])
def test_post_is_not_allowed_on_the_dataset_routes(client, route):
    assert client.post(f"{P}/{route}").status_code == 405

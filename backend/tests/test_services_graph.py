"""graph_service against the real C engine (no stand-ins), one test group per service function."""
from contextlib import contextmanager

import pytest

from app import graph_engine as ge
from app.services import graph_service as svc
from app.services.graph_service import GraphEngineError
from tests.support import (
    A, AB, B, BC, C, CD, D, EDGES, MST_COST, MST_PAIRS, SOURCE_ID,
    by_pair, by_vertex, flow_req, mst_req, scenarios_req, validate_req,
)

ALGORITHMS = ["kruskal", "prim"]
FLOW_ALGORITHMS = ["edmonds_karp", "ford_fulkerson"]

DISCONNECTED = EDGES[:1]  # only A-B drawn: C and D are unreachable
UNKNOWN_VERTEX = [*EDGES, {"source": A, "target": 99,
                           "construction_cost": 1, "capacity": 1}]
DUPLICATE_EDGE = [*EDGES, {"source": A, "target": B,
                           "construction_cost": 9, "capacity": 1}]


@contextmanager
def raises_engine_error(status):
    with pytest.raises(GraphEngineError) as exc:
        yield
    assert exc.value.engine_status == status and exc.value.status_code == 422


# ---- compute_mst -------------------------------------------------------------------------------

@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_mst_picks_the_cheapest_spanning_edges(algorithm):
    res = svc.compute_mst(mst_req(algorithm=algorithm))
    edges = by_pair(res["edges"])
    assert set(edges) == MST_PAIRS
    assert res["total_cost"] == pytest.approx(MST_COST)
    # struct fields pass through
    assert edges[BC]["construction_cost"] == 2 and edges[BC]["capacity"] == 5


def test_mst_single_node_needs_no_edges():
    req = mst_req(edges=[])
    req.nodes = req.nodes[:1]
    res = svc.compute_mst(req)
    assert res["edges"] == [] and res["total_cost"] == 0


def test_mst_zero_cost_edges_are_allowed():
    free = [{**e, "construction_cost": 0} for e in EDGES]
    assert svc.compute_mst(mst_req(edges=free))["total_cost"] == 0


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_mst_disconnected_drawing_is_an_error(algorithm):
    with raises_engine_error(ge.GRAPH_STATUS_DISCONNECTED):
        svc.compute_mst(mst_req(edges=DISCONNECTED, algorithm=algorithm))


def test_mst_unknown_vertex():
    with raises_engine_error(ge.GRAPH_STATUS_VERTEX_NOT_FOUND):
        svc.compute_mst(mst_req(edges=UNKNOWN_VERTEX))


def test_mst_duplicate_edge():
    with raises_engine_error(ge.GRAPH_STATUS_EDGE_ALREADY_EXISTS):
        svc.compute_mst(mst_req(edges=DUPLICATE_EDGE))


# ---- validate ----------------------------------------------------------------------------------

def test_validate_connected_drawing():
    assert svc.validate(validate_req()) == {
        "valid": True, "connected": True, "error": None}


def test_validate_incomplete_drawing_is_valid_but_not_connected():
    assert svc.validate(validate_req(DISCONNECTED)) == {
        "valid": True, "connected": False, "error": None}


@pytest.mark.parametrize("edges", [UNKNOWN_VERTEX, DUPLICATE_EDGE])
def test_validate_reports_a_bad_drawing_instead_of_raising(edges):
    res = svc.validate(validate_req(edges))
    assert res["valid"] is False and res["connected"] is False and res["error"]


# ---- compute_flow ------------------------------------------------------------------------------

@pytest.mark.parametrize("mst_algorithm", ALGORITHMS)
@pytest.mark.parametrize("flow_algorithm", FLOW_ALGORITHMS)
def test_flow_baseline(mst_algorithm, flow_algorithm):
    res = svc.compute_flow(
        flow_req(mst_algorithm=mst_algorithm, flow_algorithm=flow_algorithm))
    assert res["growth_pct"] == 0
    assert res["total_demand"] == pytest.approx(9)
    assert res["total_flow"] == pytest.approx(9)
    assert res["unmet_demand"] == pytest.approx(0)
    assert res["demand_satisfied"] is True

    edges = by_pair(res["edges"])
    assert abs(edges[AB]["flow"]) == pytest.approx(
        9) and edges[AB]["utilization"] == pytest.approx(0.9)
    assert abs(edges[BC]["flow"]) == pytest.approx(
        5) and edges[BC]["utilization"] == pytest.approx(1.0)
    assert abs(edges[CD]["flow"]) == pytest.approx(2)
    assert edges[BC]["saturated"] is True
    assert edges[AB]["saturated"] is False and edges[CD]["saturated"] is False

    vertices = by_vertex(res["vertices"])
    for vid, demand in ((B, 4), (C, 3), (D, 2)):
        assert vertices[vid]["demand"] == pytest.approx(demand)
        assert vertices[vid]["delivered"] == pytest.approx(demand)
        assert vertices[vid]["unmet"] == pytest.approx(0)


def test_flow_runs_on_the_mst_only():
    res = svc.compute_flow(flow_req())
    # A-C and B-D were drawn but not built
    assert set(by_pair(res["edges"])) == MST_PAIRS


@pytest.mark.parametrize(
    "growth_pct, total_demand, total_flow, unmet, satisfied",
    [
        (-50, 4.5, 4.5, 0.0, True),
        (0, 9.0, 9.0, 0.0, True),
        (10, 9.9, 9.4, 0.5, False),
        (30, 11.7, 10.0, 1.7, False),
    ],
)
def test_flow_growth_scenarios(growth_pct, total_demand, total_flow, unmet, satisfied):
    res = svc.compute_flow(flow_req(growth_pct=growth_pct))
    assert res["growth_pct"] == growth_pct
    assert res["total_demand"] == pytest.approx(total_demand)
    assert res["total_flow"] == pytest.approx(total_flow)
    assert res["unmet_demand"] == pytest.approx(unmet)
    assert res["demand_satisfied"] is satisfied
    assert sum(v["unmet"] for v in res["vertices"]) == pytest.approx(unmet)


@pytest.mark.parametrize("growth_pct, bottleneck", [(10, BC), (30, AB)])
def test_flow_flags_the_bottleneck_edge_as_saturated(growth_pct, bottleneck):
    edges = by_pair(svc.compute_flow(flow_req(growth_pct=growth_pct))["edges"])
    assert edges[bottleneck]["saturated"] is True
    assert edges[bottleneck]["utilization"] == pytest.approx(1.0)


def test_flow_disconnected_drawing_is_an_error():
    with raises_engine_error(ge.GRAPH_STATUS_DISCONNECTED):
        svc.compute_flow(flow_req(edges=DISCONNECTED))


def test_flow_unknown_source():
    with pytest.raises(GraphEngineError) as exc:
        svc.compute_flow(flow_req(source_id=99))
    assert exc.value.status_code == 422


# ---- compute_scenarios -------------------------------------------------------------------------

def test_scenarios_share_one_mst_and_keep_request_order():
    res = svc.compute_scenarios(scenarios_req([30, 0, 10]))
    assert set(by_pair(res["mst"]["edges"])) == MST_PAIRS
    assert res["mst"]["total_cost"] == pytest.approx(MST_COST)
    assert [s["growth_pct"] for s in res["scenarios"]] == [30, 0, 10]
    assert [s["demand_satisfied"]
            for s in res["scenarios"]] == [False, True, False]


@pytest.mark.parametrize("growth_pct", [0, 10, 30])
def test_each_scenario_matches_a_standalone_flow(growth_pct):
    scenario = svc.compute_scenarios(scenarios_req([growth_pct]))[
        "scenarios"][0]
    single = svc.compute_flow(flow_req(growth_pct=growth_pct))
    assert scenario["total_flow"] == pytest.approx(single["total_flow"])
    assert scenario["unmet_demand"] == pytest.approx(single["unmet_demand"])
    assert {p: e["saturated"] for p, e in by_pair(scenario["edges"]).items()} == {
        p: e["saturated"] for p, e in by_pair(single["edges"]).items()
    }


def test_scenarios_disconnected_drawing_is_an_error():
    with raises_engine_error(ge.GRAPH_STATUS_DISCONNECTED):
        svc.compute_scenarios(scenarios_req([0, 10], edges=DISCONNECTED))


# ---- C handle lifetime -------------------------------------------------------------------------

def test_repeated_calls_including_failures_do_not_corrupt_the_engine():
    """A double free or a use-after-free would crash the process; a leak would show up in memory."""
    for _ in range(200):
        svc.compute_mst(mst_req())
        svc.compute_flow(flow_req(growth_pct=30))
        svc.compute_scenarios(scenarios_req([0, 10, 30]))
        svc.validate(validate_req())
        with pytest.raises(GraphEngineError):
            svc.compute_mst(mst_req(edges=DISCONNECTED))
        with pytest.raises(GraphEngineError):
            svc.compute_flow(flow_req(edges=UNKNOWN_VERTEX))

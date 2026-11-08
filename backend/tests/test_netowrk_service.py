import pytest
 
P = "/api/v1/network"
 
 
def _scenarios_body(base, growths=None):
    scenarios = [s for s in base["scenarios"] if growths is None or s["growth_pct"] in growths]
    return {
        "nodes": [{"id": n["id"], "lat": n["lat"], "lon": n["lon"]} for n in base["nodes"]],
        "edges": [{k: e[k] for k in ("source", "target", "construction_cost", "capacity")} for e in base["edges"]],
        "source_id": base["source_id"],
        "scenarios": [{"label": f"+{s['growth_pct']:g}%", "demands": s["demands"]} for s in scenarios],
    }
 
 
@pytest.fixture(scope="module")
def base(client):
    r = client.get(f"{P}/base")
    assert r.status_code == 200, r.text
    return r.json()
 
 
def test_base_covers_every_zone(client, base):
    ids = {n["id"] for n in client.get(f"{P}/nodes").json()["nodes"]}
    assert {n["id"] for n in base["nodes"]} == ids
    assert base["source_id"] in ids
 
 
def test_base_minimum_cost_network_connects_every_zone(base):
    mst = [e for e in base["edges"] if e["in_mst"]]
    assert len(mst) == len(base["nodes"]) - 1
    assert len(base["edges"]) > len(mst)  # there are candidate pipes that were not chosen
    assert all(e["capacity"] > 0 and e["construction_cost"] > 0 for e in base["edges"])
 
 
def test_base_offers_growth_scenarios_without_the_source(base):
    assert [s["growth_pct"] for s in base["scenarios"]] == [0, 10, 30, 50, 100]
    for s in base["scenarios"]:
        assert str(base["source_id"]) not in s["demands"] and base["source_id"] not in s["demands"]
        assert len(s["demands"]) == len(base["nodes"]) - 1
    totals = [sum(s["demands"].values()) for s in base["scenarios"]]
    assert totals == sorted(totals) and totals[0] < totals[-1]
 
 
def test_base_network_covers_the_base_demand_and_saturates_with_growth(client, base):
    r = client.post(f"{P}/scenarios", json=_scenarios_body(base))
    assert r.status_code == 200, r.text
    body = r.json()
    results = body["scenarios"]
    assert results[0]["demand_satisfied"] is True
    assert results[0]["unmet_demand"] == pytest.approx(0, abs=1)
    saturated = [sum(e["saturated"] for e in s["edges"]) for s in results]
    assert saturated == sorted(saturated)       # more growth never saturates fewer pipes
    assert saturated[-1] > 0                    # the +100 % scenario must show saturated pipes
    assert results[-1]["total_demand"] > results[0]["total_demand"]
    assert {frozenset((e["source"], e["target"])) for e in body["mst"]["edges"]} == \
        {frozenset((e["source"], e["target"])) for e in base["edges"] if e["in_mst"]}
 
 
def test_base_with_a_chosen_source(client, base):
    other = next(n["id"] for n in base["nodes"] if n["id"] != base["source_id"])
    r = client.get(f"{P}/base", params={"source_id": other})
    assert r.status_code == 200, r.text
    assert r.json()["source_id"] == other
 
 
@pytest.mark.parametrize("source_id", [99999, -1, "abc"])
def test_base_rejects_a_bad_source(client, source_id):
    assert client.get(f"{P}/base", params={"source_id": source_id}).status_code == 422
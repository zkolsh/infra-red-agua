from app.services import zone_service


def test_layout_describes_every_dataset_node():
    nodes = zone_service.layout()
    assert nodes
    assert len({n["id"] for n in nodes}) == len(nodes)
    for n in nodes:
        assert isinstance(n["id"], int)
        assert -90 <= n["lat"] <= 90 and -180 <= n["lon"] <= 180
        assert n["zone_type"] and n["population"] >= 0


def test_projected_demands_cover_the_layout_and_are_clean():
    ids = {n["id"] for n in zone_service.layout()}
    demands = zone_service.project_demands(0.0)
    assert set(demands) == ids
    assert all(isinstance(v, float) and v >=
               0 for v in demands.values())
    assert all(round(v, 2) == v for v in demands.values())


def test_a_scenario_does_not_change_the_dataset_or_later_projections():
    """The dataframe is module-level state shared by every request: a scenario must not mutate it."""
    before = zone_service.project_demands(0.0)
    zone_service.project_demands(50.0)
    assert zone_service.project_demands(0.0) == before

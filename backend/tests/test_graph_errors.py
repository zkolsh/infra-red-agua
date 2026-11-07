"""The status table needs no compiled library, only the constants."""
import pytest

from app import graph_engine as ge
from app.services.graph_service import GraphEngineError

ERROR_STATUSES = [
    getattr(ge, name) for name in dir(ge) if name.startswith("GRAPH_STATUS_") and name != "GRAPH_STATUS_OK"
]


@pytest.mark.parametrize("status", ERROR_STATUSES)
def test_every_engine_status_has_a_mapping(status):
    err = GraphEngineError(status)
    assert err.engine_status == status
    assert err.status_code in (422, 500)
    # a real message, not the fallback
    assert err.detail and "status" not in err.detail.lower()


@pytest.mark.parametrize(
    "status, http",
    [
        (ge.GRAPH_STATUS_DISCONNECTED, 422),
        (ge.GRAPH_STATUS_VERTEX_NOT_FOUND, 422),
        (ge.GRAPH_STATUS_EDGE_ALREADY_EXISTS, 422),
        (ge.GRAPH_STATUS_INVALID_GRAPH, 422),
        (ge.GRAPH_STATUS_OUT_OF_MEMORY, 500),
        (ge.GRAPH_STATUS_INVALID_RESULT, 500),
    ],
)
def test_client_problems_are_422_and_engine_problems_are_500(status, http):
    assert GraphEngineError(status).status_code == http


def test_unknown_status_is_a_500():
    assert GraphEngineError(999).status_code == 500

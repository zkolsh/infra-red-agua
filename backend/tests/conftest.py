import pytest

from app import graph_engine as ge


def pytest_sessionstart(session):
    """Abort the whole run if the C library cannot be loaded; nothing here is meaningful without it.
    The bindings swallow the real error (`except Exception: _lib = None`), so load it again here
    to show why it failed."""

    try:
        ge.bind_functions(ge.load_graph_library())
    except Exception as exc:
        pytest.exit(
            f"graph_engine could not be loaded: {type(exc).__name__}: {exc}\n"
            "Build the shared library and make sure the loader can find it",
            returncode=3,
        )


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)

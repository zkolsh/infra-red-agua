"""Settings come from one TOML file (stdlib tomllib, Python >= 3.11).
The only environment variable is RTS_LOCATION, and it only says where that file is.
"""
from __future__ import annotations

import os
import tomllib
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "rts.toml"


class Cors(BaseModel):
    allow_origins: list[str]


class Settings(BaseModel):
    cors: Cors
    libgraph_engine_loc: Path


@lru_cache
def get_settings() -> Settings:
    path = Path(os.environ.get("RTS_LOCATION", DEFAULT_PATH)).resolve()
    data = tomllib.loads(path.read_text(encoding="utf-8"))

    settings = Settings.model_validate(data)

    if not settings.libgraph_engine_loc.is_absolute():
        settings.libgraph_engine_loc = (
            path.parent / settings.libgraph_engine_loc
        ).resolve()

    return settings

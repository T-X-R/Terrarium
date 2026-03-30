"""Shared pytest fixtures for Terrarium tests."""

import pytest

from src.core.config import TerrariumConfig
from src.core.tools import create_tools


@pytest.fixture
def tools(tmp_path):
    """Create a dict of tool instances keyed by name, bound to *tmp_path*."""
    return {t.name: t for t in create_tools(tmp_path, TerrariumConfig())}

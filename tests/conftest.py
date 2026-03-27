"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_project():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)
        
        # Create some files
        (project / "main.py").write_text("# main file")
        (project / "utils.py").write_text("# utils file")
        (project / "README.md").write_text("# README")
        
        yield project


@pytest.fixture
def initialized_project(temp_project):
    """Create an initialized Terrarium project."""
    terrarium_dir = temp_project / ".terrarium"
    terrarium_dir.mkdir()
    (terrarium_dir / "memory").mkdir()
    (terrarium_dir / "logs").mkdir()
    
    config = """
version: "0.1"
project_type: python
heartbeat:
  enabled: false
skills:
  - perception
  - memory
"""
    (terrarium_dir / "config.yaml").write_text(config)
    
    yield temp_project

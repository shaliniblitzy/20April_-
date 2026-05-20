"""Test package marker.

Makes ``tests/`` a regular Python package so pytest can resolve test-module
imports cleanly and avoid name collisions. This module intentionally contains
no executable code; shared fixtures live in :mod:`tests.conftest`, and pytest
discovers test modules via ``[tool.pytest.ini_options].testpaths`` in
``pyproject.toml``. See AAP §0.4.1.
"""

"""Shared pytest fixtures for the Flask scaffold test suite.

Purpose
-------
This module is the canonical pytest fixtures module discovered by pytest
via the ``conftest.py`` naming convention. It provides the three
fixtures consumed by every test module in :mod:`tests`:

* :func:`app`    — yields a Flask instance built via
  ``create_app("testing")``.
* :func:`client` — yields ``app.test_client()`` for HTTP request
  simulation.
* :func:`runner` — yields ``app.test_cli_runner()`` for Click CLI
  command testing.

All fixtures use the ``TestingConfig`` profile (``TESTING=True``) so
tests run hermetically without depending on the environment, and use
the default function scope so each test function gets an independent
Flask instance — ensuring order-independent execution.

Discovery
---------
pytest auto-discovers :mod:`conftest.py` modules anywhere under
``testpaths`` (configured to ``["tests"]`` in ``pyproject.toml``). No
manual import is required from individual test modules: fixtures are
consumed via parameter injection. For example::

    def test_index_returns_200(client):
        response = client.get("/")
        assert response.status_code == 200

Test isolation contract (AAP §0.6.7)
-------------------------------------
Function-scoped fixtures provide per-test hermeticity by default. Each
``def test_*(client): ...`` invocation receives:

* A fresh :class:`flask.Flask` instance built by :func:`create_app`
  under ``TestingConfig`` (``TESTING=True``).
* A fresh :class:`flask.testing.FlaskClient` bound to that instance.
* A fresh :class:`flask.testing.FlaskCliRunner` bound to that instance.

This eliminates the cross-test state-leakage class of bugs that plagues
shared-Flask-instance test suites. Session-scoped fixtures are
intentionally avoided unless an explicit cost/benefit case justifies
the reduced isolation.

References
----------
* AAP §0.4.1 — Transformation table row for ``tests/conftest.py``
  (``app`` fixture builds ``create_app('testing')``; ``client`` fixture
  yields ``app.test_client()``; ``runner`` fixture yields
  ``app.test_cli_runner()``)
* AAP §0.6.7 — Cross-cutting concerns: test isolation via
  ``TESTING=True``
* AAP §0.7.2 — Preservation rules: tests must remain portable when the
  Node.js source becomes available
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from flask import Flask
from flask.testing import FlaskClient, FlaskCliRunner

from app import create_app


@pytest.fixture
def app() -> Generator[Flask, None, None]:
    """Build a Flask application instance configured for testing.

    Each test function receiving ``app`` gets its own fresh Flask
    instance constructed via ``create_app("testing")``. The
    ``TestingConfig`` profile sets ``TESTING=True`` and provides a
    hardcoded ``SECRET_KEY`` so tests run hermetically without
    requiring environment variables.

    The fixture uses ``yield`` (not ``return``) so any future cleanup
    logic can be added below the yield point without breaking the
    fixture contract. The local variable is named ``application`` to
    avoid shadowing the fixture name itself.

    Yields:
        A configured :class:`flask.Flask` instance ready for HTTP
        request simulation via :meth:`flask.Flask.test_client` and
        Click command testing via
        :meth:`flask.Flask.test_cli_runner`.
    """
    application = create_app("testing")
    yield application


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Provide a Flask test client for HTTP request simulation.

    The :class:`flask.testing.FlaskClient` allows tests to dispatch
    HTTP requests directly against the WSGI callable without spinning
    up a real network server — every ``client.get(...)``,
    ``client.post(...)``, etc. call runs inside the same Python
    process as the test, returning a :class:`flask.Response` object
    whose body, headers, and status code can be asserted against.

    The client shares the application's lifecycle (it inherits the
    same configuration, blueprints, error handlers, and logging
    setup), so no separate teardown is needed. The ``with`` block
    form is intentionally NOT used: leaving the implicit context
    manager open lets test functions inspect response data after the
    request returns.

    Args:
        app: The Flask application fixture (auto-injected by pytest's
            parameter-injection mechanism).

    Returns:
        A :class:`flask.testing.FlaskClient` bound to the test
        application instance.
    """
    return app.test_client()


@pytest.fixture
def runner(app: Flask) -> FlaskCliRunner:
    """Provide a Flask CLI test runner for Click command testing.

    The :class:`flask.testing.FlaskCliRunner` invokes ``flask`` CLI
    commands (built-in or custom ``@app.cli.command()``-registered)
    in-process — no subprocess fork, no shell escaping. This fixture
    is currently unused by the scaffold (no custom CLI commands
    exist) but is part of the canonical fixture surface mandated by
    AAP §0.4.1 so test authors know it is available when they add
    CLI commands.

    Args:
        app: The Flask application fixture (auto-injected by pytest's
            parameter-injection mechanism).

    Returns:
        A :class:`flask.testing.FlaskCliRunner` bound to the test
        application instance.
    """
    return app.test_cli_runner()

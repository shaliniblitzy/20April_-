"""Tests for the application factory ``create_app`` (``app/__init__.py``).

Purpose
-------
This module is the pytest test suite for the application factory
function :func:`app.create_app` defined in :mod:`app.__init__`. It
exists to lock down — and prevent regression in — the factory's public
contract, which AAP §0.3.3 identifies as the CENTRAL design decision
of the entire Flask scaffold. Every other component of the runtime
(``wsgi.py``, the ``flask`` CLI, the pytest fixtures in
:mod:`tests.conftest`) reaches the running Flask instance through this
single function, so a regression here invalidates the entire scaffold.

What this module verifies
-------------------------
The eleven tests in this file cover the documented contract surface
of :func:`app.create_app` end-to-end:

1. The factory returns an instance of :class:`flask.Flask` (not a
   subclass-aware look-alike, not ``None``, not a tuple).
2. Passing ``"testing"`` loads :class:`app.config.TestingConfig`,
   making ``app.config["TESTING"]`` evaluate to :data:`True` — the
   single most important configuration invariant for the pytest
   suite per AAP §0.4.1 and §0.6.7.
3. ``TestingConfig`` supplies a hardcoded ``SECRET_KEY`` so the
   suite runs hermetically without reading the environment.
4-6. Each of the three documented Blueprints (``health``, ``main``,
   ``api``) is registered.
7. All three Blueprints are registered together (the most common
   factory regression — forgetting one).
8. The factory is deterministic: each call produces an independent
   :class:`flask.Flask` instance (essential for test isolation under
   the Application Factory pattern).
9. The factory's defensive fallback handles invalid ``config_name``
   strings gracefully (coerce to default, do not raise).
10. The factory configures the application logger so
    ``app.logger`` is wired and usable.
11. An end-to-end smoke test confirms the factory's output handles
    a real HTTP request via :meth:`flask.Flask.test_client`.

Relationship to sibling test modules
------------------------------------
Unlike :mod:`tests.test_main`, :mod:`tests.test_health`, and
:mod:`tests.test_api` — which exercise routed endpoints through the
``client`` fixture supplied by :mod:`tests.conftest` — this module
imports :func:`app.create_app` directly and invokes it from inside
each test. The direct invocation is intentional: several tests here
need to call the factory with NON-standard arguments (e.g.,
``"nonexistent_config_name"``) or repeatedly within the same test
(``app1 = create_app("testing"); app2 = create_app("testing")``) to
exercise behaviors that the ``app`` fixture cannot model. The
``conftest.py`` fixture surface (which itself calls
``create_app("testing")``) is left untouched by this module.

Test isolation contract
-----------------------
Each test function constructs its own fresh :class:`flask.Flask`
instance via :func:`app.create_app` and lets it go out of scope at
the end of the function. No global state is mutated by any test in
this module, so the suite is order-independent and trivially
parallelisable (e.g., under ``pytest-xdist``).

References
----------
* AAP §0.3.3 — Application Factory design pattern (central design
  decision; this module is the regression gate for that pattern).
* AAP §0.4.1 — Transformation table row for ``tests/test_app_factory.py``:
  "Assert ``create_app('testing')`` returns a Flask instance; assert
  ``app.config['TESTING'] is True``; assert blueprints registered".
* AAP §0.4.2 — Cross-file dependencies (import graph rooted at
  :func:`app.create_app`).
* AAP §0.6.7 — Cross-cutting concerns: test isolation via
  ``TESTING=True``.
* :mod:`app.__init__` — the :func:`create_app` function under test.
* :mod:`app.config` — the :class:`TestingConfig` selected by
  ``create_app("testing")``.
* :mod:`tests.conftest` — supplies the ``app`` / ``client`` /
  ``runner`` fixtures used by sibling test modules (intentionally
  unused here).
"""

from __future__ import annotations

from flask import Flask

from app import create_app

# =============================================================================
# 1. Flask instance contract
# =============================================================================
# The Application Factory pattern requires :func:`create_app` to return an
# instance of :class:`flask.Flask` (or, theoretically, a subclass). Tests
# rely on :func:`isinstance` rather than ``type(app) is Flask`` so that a
# future subclass-based extension (e.g., a custom application class that
# adds request-tracing hooks) remains compatible with the contract.


def test_create_app_returns_flask_instance() -> None:
    """Verify ``create_app('testing')`` returns a :class:`flask.Flask` instance.

    The factory's most fundamental contract is that it returns a Flask
    application object. A regression here (e.g., the factory returning
    ``None``, or accidentally returning the configuration object instead
    of the application) would cascade into every other test in the suite
    and into the production WSGI entry point, so this is the first thing
    we verify.
    """
    app = create_app("testing")
    assert isinstance(app, Flask), (
        f"Expected Flask instance from create_app('testing'), got {type(app).__name__}"
    )


# =============================================================================
# 2. TestingConfig loading contract
# =============================================================================
# Per AAP §0.4.1, the ``testing`` configuration profile MUST set
# ``TESTING = True`` so that Flask's testing-friendly behavior is enabled
# (exceptions propagate to the test client rather than being converted to
# HTTP 500 pages, et cetera). This single key is what makes the suite
# hermetic — without it, tests would observe Flask's production error
# handling and pass for the wrong reasons.


def test_create_app_loads_testing_config() -> None:
    """Verify ``create_app('testing')`` enables ``TESTING`` mode.

    The ``TestingConfig`` class in :mod:`app.config` sets
    ``TESTING = True``. Flask consults ``app.config["TESTING"]`` to
    decide whether to propagate exceptions to the test client. This
    test ensures the configuration profile was actually loaded and
    that ``TESTING`` is the strict boolean :data:`True` rather than
    a truthy proxy (e.g., the string ``"1"``).
    """
    app = create_app("testing")
    assert app.config["TESTING"] is True, (
        f"Expected app.config['TESTING'] is True, got {app.config.get('TESTING')!r}"
    )


# =============================================================================
# 3. Hermetic SECRET_KEY contract
# =============================================================================
# The ``TestingConfig`` overrides ``SECRET_KEY`` to a hardcoded value so
# tests run hermetically without needing the ``SECRET_KEY`` environment
# variable to be set. CI sandboxes commonly omit it, and tests that
# silently fall back to a ``None`` secret would surface as
# ``RuntimeError: The session is unavailable...`` deep inside the request
# handling layer — a confusing failure mode. The assertions below verify
# the property of "non-empty string secret" without pinning the literal
# value, allowing the implementation to rotate the test secret without
# breaking this test.


def test_create_app_testing_config_has_test_secret_key() -> None:
    """Verify ``create_app('testing')`` supplies a non-empty ``SECRET_KEY``.

    Per :class:`app.config.TestingConfig`, the ``SECRET_KEY`` attribute
    is hardcoded so the test suite runs without depending on the
    environment. This test asserts the property — a non-empty string —
    rather than the literal value, so the implementation can rotate the
    test secret (e.g., to silence a future secret-scanner false positive)
    without invalidating this test.
    """
    app = create_app("testing")
    secret = app.config.get("SECRET_KEY")
    assert secret is not None, "TestingConfig must define SECRET_KEY"
    assert isinstance(secret, str), f"Expected SECRET_KEY to be a str, got {type(secret).__name__}"
    assert len(secret) > 0, "TestingConfig SECRET_KEY must be non-empty"


# =============================================================================
# 4-6. Per-Blueprint registration contract
# =============================================================================
# The factory must register all three documented Blueprints. We verify
# each one in its own focused test so a regression that drops a single
# Blueprint surfaces as a single, unambiguously named test failure
# rather than as one omnibus assertion failure that requires reading the
# assertion body to diagnose. Blueprint names are checked against
# ``app.blueprints`` (Flask's dict mapping name → Blueprint instance);
# this is the canonical introspection surface.


def test_create_app_registers_health_blueprint() -> None:
    """Verify the ``health`` Blueprint is registered.

    The ``health`` Blueprint exposes the ``/healthz`` and ``/readyz``
    liveness and readiness probes consumed by orchestrators. Dropping
    it would cause Kubernetes liveness probes to fail and the pod to
    be restarted — a severe production regression that this test
    catches at the unit level.
    """
    app = create_app("testing")
    assert "health" in app.blueprints, (
        f"Expected 'health' in app.blueprints, got {sorted(app.blueprints.keys())}"
    )


def test_create_app_registers_main_blueprint() -> None:
    """Verify the ``main`` Blueprint is registered.

    The ``main`` Blueprint exposes the ``/`` and ``/version``
    service-identity endpoints. Dropping it would render the service's
    root URL a 404 — a less catastrophic regression than dropping
    ``health``, but still a contract violation per AAP §0.4.1.
    """
    app = create_app("testing")
    assert "main" in app.blueprints, (
        f"Expected 'main' in app.blueprints, got {sorted(app.blueprints.keys())}"
    )


def test_create_app_registers_api_blueprint() -> None:
    """Verify the ``api`` Blueprint is registered with ``url_prefix='/api'``.

    The ``api`` Blueprint is the ONLY scaffold Blueprint that carries a
    URL prefix per AAP §0.4.1. The prefix is mounted at Blueprint
    construction time (``Blueprint("api", __name__, url_prefix="/api")``)
    rather than at registration time, so this test cross-checks BOTH the
    presence of the Blueprint AND the URL prefix it carries. A
    regression that mounts the API at the root (no prefix) would cause
    routing collisions with the ``main`` Blueprint's ``/`` route.
    """
    app = create_app("testing")
    assert "api" in app.blueprints, (
        f"Expected 'api' in app.blueprints, got {sorted(app.blueprints.keys())}"
    )
    assert app.blueprints["api"].url_prefix == "/api", (
        f"Expected api Blueprint url_prefix='/api', got {app.blueprints['api'].url_prefix!r}"
    )


# =============================================================================
# 7. Joint Blueprint registration contract
# =============================================================================
# The per-Blueprint tests above each verify one Blueprint in isolation;
# this consolidated test verifies the COMPLETE set in a single assertion
# so the "factory forgot one Blueprint" regression surfaces with a
# pytest report that names the missing Blueprint set directly. We use
# :py:meth:`set.issubset` (not equality) so adding new Blueprints
# downstream — e.g., once the Node.js port introduces additional route
# groups — does not require updating this test in lock-step.


def test_create_app_registers_all_three_blueprints() -> None:
    """Verify all three scaffold Blueprints are registered together.

    Per AAP §0.3.1 and §0.4.1, the scaffold registers exactly three
    Blueprints: ``health``, ``main``, and ``api``. This test asserts
    the documented set is a SUBSET of the registered Blueprints (not
    equal-to), so future Blueprints added by downstream agents — for
    example, when the Node.js port introduces additional route groups —
    do not require this test to be updated in lock-step.
    """
    app = create_app("testing")
    expected = {"health", "main", "api"}
    actual = set(app.blueprints.keys())
    assert expected.issubset(actual), (
        f"Missing Blueprint(s) from create_app: "
        f"expected at minimum {expected}, got {actual}, "
        f"missing {expected - actual}"
    )


# =============================================================================
# 8. Determinism / per-call independence contract
# =============================================================================
# The Application Factory pattern's core promise is per-call
# independence: every call to :func:`create_app` returns a NEW
# :class:`flask.Flask` instance with no shared mutable state. This is
# the property that makes pytest fixtures hermetic — each test's
# fixture gets its own Flask instance, so a request handled in test A
# cannot mutate state observed in test B. A regression here (e.g., the
# factory accidentally caching a single instance via a module-level
# variable) would cause cross-test contamination that is notoriously
# hard to diagnose, so we test it explicitly.


def test_create_app_factory_is_deterministic() -> None:
    """Verify ``create_app`` returns independent Flask instances per call.

    The Application Factory pattern (AAP §0.3.3) requires that each call
    to :func:`create_app` materialises a NEW :class:`flask.Flask`
    instance — never a cached/shared singleton. Test isolation depends
    on this property: the pytest ``app`` fixture in
    :mod:`tests.conftest` builds a new application per test function,
    relying on the factory to produce independent objects.

    This test calls the factory twice and asserts:

    * The two returned objects are NOT the same instance (``is not``).
    * Both objects load the ``TestingConfig`` correctly (so we know the
      factory ran end-to-end on both calls, not a short-circuit that
      returned a stale cached instance).
    """
    app1 = create_app("testing")
    app2 = create_app("testing")
    assert app1 is not app2, (
        "create_app must return independent Flask instances per call; "
        "got the same object identity twice (cached singleton bug)"
    )
    assert app1.config["TESTING"] is True
    assert app2.config["TESTING"] is True


# =============================================================================
# 9. Invalid-config fallback contract
# =============================================================================
# Per :func:`app.create_app`'s defensive remap (``app/__init__.py``
# lines ~342-353), an unrecognized ``config_name`` is silently coerced
# to :data:`app.DEFAULT_CONFIG` rather than raising :class:`KeyError`.
# This protects production from a typo in the ``FLASK_CONFIG``
# environment variable taking the process down; the operator can still
# tell which config was selected from the startup log line. The test
# below verifies the call does not raise and that the returned object
# is still a Flask instance — it does NOT pin the specific fallback
# config, because that would couple this test to a default-name choice
# that may evolve.


def test_create_app_with_invalid_config_falls_back_to_default() -> None:
    """Verify ``create_app`` falls back to default config for unknown names.

    The factory's defensive coercion (``app/__init__.py``) turns any
    unrecognized ``config_name`` into :data:`app.DEFAULT_CONFIG`
    instead of raising :class:`KeyError`. This protects production
    from a misspelled ``FLASK_CONFIG=produktion`` environment variable
    crashing the process at startup.

    The test asserts only the structural properties of the fallback
    behavior (the call returns without raising; the returned object is
    a Flask instance). It deliberately avoids asserting which specific
    fallback config was selected, so the test remains stable if the
    documented default changes in the future.
    """
    app = create_app("nonexistent_config_name")
    # The fact that we reached this line at all already proves the
    # factory did not raise on the invalid name. The isinstance check
    # then proves the fallback path produced a usable Flask instance,
    # not (for example) ``None``.
    assert isinstance(app, Flask), (
        f"Expected Flask instance from create_app('nonexistent_config_name') "
        f"via default-config fallback, got {type(app).__name__}"
    )


# =============================================================================
# 10. Logger configuration contract
# =============================================================================
# The factory calls :func:`app.logging_config.configure_logging` as
# step 5 of the wiring sequence documented in ``app/__init__.py``. This
# test confirms the resulting Flask application exposes a usable
# logger via ``app.logger`` — Flask's per-app logger proxy — without
# diving into the structural details of the logging configuration
# (handler set, levels, formatters), which are exercised by integration
# tests dedicated to :mod:`app.logging_config`.


def test_create_app_logger_is_configured() -> None:
    """Verify ``create_app`` produces a Flask app with a usable logger.

    The factory's wiring sequence (``app/__init__.py``, step 5) calls
    :func:`app.logging_config.configure_logging` to set up logging
    before any other code path emits a log record. The Flask instance
    exposes ``app.logger`` as the canonical per-application logger
    proxy. This test verifies the logger attribute is present and
    supports the standard :py:class:`logging.Logger` API.

    The test deliberately does NOT assert on the configured log level,
    handlers, or formatter — those details belong in
    integration-level tests for :mod:`app.logging_config`. Here we
    only verify the factory wired the logger into a usable state.
    """
    app = create_app("testing")
    assert app.logger is not None, "app.logger must be present"
    # ``hasattr`` is preferred over ``isinstance(app.logger, Logger)``
    # because Flask wraps the underlying logger in a proxy
    # (``flask.app.Flask.logger`` is a cached property returning a
    # :class:`logging.Logger` in current versions; this duck-typed
    # check survives future internal refactors that swap in a proxy
    # wrapper as long as the public method surface is preserved).
    assert hasattr(app.logger, "info"), "app.logger must expose the standard Logger.info() API"
    assert hasattr(app.logger, "error"), "app.logger must expose the standard Logger.error() API"


# =============================================================================
# 11. End-to-end smoke test
# =============================================================================
# This is the canary test that catches the "factory completed but the
# application is broken" class of regression. A factory can register
# Blueprints, load configuration, and configure logging, and still
# produce an application that 500s on every request — e.g., due to a
# Blueprint registration ordering bug that leaves an endpoint
# unreachable, or a middleware that throws on the first request. By
# issuing a real HTTP request through :meth:`flask.Flask.test_client`
# and asserting the full response triple (status, content-type, body),
# this test verifies the factory's output is actually usable, not just
# structurally correct.


def test_create_app_can_handle_health_request() -> None:
    """End-to-end smoke test: factory output handles a health probe.

    Verifies that the Flask instance returned by
    ``create_app('testing')`` can route an HTTP request to the
    ``/healthz`` endpoint and return the documented JSON envelope.
    This single test catches the "factory completes but produces a
    non-functional app" class of regression — e.g., a Blueprint
    registration ordering bug that leaves the endpoint unreachable,
    or a middleware that throws on the first request.

    The :meth:`flask.Flask.test_client` context-manager form ensures
    the WSGI environment is torn down cleanly after the request, even
    if the assertion below fails.
    """
    app = create_app("testing")
    with app.test_client() as client:
        response = client.get("/healthz")
        # Status: liveness probes must return 200 OK so orchestrators
        # treat the container as healthy.
        assert response.status_code == 200, (
            f"Expected 200 from GET /healthz, got {response.status_code}; "
            f"body={response.get_data(as_text=True)!r}"
        )
        # Content type: liveness probe consumers expect JSON
        # (``Content-Type: application/json``); :func:`flask.jsonify`
        # sets it automatically. ``response.is_json`` consults the
        # parsed content type.
        assert response.is_json, (
            f"Expected JSON response from GET /healthz, got content-type "
            f"{response.headers.get('Content-Type')!r}"
        )
        # Body: the documented health envelope per
        # ``app/blueprints/health/routes.py``.
        assert response.get_json() == {"status": "ok"}, (
            f"Expected body {{'status': 'ok'}} from GET /healthz, got {response.get_json()!r}"
        )

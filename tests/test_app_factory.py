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

import logging
from typing import TYPE_CHECKING

from flask import Flask

from app import create_app
from app.logging_config import _resolve_log_level

if TYPE_CHECKING:
    # ``pytest.MonkeyPatch`` is the typed return value of the
    # function-scoped ``monkeypatch`` fixture pytest auto-injects when a
    # test requests it by name. Gating the import behind
    # ``TYPE_CHECKING`` keeps pytest's heavier symbols out of the runtime
    # import graph while still giving mypy the symbol to validate the
    # ``monkeypatch: pytest.MonkeyPatch`` parameter annotation used
    # below.
    import pytest

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
# step 5 of the wiring sequence documented in ``app/__init__.py``. The
# Checkpoint 3 review flagged the prior single test for asserting only
# that ``app.logger is not None`` and that it had ``info``/``error``
# attributes — assertions that would PASS even if
# ``configure_logging(app)`` were deleted from the factory, because
# Flask creates a default logger as a side effect of constructing a
# :class:`flask.Flask` instance.
#
# This section now contains TWO complementary tests that together lock
# down the logger-configuration contract robustly:
#
# 1. :func:`test_create_app_logger_is_configured` asserts the CONCRETE
#    side effects ``configure_logging`` produces — the logger level
#    matches :func:`app.logging_config._resolve_log_level`, the
#    factory-configured ``app`` named logger has at least one handler,
#    and ``propagate`` is the dictConfig-mandated ``False``. Each of
#    these differs from Flask's default-logger state (level
#    ``WARNING`` (30), no application-attached handlers, ``propagate``
#    inheriting Flask's default), so deleting the
#    ``configure_logging(app)`` call from the factory would cause
#    every assertion in this test to fail.
#
# 2. :func:`test_create_app_invokes_configure_logging` uses
#    :class:`pytest.MonkeyPatch` to spy on :func:`configure_logging`
#    and asserts the factory invokes it exactly once with the new
#    :class:`flask.Flask` instance. This catches the regression where
#    the configuration call is silently removed, even in a future
#    world where Flask's default logger state happens to match the
#    configured state.
#
# Together the two tests are belt-and-suspenders: side-effect
# assertions catch silent-corruption regressions; the call-spy
# assertion catches outright-removal regressions.


def test_create_app_logger_is_configured() -> None:
    """Verify ``create_app`` produces a configured logger (concrete side effects).

    Asserts the structural side effects produced by
    :func:`app.logging_config.configure_logging` so the test FAILS if
    that call is removed from the factory:

    1. ``app.logger`` exists and exposes the standard
       :class:`logging.Logger` interface (``info``, ``error``,
       ``exception``).
    2. The application-namespace logger (``logging.getLogger('app')``)
       has its level set to the value resolved from the ``LOG_LEVEL``
       environment variable by :func:`app.logging_config._resolve_log_level`.
       Flask's default is ``WARNING`` (30); after
       :func:`configure_logging` the level matches the resolved level
       (``INFO`` by default), so a mismatch indicates the dictConfig
       payload did not apply.
    3. The application-namespace logger has at least one handler
       attached. ``configure_logging`` installs a
       :class:`logging.StreamHandler` pointed at ``sys.stdout``;
       Flask's default-logger setup attaches a stderr handler to the
       Flask-app logger, not to the ``app`` named logger this
       assertion inspects. A zero-length handler list therefore
       indicates dictConfig did not run.
    4. The application-namespace logger has ``propagate`` set to
       :data:`False`. The Python logging defaults propagate to the
       root logger; ``configure_logging`` explicitly sets
       ``propagate=False`` on the ``app`` logger per the dictConfig
       payload in :func:`app.logging_config._build_logging_config`.
       The default :data:`True` value indicates dictConfig did not run.

    Independent verification (anti-regression rationale):

    The prior version of this test asserted only
    ``app.logger is not None`` and that it had ``info``/``error``
    attributes. That contract was satisfied by Flask's default logger
    creation alone — the test would have PASSED with
    ``configure_logging(app)`` deleted entirely from the factory. The
    Checkpoint 3 review surfaced this gap explicitly; the new
    assertions above each fail in that scenario, which the
    complementary :func:`test_create_app_invokes_configure_logging`
    test exercises directly via :class:`pytest.MonkeyPatch`.
    """
    app = create_app("testing")

    # ----- (1) Logger surface presence -----
    assert app.logger is not None, "app.logger must be present after create_app"
    assert hasattr(app.logger, "info"), "app.logger must expose Logger.info()"
    assert hasattr(app.logger, "error"), "app.logger must expose Logger.error()"
    assert hasattr(app.logger, "exception"), "app.logger must expose Logger.exception()"

    # ----- (2) Effective level matches resolved LOG_LEVEL -----
    # ``_resolve_log_level`` is the helper inside
    # :mod:`app.logging_config` that reads + validates the
    # ``LOG_LEVEL`` environment variable. Asserting equality of the
    # numeric value against the resolved level guarantees the
    # dictConfig payload was applied: Flask's default level is
    # ``WARNING`` (30) which would never coincidentally match the
    # ``INFO`` (20) default that ``_resolve_log_level`` returns.
    resolved_level_name = _resolve_log_level()
    expected_level = logging.getLevelName(resolved_level_name)
    assert isinstance(expected_level, int), (
        f"_resolve_log_level returned an unrecognised name {resolved_level_name!r}"
    )
    app_namespace_logger = logging.getLogger("app")
    assert app_namespace_logger.level == expected_level, (
        f"Expected app namespace logger level to match resolved "
        f"LOG_LEVEL '{resolved_level_name}' ({expected_level}), got "
        f"{logging.getLevelName(app_namespace_logger.level)} "
        f"({app_namespace_logger.level}); did configure_logging run?"
    )

    # ----- (3) At least one handler is attached -----
    # The dictConfig payload assigns the ``console`` handler to the
    # ``app`` namespace logger; with no configuration, the named
    # ``app`` logger has zero handlers (records propagate to the root
    # logger via the default ``propagate=True``). An empty handler
    # list therefore proves dictConfig did not run.
    assert len(app_namespace_logger.handlers) > 0, (
        "Expected the 'app' namespace logger to have at least one handler "
        "attached by configure_logging; got an empty handler list, which "
        "indicates the dictConfig payload did not apply (configure_logging "
        "was not called or was overridden)."
    )

    # ----- (4) propagate is explicitly False -----
    # The Python logging default is ``propagate=True``. The dictConfig
    # payload in :func:`app.logging_config._build_logging_config`
    # explicitly sets it to ``False`` on the ``app`` named logger so
    # records are not double-emitted by the root logger's handlers.
    # A ``True`` value here proves the dictConfig override did not run.
    assert app_namespace_logger.propagate is False, (
        f"Expected the 'app' namespace logger to have propagate=False "
        f"(the dictConfig-configured value), got "
        f"{app_namespace_logger.propagate!r}; did configure_logging run?"
    )


def test_create_app_invokes_configure_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify ``create_app`` calls ``configure_logging`` exactly once.

    Uses :meth:`pytest.MonkeyPatch.setattr` to install a spy in place of
    :func:`app.logging_config.configure_logging` BEFORE the application
    factory imports the symbol. Each invocation appends the positional
    argument (the :class:`flask.Flask` instance) to a list so the test
    can assert:

    1. The factory invoked the spy at least once.
    2. The factory invoked the spy exactly once per ``create_app``
       call (catches the regression where the call is duplicated, e.g.
       moved into a Blueprint registration step that runs per
       Blueprint).
    3. The argument received was the same Flask instance the factory
       returned (catches the regression where the call is preserved
       but moved to a stale module-level instance).

    Why a separate test from :func:`test_create_app_logger_is_configured`:

    The sibling test asserts the SIDE EFFECTS of ``configure_logging``
    (level, handlers, propagate). Side-effect assertions can be
    satisfied by other code paths in principle — for example, a future
    refactor that moves logging setup into a Flask ``before_request``
    hook would re-establish the side effects without
    ``configure_logging`` ever running. This call-spy test asserts the
    factory specifically invokes ``configure_logging``, which is the
    exact behaviour the AAP §0.4.2 import graph and ``app/__init__.py``
    docstring contract document. Belt and suspenders: silent corruption
    is caught by the side-effect test; outright removal is caught here.

    Args:
        monkeypatch: pytest-supplied :class:`pytest.MonkeyPatch`
            instance used to install the spy. The fixture
            automatically tears down after the test returns, so the
            real :func:`configure_logging` is restored before the next
            test runs.
    """
    # The spy records every (positional_args, keyword_args) pair it
    # was called with so the test can assert call count and the
    # specific app instance passed in.
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def _spy(*args: object, **kwargs: object) -> None:
        calls.append((args, kwargs))

    # IMPORTANT: monkeypatch the symbol on :mod:`app`, not on
    # :mod:`app.logging_config`. :func:`create_app` imports
    # ``configure_logging`` at module load time via ``from
    # app.logging_config import configure_logging``, which binds the
    # name to :mod:`app`'s namespace. Patching the source module
    # would not affect the already-bound reference inside :mod:`app`.
    monkeypatch.setattr("app.configure_logging", _spy)

    # Invoke the factory under spy. The spy is a no-op, so the
    # resulting Flask app has Flask's default (un-configured) logger
    # state — but that is fine for THIS test, whose only assertion
    # surface is the call record below.
    app = create_app("testing")

    assert len(calls) == 1, (
        f"Expected create_app to invoke configure_logging exactly once; "
        f"got {len(calls)} invocation(s): {calls!r}"
    )

    # The factory's wiring contract is ``configure_logging(app)`` —
    # one positional argument, no keyword arguments. Validating the
    # positional argument count protects against a future refactor
    # that calls ``configure_logging(app=app)`` (which would still
    # work but signal the call shape drifted from the contract).
    args, kwargs = calls[0]
    assert kwargs == {}, (
        f"Expected configure_logging to be called with no keyword arguments; got {kwargs!r}"
    )
    assert len(args) == 1, (
        f"Expected configure_logging to be called with exactly one "
        f"positional argument; got {len(args)}: {args!r}"
    )
    assert args[0] is app, (
        "Expected configure_logging to receive the Flask instance "
        "returned by create_app; got a different object."
    )


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

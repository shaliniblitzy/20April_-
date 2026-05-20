"""Tests for the ``health`` Blueprint — liveness and readiness probes.

Purpose
-------
This module is the pytest test suite for the :mod:`app.blueprints.health`
Blueprint. It exercises the two container-orchestrator probe endpoints
that the Blueprint exposes at the application root:

* ``GET /healthz`` — liveness probe; returns HTTP 200 with body exactly
  ``{"status": "ok"}``.
* ``GET /readyz``  — readiness probe; returns HTTP 200 with body exactly
  ``{"status": "ready"}``.

The :data:`app.blueprints.health.health_bp` Blueprint is registered
WITHOUT a ``url_prefix`` (see :mod:`app.blueprints.health.__init__` and
the ``app.register_blueprint(health_bp)`` call inside
:func:`app.create_app`), so the paths above are absolute. The trailing
``-z`` suffix matches the de-facto Kubernetes naming convention for
machine-readable probe endpoints; orchestrators (Kubernetes, Docker
Swarm, ECS, Nomad, most cloud load balancers) default to these
unprefixed paths.

Tight contract — exact equality
-------------------------------
Unlike the structural assertions in :mod:`tests.test_main` (which assert
only key presence, type, and non-emptiness so the suite remains green
across non-breaking wording revisions), the body assertions in this
module assert EXACT equality with ``{"status": "ok"}`` and
``{"status": "ready"}``. The rationale, captured in AAP §0.4.1, is that
orchestrators may match on the literal string values of the probe
response — adding or removing keys, mutating the status string, or
reordering would break those matches. This is therefore one of the
narrow contracts in the scaffold where loosening the assertion would
weaken the contract guarantee.

Fixtures
--------
All tests consume the ``app`` and ``client`` fixtures supplied by
:mod:`tests.conftest` (which pytest auto-discovers). The ``client``
fixture wraps :meth:`flask.Flask.test_client` and provides an in-process
HTTP transport that requires no live server. The ``app`` fixture yields
a configured :class:`flask.Flask` instance built via the application
factory under the ``TestingConfig`` profile (``TESTING=True``), ensuring
hermetic, order-independent test runs (AAP §0.6.7).

Coverage summary
----------------
This module verifies:

1. ``GET /healthz`` returns HTTP 200
   (:func:`test_healthz_returns_200`).
2. ``GET /healthz`` returns ``Content-Type: application/json``
   (:func:`test_healthz_returns_json_content_type`).
3. ``GET /healthz`` body is exactly ``{"status": "ok"}``
   (:func:`test_healthz_body_matches_documented_contract`).
4. ``GET /readyz`` returns HTTP 200
   (:func:`test_readyz_returns_200`).
5. ``GET /readyz`` returns ``Content-Type: application/json``
   (:func:`test_readyz_returns_json_content_type`).
6. ``GET /readyz`` body is exactly ``{"status": "ready"}``
   (:func:`test_readyz_body_matches_documented_contract`).
7. The ``health`` Blueprint is registered with ``url_prefix is None``
   (:func:`test_health_blueprint_is_registered`).
8. ``/healthz`` and ``/readyz`` are registered at the application root
   (:func:`test_health_routes_are_at_root_paths`).

References
----------
* AAP §0.4.1 — Transformation table row for ``tests/test_health.py``
  ("``GET /healthz`` returns 200 + ``{\"status\": \"ok\"}``; ``GET
  /readyz`` returns 200 + ``{\"status\": \"ready\"}``").
* AAP §0.6.7 — Cross-cutting concerns catalog: health/readiness
  isolated in its own Blueprint so liveness/readiness reasoning is
  independent of business-endpoint behaviour.
* AAP §0.7.2 — Preservation rules (tests must remain portable when the
  Node.js source becomes available).
* :mod:`app.blueprints.health` — Blueprint package; ``health_bp`` is
  registered with ``url_prefix=None``.
* :mod:`app.blueprints.health.routes` — handlers for ``healthz`` and
  ``readyz``.
* :mod:`tests.conftest` — supplies the ``app`` and ``client`` fixtures
  used throughout this module.
"""

from __future__ import annotations

from flask import Flask
from flask.testing import FlaskClient

# =============================================================================
# Tests for ``GET /healthz`` — liveness probe
# =============================================================================
# The liveness probe is the single most heavily-trafficked endpoint in
# a containerised deployment: Kubernetes ``livenessProbe`` defaults to
# polling it every 10 seconds for the lifetime of every pod. Any
# regression in this endpoint produces immediate, cascading pod
# restarts in production. The three tests below cover the three
# orthogonal dimensions of the endpoint's contract: status code,
# content type, and body shape.


def test_healthz_returns_200(client: FlaskClient) -> None:
    """Verify ``GET /healthz`` returns HTTP 200.

    The orchestrator-side ``livenessProbe`` decision (restart vs.
    leave-alone) is driven purely by the status code; a non-200
    response from ``/healthz`` would trigger pod restarts in
    Kubernetes. The handler is a static :func:`flask.jsonify` call
    whose default status is 200, so any deviation indicates either
    the Blueprint failed to mount or the handler raised an
    unexpected exception that the error-handler chain caught and
    re-rendered with a non-200 status.
    """
    response = client.get("/healthz")
    assert response.status_code == 200, (
        f"Expected 200 from GET /healthz, got {response.status_code}; "
        f"body={response.get_data(as_text=True)!r}"
    )


def test_healthz_returns_json_content_type(client: FlaskClient) -> None:
    """Verify ``GET /healthz`` returns ``Content-Type: application/json``.

    The handler uses :func:`flask.jsonify` which sets the canonical
    ``application/json`` Content-Type. Two checks are performed:

    * :attr:`flask.Response.is_json` — convenience boolean derived
      from the Content-Type header; ``True`` indicates Flask
      considers the response JSON-compatible.
    * :attr:`flask.Response.content_type` — the raw header value,
      which for :func:`flask.jsonify` responses begins with
      ``application/json`` (optionally followed by a ``; charset=...``
      suffix on some Flask configurations).

    Both checks defend against the misconfiguration where the handler
    returned a plain ``str`` (which would carry ``text/html``).
    """
    response = client.get("/healthz")
    assert response.is_json, (
        f"GET /healthz did not return JSON (content_type={response.content_type!r})"
    )
    assert response.content_type.startswith("application/json"), (
        f"Expected content_type starting with 'application/json', got {response.content_type!r}"
    )


def test_healthz_body_matches_documented_contract(client: FlaskClient) -> None:
    """Verify ``GET /healthz`` body is exactly ``{"status": "ok"}``.

    Per AAP §0.4.1, the body MUST be exactly ``{"status": "ok"}``.
    This is a TIGHT contract: orchestrators and external monitoring
    services may match on the literal string ``"ok"``, so the
    assertion uses exact dict equality rather than asserting only
    key presence. Adding extra keys, mutating the status string, or
    omitting the ``status`` key would all silently break downstream
    consumers that key off the documented shape.
    """
    response = client.get("/healthz")
    data = response.get_json()
    assert data == {"status": "ok"}, f"Expected exactly {{'status': 'ok'}}, got {data!r}"


# =============================================================================
# Tests for ``GET /readyz`` — readiness probe
# =============================================================================
# The readiness probe is consulted by Kubernetes ``readinessProbe`` and
# by upstream load balancers to decide whether to route traffic to
# this pod. A regression here causes traffic to either bypass a
# healthy pod (false negative — silent capacity loss) or be routed to
# an unhealthy pod (false positive — user-facing errors). The three
# tests below mirror the ``/healthz`` triplet, asserting status code,
# content type, and body shape independently.


def test_readyz_returns_200(client: FlaskClient) -> None:
    """Verify ``GET /readyz`` returns HTTP 200.

    The orchestrator-side ``readinessProbe`` decision (include in
    Service endpoints vs. drain) is driven purely by the status code;
    a non-200 response from ``/readyz`` would silently drain the pod
    from the upstream load balancer's rotation. The handler is a
    static :func:`flask.jsonify` call whose default status is 200,
    so any deviation indicates the Blueprint failed to mount or the
    handler raised an unexpected exception.
    """
    response = client.get("/readyz")
    assert response.status_code == 200, (
        f"Expected 200 from GET /readyz, got {response.status_code}; "
        f"body={response.get_data(as_text=True)!r}"
    )


def test_readyz_returns_json_content_type(client: FlaskClient) -> None:
    """Verify ``GET /readyz`` returns ``Content-Type: application/json``.

    The handler uses :func:`flask.jsonify` which sets the canonical
    ``application/json`` Content-Type. The two assertions mirror the
    sibling :func:`test_healthz_returns_json_content_type` test and
    guard against the same misconfiguration class (handler returning
    a plain ``str`` with ``text/html``).
    """
    response = client.get("/readyz")
    assert response.is_json, (
        f"GET /readyz did not return JSON (content_type={response.content_type!r})"
    )
    assert response.content_type.startswith("application/json"), (
        f"Expected content_type starting with 'application/json', got {response.content_type!r}"
    )


def test_readyz_body_matches_documented_contract(client: FlaskClient) -> None:
    """Verify ``GET /readyz`` body is exactly ``{"status": "ready"}``.

    Per AAP §0.4.1, the body MUST be exactly ``{"status": "ready"}``.
    Tight contract — orchestrators may match on the literal string
    ``"ready"``, so the assertion uses exact dict equality rather
    than asserting only key presence. Adding extra keys, mutating
    the status string, or omitting the ``status`` key would all
    silently break downstream consumers that key off the documented
    shape.
    """
    response = client.get("/readyz")
    data = response.get_json()
    assert data == {"status": "ready"}, f"Expected exactly {{'status': 'ready'}}, got {data!r}"


# =============================================================================
# Tests for the Blueprint registration contract
# =============================================================================
# The two tests below guard against the misconfiguration class where
# the routes ARE registered (so the per-endpoint tests above pass) but
# under the wrong mount point — for example, if a ``url_prefix`` were
# added to the Blueprint or at registration time, the per-endpoint
# tests would still pass against ``/health/healthz`` but the routes
# would no longer be where orchestrators expect them. These tests
# inspect the Flask URL map directly so a silent route-relocation is
# caught.


def test_health_blueprint_is_registered(app: Flask) -> None:
    """Verify the ``health`` Blueprint is registered with no ``url_prefix``.

    Two invariants are checked:

    1. The Blueprint name ``"health"`` appears as a key in
       :attr:`flask.Flask.blueprints` — confirming the application
       factory's ``app.register_blueprint(health_bp)`` call ran
       successfully.
    2. ``health_bp.url_prefix is None`` — confirming the Blueprint is
       mounted at the application root, not under a prefix. The
       ``health`` Blueprint is one of TWO prefix-less Blueprints in
       the scaffold (the other being ``main``); ``api`` is the only
       Blueprint that carries a prefix (``/api``). Accidentally
       adding a prefix here (either at Blueprint construction or at
       registration) would relocate ``/healthz`` and ``/readyz``
       under that prefix and silently break orchestrator probes.

    Uses the ``app`` fixture from :mod:`tests.conftest` (the
    ``client`` fixture is not needed because the assertion inspects
    the Flask application object directly, not the HTTP surface).
    """
    assert "health" in app.blueprints, (
        f"'health' Blueprint missing from app.blueprints; registered names: "
        f"{sorted(app.blueprints.keys())}"
    )
    health_blueprint = app.blueprints["health"]
    assert health_blueprint.url_prefix is None, (
        f"Expected url_prefix=None for the 'health' Blueprint, got "
        f"{health_blueprint.url_prefix!r}; adding a prefix would relocate "
        f"/healthz and /readyz and silently break orchestrator probes."
    )


def test_health_routes_are_at_root_paths(app: Flask) -> None:
    """Verify ``/healthz`` and ``/readyz`` are registered at the application root.

    Iterates :attr:`flask.Flask.url_map` rules, filters to rules whose
    endpoint name begins with ``health.`` (the Flask convention is
    ``<blueprint_name>.<view_func>`` — so the ``health`` Blueprint's
    handlers are ``health.healthz`` and ``health.readyz``), and
    asserts both expected absolute paths are present.

    This is a defence-in-depth complement to
    :func:`test_health_blueprint_is_registered`: the latter checks
    that the Blueprint is mounted without a prefix, while this test
    checks that the rule paths actually materialise at the expected
    absolute paths. The two assertions together catch the misconfig
    where a route is silently renamed (e.g.
    ``@health_bp.get("/healthcheck")`` instead of
    ``@health_bp.get("/healthz")``) — that change would pass the
    Blueprint-registration test but fail this one.

    Uses the ``app`` fixture from :mod:`tests.conftest`.
    """
    rules = {rule.rule for rule in app.url_map.iter_rules() if rule.endpoint.startswith("health.")}
    assert "/healthz" in rules, f"'/healthz' not found in health Blueprint rules: {sorted(rules)}"
    assert "/readyz" in rules, f"'/readyz' not found in health Blueprint rules: {sorted(rules)}"

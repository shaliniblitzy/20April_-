"""Tests for the ``main`` Blueprint — service-identity endpoints.

Purpose
-------
This module is the pytest test suite for the :mod:`app.blueprints.main`
Blueprint. It exercises the two service-identity endpoints exposed at the
application root (the Blueprint is registered WITHOUT a ``url_prefix``,
so its routes are absolute paths):

* ``GET /``         — service banner JSON envelope with keys
                       ``service``, ``message``, ``endpoints``.
* ``GET /version``  — service identification JSON envelope with keys
                       ``name``, ``version``, ``python``.

Fixtures
--------
All tests consume the ``app`` and ``client`` fixtures supplied by
:mod:`tests.conftest` (which is auto-discovered by pytest). The
``client`` fixture wraps :meth:`flask.Flask.test_client` and provides an
in-process HTTP transport that requires no live server. The ``app``
fixture yields a configured :class:`flask.Flask` instance built via the
application factory under the ``TestingConfig`` profile
(``TESTING=True``), ensuring hermetic, order-independent test runs.

Type-checking imports
---------------------
The :class:`flask.Flask` and :class:`flask.testing.FlaskClient` types
are imported under a :data:`typing.TYPE_CHECKING` guard so they are
available to static type-checkers (mypy) without being loaded at
runtime. This is the checkpoint-prescribed pattern for fixture-only
type annotations: pytest's parameter-injection mechanism does not
introspect annotations at import time, so the types need not be
present at runtime — but the annotations remain machine-readable for
IDEs and type-checkers.

Test structure
--------------
Tests are split into focused per-key/per-assertion functions rather
than aggregating multiple assertions into one omnibus test. This
granularity:

* Surfaces the exact key/assertion that failed in pytest's report,
  rather than a single "envelope shape" failure that requires reading
  the assertion body to diagnose.
* Lets the suite be filtered with ``pytest -k <name>`` to target a
  specific contract dimension during local debugging.
* Mirrors the per-key contract structure documented in AAP §0.4.1 and
  in the Checkpoint 2 review's prescribed skeleton.

Design intent
-------------
These tests are written defensively against the (currently absent)
Node.js source the user requested be ported. They assert structural
invariants of the response envelopes (key presence, types, semver-like
shape) rather than exact string values, so the suite remains stable as
the scaffold evolves (e.g., when ``version`` bumps from ``0.1.0`` or
when the test environment Python version changes). Per AAP §0.7.2,
this preservation-rules portability is a hard requirement: when the
Node source is supplied and ported into the Blueprint, these tests
must continue to pass without modification.

References
----------
* AAP §0.4.1 — Transformation table row for ``tests/test_main.py``
  ("``GET /`` returns 200 + JSON envelope; ``GET /version`` returns
  200 + JSON with expected keys").
* AAP §0.7.2 — Preservation rules (tests must be portable when source
  becomes available).
* :mod:`app.blueprints.main` — Blueprint package; ``main_bp`` is
  registered with ``url_prefix=None``.
* :mod:`tests.conftest` — supplies the ``app`` and ``client``
  fixtures used throughout this module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Imports gated by TYPE_CHECKING are evaluated by static type-checkers
    # (mypy) but skipped at runtime — they exist solely to give pytest
    # fixture parameters (``app: Flask``, ``client: FlaskClient``) typed
    # annotations without forcing the costlier ``flask.testing`` import at
    # test-collection time. ``from __future__ import annotations`` (above)
    # makes ALL annotations strings at runtime, so these names need only
    # resolve during static analysis. This is the checkpoint-prescribed
    # pattern for fixture-only type annotations.
    from flask import Flask
    from flask.testing import FlaskClient


# =============================================================================
# Tests for ``GET /`` (service banner)
# =============================================================================
# The index endpoint is the entrypoint of the service-identity surface.
# It must:
#
#   * Return HTTP 200 OK.
#   * Be content-type ``application/json`` (set by ``flask.jsonify``).
#   * Carry a JSON object with the three documented keys ``service``,
#     ``message``, ``endpoints``.
#   * The ``endpoints`` list must enumerate the helper paths advertised
#     by the scaffold (``/healthz``, ``/readyz``, ``/version``, ``/api/``)
#     so operators discover them from a single request to the root.
#
# Each property is asserted by its own focused test function so the
# pytest report points directly to the failing key/dimension without
# requiring inspection of an omnibus assertion body. Exact string values
# (e.g., ``service`` text, ``message`` wording) are deliberately NOT
# pinned to tolerate non-breaking wording revisions and to preserve
# portability when the Node.js source is eventually ported.


def test_index_returns_200(client: FlaskClient) -> None:
    """Verify ``GET /`` returns HTTP 200.

    The handler is a synchronous Flask view that produces a JSON banner
    via :func:`flask.jsonify`, which sets the default status code 200.
    A non-200 status here would indicate either the Blueprint is not
    mounted, or the handler raised an exception that was caught by the
    error handler (which would also change the response shape).
    """
    response = client.get("/")
    assert response.status_code == 200, (
        f"Expected 200 from GET /, got {response.status_code}; "
        f"body={response.get_data(as_text=True)!r}"
    )


def test_index_content_type_is_json(client: FlaskClient) -> None:
    """Verify ``GET /`` returns ``Content-Type: application/json``.

    The Flask :class:`~flask.Response` object exposes:

    * ``is_json``      — convenience boolean derived from the
                          Content-Type header.
    * ``content_type`` — the raw header value, which for ``jsonify``
                          responses is the canonical
                          ``application/json`` (optionally with a
                          ``; charset=...`` suffix on some Flask
                          configurations).

    Both checks are asserted to defend against the misconfiguration
    where the handler returned a plain ``str`` (which would carry
    ``text/html``).
    """
    response = client.get("/")
    assert response.is_json, f"GET / did not return JSON (content_type={response.content_type!r})"
    assert response.content_type.startswith("application/json"), (
        f"Expected content_type starting with 'application/json', got {response.content_type!r}"
    )


def test_index_envelope_has_service_key(client: FlaskClient) -> None:
    """Verify ``GET /`` body includes a non-empty ``service`` string.

    The ``service`` key carries the human-readable identifier of the
    running scaffold. The exact string value is intentionally NOT
    pinned (per AAP §0.7.2 portability rules) — only its presence,
    type, and non-emptiness are asserted so the test remains green
    when the upstream Node.js source is ported and brings its own
    canonical service name.
    """
    response = client.get("/")
    data = response.get_json()

    assert isinstance(data, dict), (
        f"Expected JSON object (dict) at GET /, got {type(data).__name__}: {data!r}"
    )
    assert "service" in data, f"Missing 'service' key in GET / body: {data!r}"
    assert isinstance(data["service"], str), (
        f"'service' must be a string, got {type(data['service']).__name__}"
    )
    assert len(data["service"]) > 0, "'service' must be a non-empty string"


def test_index_envelope_has_message_key(client: FlaskClient) -> None:
    """Verify ``GET /`` body includes a non-empty ``message`` string.

    The ``message`` key carries a brief description of the running
    scaffold. The exact string value is intentionally NOT pinned (per
    AAP §0.7.2 portability rules) — only its presence, type, and
    non-emptiness are asserted so the test remains green across
    non-breaking wording revisions.
    """
    response = client.get("/")
    data = response.get_json()

    assert isinstance(data, dict), (
        f"Expected JSON object (dict) at GET /, got {type(data).__name__}: {data!r}"
    )
    assert "message" in data, f"Missing 'message' key in GET / body: {data!r}"
    assert isinstance(data["message"], str), (
        f"'message' must be a string, got {type(data['message']).__name__}"
    )
    assert len(data["message"]) > 0, "'message' must be a non-empty string"


def test_index_envelope_has_endpoints_key(client: FlaskClient) -> None:
    """Verify ``GET /`` body includes a non-empty ``endpoints`` list.

    The ``endpoints`` key carries a list of helper paths advertised
    by the scaffold. This test asserts only the structural properties
    (presence, list type, non-emptiness); the specific paths the list
    must contain are exercised by
    :func:`test_index_endpoints_includes_expected_paths` below.
    """
    response = client.get("/")
    data = response.get_json()

    assert isinstance(data, dict), (
        f"Expected JSON object (dict) at GET /, got {type(data).__name__}: {data!r}"
    )
    assert "endpoints" in data, f"Missing 'endpoints' key in GET / body: {data!r}"
    assert isinstance(data["endpoints"], list), (
        f"'endpoints' must be a list, got {type(data['endpoints']).__name__}"
    )
    assert len(data["endpoints"]) > 0, "'endpoints' list must not be empty"


def test_index_endpoints_includes_expected_paths(client: FlaskClient) -> None:
    """Verify the ``endpoints`` list documents the helper paths.

    The index banner must advertise the helper routes the rest of the
    scaffold exposes so operators can discover them from a single
    request to ``/``. ``set.issubset`` is used (rather than equality)
    so the implementation may add additional paths in the future
    without breaking this test — only the documented minimum is
    enforced. The minimum set comes from the
    :mod:`app.blueprints.main.routes` agent prompt:

    * ``/healthz``   — liveness probe (health Blueprint).
    * ``/readyz``    — readiness probe (health Blueprint).
    * ``/version``   — service identification (main Blueprint).
    * ``/api/``      — API surface mount point (api Blueprint).
    """
    response = client.get("/")
    data = response.get_json()
    endpoints = data["endpoints"]

    assert isinstance(endpoints, list), (
        f"'endpoints' must be a list, got {type(endpoints).__name__}"
    )

    # Required minimum set of helper paths advertised by the banner.
    expected_endpoints = {"/healthz", "/readyz", "/version", "/api/"}
    actual_endpoints = set(endpoints)

    assert expected_endpoints.issubset(actual_endpoints), (
        f"Expected endpoints {sorted(expected_endpoints)} to be a subset of "
        f"advertised endpoints {sorted(actual_endpoints)}; missing: "
        f"{sorted(expected_endpoints - actual_endpoints)}"
    )


# =============================================================================
# Tests for ``GET /version`` (service identification)
# =============================================================================
# The version endpoint identifies the running build to load balancers,
# canary verifiers, and operator tooling. It must:
#
#   * Return HTTP 200 OK.
#   * Be content-type ``application/json``.
#   * Carry a JSON object with the three documented keys ``name``,
#     ``version``, ``python``.
#   * ``python`` should be the runtime version reported by
#     :func:`platform.python_version` (e.g., ``"3.12.3"``), which is
#     environment-dependent.
#   * ``version`` should follow a semver-like ``MAJOR.MINOR[.PATCH]``
#     pattern (e.g., ``"0.1.0"``).
#
# Specific values are deliberately NOT pinned so the suite tolerates
# both build-version bumps and varied test environments
# (Python 3.10/3.11/3.12/3.13 are all supported per AAP §0.5.1).


def test_version_returns_200(client: FlaskClient) -> None:
    """Verify ``GET /version`` returns HTTP 200.

    Same rationale as :func:`test_index_returns_200`: a non-200 here
    signals either a missing route registration or a handler exception
    that was caught by the centralised error handler in
    :mod:`app.errors`.
    """
    response = client.get("/version")
    assert response.status_code == 200, (
        f"Expected 200 from GET /version, got {response.status_code}; "
        f"body={response.get_data(as_text=True)!r}"
    )


def test_version_content_type_is_json(client: FlaskClient) -> None:
    """Verify ``GET /version`` returns ``Content-Type: application/json``.

    Mirrors :func:`test_index_content_type_is_json` — both
    handlers must return JSON via :func:`flask.jsonify`, which sets
    the canonical ``application/json`` content type.
    """
    response = client.get("/version")
    assert response.is_json, (
        f"GET /version did not return JSON (content_type={response.content_type!r})"
    )
    assert response.content_type.startswith("application/json"), (
        f"Expected content_type starting with 'application/json', got {response.content_type!r}"
    )


def test_version_has_required_keys(client: FlaskClient) -> None:
    """Verify ``GET /version`` body has the required keys ``name``, ``version``, ``python``.

    Expected JSON envelope shape per AAP §0.4.1::

        {
            "name":    <non-empty string>,
            "version": <non-empty string>,
            "python":  <non-empty string>,
        }

    Exact string values are not pinned: ``version`` will bump as the
    project evolves (per :data:`app.__version__` and the corresponding
    :mod:`pyproject.toml` ``[project].version``); ``python`` is the
    runtime version which varies by test environment; and ``name`` may
    evolve when the upstream Node.js source is ported and brings its
    own canonical service name.
    """
    response = client.get("/version")
    data = response.get_json()

    assert isinstance(data, dict), (
        f"Expected JSON object (dict) at GET /version, got {type(data).__name__}: {data!r}"
    )
    assert "name" in data, f"Missing 'name' key in GET /version body: {data!r}"
    assert "version" in data, f"Missing 'version' key in GET /version body: {data!r}"
    assert "python" in data, f"Missing 'python' key in GET /version body: {data!r}"

    assert isinstance(data["name"], str), (
        f"'name' must be a string, got {type(data['name']).__name__}"
    )
    assert len(data["name"]) > 0, "'name' must be a non-empty string"

    assert isinstance(data["version"], str), (
        f"'version' must be a string, got {type(data['version']).__name__}"
    )
    assert len(data["version"]) > 0, "'version' must be a non-empty string"

    assert isinstance(data["python"], str), (
        f"'python' must be a string, got {type(data['python']).__name__}"
    )
    assert len(data["python"]) > 0, "'python' must be a non-empty string"


def test_version_value_matches_pattern(client: FlaskClient) -> None:
    """Verify ``GET /version``'s ``version`` field follows a semver-like pattern.

    Validates the structural shape ``MAJOR.MINOR[.PATCH][-PRERELEASE][+BUILD]``
    rather than a specific value, so the test remains green as the
    scaffold version evolves from its initial ``"0.1.0"``. Pre-release
    suffixes (``"-alpha"``, ``"-rc.1"``) and build-metadata suffixes
    (``"+build.123"``) on the patch component are tolerated by
    stripping them before the digit check.

    Validation strategy:

    1. Split the declared version on ``"."`` — expect at least
       ``major.minor`` (2 components).
    2. For each of the first three components, strip pre-release
       (``-...``) and build-metadata (``+...``) suffixes and assert
       the remaining characters are all digits.

    Notes
    -----
    * Only the first three components are checked — extra components
      (e.g., a build-id suffix appended as a fourth segment) are
      ignored to remain forward-compatible with internal versioning
      conventions.
    """
    response = client.get("/version")
    data = response.get_json()
    declared_version = data["version"]

    parts = declared_version.split(".")
    assert len(parts) >= 2, (
        f"Version should have at least major.minor components, "
        f"got {declared_version!r} (parts={parts!r})"
    )

    # Validate the first three components (or fewer if the version has
    # only two). Strip pre-release/build suffixes before the digit check.
    for part in parts[:3]:
        # ``"0-alpha"`` → ``"0"``; ``"3+build.7"`` → ``"3"``.
        digit_part = part.split("-")[0].split("+")[0]
        assert digit_part.isdigit(), (
            f"Version component {part!r} is not a recognisable semver number "
            f"(stripped: {digit_part!r}; full version: {declared_version!r})"
        )


def test_version_python_runtime_is_valid(client: FlaskClient) -> None:
    """Verify ``GET /version``'s ``python`` field looks like a Python version string.

    :func:`platform.python_version` returns strings such as ``"3.12.3"``
    or ``"3.11.10"`` — major.minor.patch components separated by dots.
    This test catches the bug class where a handler accidentally
    returned a placeholder like ``"unknown"``, an empty string, or an
    unrelated identifier (these would all pass the type/empty checks
    in :func:`test_version_has_required_keys` but fail here).

    Validation strategy:

    1. Split the version on ``"."``.
    2. Require at least 2 components (``major.minor``); Python release
       strings always have 3 (``major.minor.patch``) but a 2-component
       form would still be parseable.
    3. Require the first two components (the major and minor numbers)
       to be entirely digit characters — Python's major is always
       ``"3"`` for Python 3.x and minor is always a non-negative int.

    Specific version numbers are NOT asserted because tests must run
    on any Python 3.10+ environment per ``requires-python`` in
    ``pyproject.toml``.
    """
    response = client.get("/version")
    data = response.get_json()
    python_version = data["python"]

    parts = python_version.split(".")
    assert len(parts) >= 2, (
        f"Expected python version with at least major.minor, "
        f"got {python_version!r} (parts={parts!r})"
    )

    # Major version must be a positive integer (Python's major is "3").
    assert parts[0].isdigit(), (
        f"Major version component not numeric: {parts[0]!r} (full version: {python_version!r})"
    )

    # Minor version must be a non-negative integer.
    assert parts[1].isdigit(), (
        f"Minor version component not numeric: {parts[1]!r} (full version: {python_version!r})"
    )


# =============================================================================
# Blueprint-registration smoke test
# =============================================================================
# A direct introspection of the :class:`flask.Flask` instance ensures the
# Blueprint is wired into the application factory the way the design
# intends — name ``"main"``, no ``url_prefix``. This catches a class of
# regressions that the HTTP-layer tests can miss (for example, a
# Blueprint registered under a prefix would still respond to its routes
# at the prefixed path, so the HTTP tests would silently fail — this
# introspection test pins the contract explicitly).


def test_main_blueprint_is_registered(app: Flask) -> None:
    """Verify the ``main`` Blueprint is registered with no ``url_prefix``.

    The :attr:`flask.Flask.blueprints` attribute is a ``dict[str,
    flask.Blueprint]`` keyed by the Blueprint *name*. After the
    application factory runs ``app.register_blueprint(main_bp)``, the
    key ``"main"`` must be present and the resulting Blueprint must
    have ``url_prefix is None`` (mounting its routes at absolute paths).

    Sister Blueprints' expectations:

    * ``"health"`` — also has ``url_prefix=None`` (asserted in
      :mod:`tests.test_health`).
    * ``"api"``    — has ``url_prefix="/api"`` (asserted in
      :mod:`tests.test_api`).

    Catching a misconfiguration here (e.g., someone accidentally added
    ``url_prefix="/v1"`` at Blueprint construction or at registration)
    is critical because external probes hit ``/`` and ``/version``
    unconditionally — relocating them is a silent-break change.
    """
    assert "main" in app.blueprints, (
        f"'main' Blueprint missing from app.blueprints "
        f"(registered: {sorted(app.blueprints.keys())!r})"
    )

    main_blueprint = app.blueprints["main"]
    assert main_blueprint.url_prefix is None, (
        f"Expected url_prefix=None for main Blueprint, got {main_blueprint.url_prefix!r}"
    )

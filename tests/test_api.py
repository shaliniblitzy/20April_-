"""Tests for the ``api`` Blueprint — placeholder smoke tests.

Purpose
-------
This module is the pytest smoke-test suite for the
:mod:`app.blueprints.api` Blueprint. It exercises the *placeholder*
endpoint that the Blueprint exposes under its mount point
``/api/*`` while the repository awaits the original Node.js source
referenced in the user directive (see Agent Action Plan (AAP)
§0.6.1 and §0.7.4 for the precondition gap and the open
clarification questions, respectively).

Mount point
-----------
The :data:`app.blueprints.api.api_bp` Blueprint is the ONLY Blueprint
in the scaffold that carries a URL prefix; the sibling Blueprints
:mod:`app.blueprints.health` and :mod:`app.blueprints.main` mount at
the application root (no prefix). The Blueprint is instantiated as::

    api_bp = Blueprint("api", __name__, url_prefix="/api")

The placeholder handler is registered on the Blueprint at the route
``"/"``. Because the URL prefix ``"/api"`` is composed with the
route ``"/"``, the externally addressable URL is ``/api/`` — the
trailing slash matters. Werkzeug's default ``strict_slashes=True``
causes requests to ``/api`` (without trailing slash) to receive an
HTTP 308 Permanent Redirect to ``/api/``; this redirect behaviour is
exercised by :func:`test_api_root_without_trailing_slash_redirects`.

Placeholder contract
--------------------
Until the original Node.js source is supplied (AAP §0.7.4), the
``api`` Blueprint hosts exactly one handler bound to ``GET /api/``
that returns:

* HTTP status ``501 Not Implemented`` — the IANA-canonical code for
  a request whose method is recognised by the server but the
  functionality required to satisfy it has not been implemented.
* ``Content-Type: application/json`` — set automatically by
  :func:`flask.jsonify`.
* JSON body — the centralized error envelope from :mod:`app.errors`
  extended with a placeholder-only ``detail`` field::

      {
          "error": {
              "code": 501,
              "message": "Not Implemented",
              "detail": <string referencing the Node.js port / AAP §0.7.4>
          }
      }

When ported endpoints replace the placeholder, this module becomes
the natural location to expand coverage with route-specific tests
(per AAP §0.7.2, tests must remain portable across that transition).

Fixtures
--------
All tests consume the ``app`` and ``client`` fixtures supplied by
:mod:`tests.conftest` (which pytest auto-discovers). The ``client``
fixture wraps :meth:`flask.Flask.test_client` and provides an
in-process HTTP transport that requires no live server. The ``app``
fixture yields a configured :class:`flask.Flask` instance built via
the application factory under the ``TestingConfig`` profile
(``TESTING=True``), ensuring hermetic, order-independent test runs
(AAP §0.6.7).

Coverage summary
----------------
This module verifies:

1. ``GET /api/`` returns HTTP 501
   (:func:`test_api_placeholder_returns_501`).
2. ``GET /api/`` returns ``Content-Type: application/json``
   (:func:`test_api_placeholder_returns_json_content_type`).
3. ``GET /api/`` body matches the error envelope shape
   ``{"error": {"code": 501, "message": "Not Implemented",
   "detail": <str>}}`` (:func:`test_api_placeholder_envelope_shape`).
4. The ``api`` Blueprint is registered with ``url_prefix="/api"``
   (:func:`test_api_blueprint_is_registered`).
5. ``GET /api`` (no trailing slash) redirects to ``/api/`` and the
   redirect ultimately resolves to the 501 placeholder
   (:func:`test_api_root_without_trailing_slash_redirects`).

References
----------
* AAP §0.4.1 — Transformation table row for ``tests/test_api.py``:
  "Smoke-test API blueprint mount-point at ``/api/`` returns the
  documented placeholder response".
* AAP §0.6.1 — Precondition gap (no Node source available).
* AAP §0.6.7 — Cross-cutting concerns catalog (test isolation via
  ``TESTING=True``).
* AAP §0.7.2 — Preservation rules (tests must remain portable when
  the Node.js source becomes available).
* AAP §0.7.4 — Open Questions Requiring User Clarification.
* :mod:`app.blueprints.api` — Blueprint package; ``api_bp`` is
  registered with ``url_prefix="/api"``.
* :mod:`app.blueprints.api.routes` — placeholder handler returning
  the 501 envelope.
* :mod:`app.errors` — centralized error envelope shape
  ``{"error": {"code": ..., "message": ...}}`` that the placeholder
  mirrors and extends with a ``detail`` field.
* :mod:`tests.conftest` — supplies the ``app`` and ``client``
  fixtures used throughout this module.
"""

from __future__ import annotations

from flask import Flask
from flask.testing import FlaskClient

# =============================================================================
# Tests for ``GET /api/`` — placeholder endpoint contract
# =============================================================================
# The placeholder is the single endpoint mounted on the ``api`` Blueprint
# until the original Node.js source is supplied (AAP §0.6.1, §0.7.4). The
# three tests below cover the three orthogonal dimensions of the
# endpoint's documented contract: status code, content type, and body
# shape. Each property is asserted by its own focused test so the pytest
# report points directly to the failing dimension without requiring
# inspection of an omnibus assertion body.


def test_api_placeholder_returns_501(client: FlaskClient) -> None:
    """Verify ``GET /api/`` returns HTTP 501 Not Implemented.

    The API blueprint placeholder is mounted at ``/api/`` (the
    trailing slash matters: the Blueprint's ``url_prefix="/api"``
    composes with the route ``"/"`` to produce the externally
    addressable URL ``"/api/"``). Until the Node.js source is
    ported, this endpoint returns HTTP 501 with a JSON envelope
    explaining the precondition gap (AAP §0.6.1, §0.7.4).

    The IANA-canonical 501 status was chosen (per the
    ``app/blueprints/api/routes.py`` agent prompt) because it
    precisely describes the situation: the server recognises the
    method but has not implemented the functionality. A 503
    Service Unavailable would be misleading (the service is up;
    only the API surface is unimplemented); a 404 Not Found would
    falsely imply the endpoint URL itself is unknown. The
    placeholder handler is intentionally side-effect-free and
    will not raise — so any non-501 response indicates either the
    Blueprint failed to mount or an unexpected exception was
    caught by the centralized error handler in :mod:`app.errors`.
    """
    response = client.get("/api/")
    assert response.status_code == 501, (
        f"Expected 501 from GET /api/, got {response.status_code}; "
        f"body={response.get_data(as_text=True)!r}"
    )


def test_api_placeholder_returns_json_content_type(client: FlaskClient) -> None:
    """Verify ``GET /api/`` returns ``Content-Type: application/json``.

    The placeholder handler uses :func:`flask.jsonify` which sets
    the canonical ``application/json`` Content-Type. Two checks
    are performed:

    * :attr:`flask.Response.is_json` — convenience boolean derived
      from the Content-Type header; ``True`` indicates Flask
      considers the response JSON-compatible.
    * :attr:`flask.Response.content_type` — the raw header value,
      which for :func:`flask.jsonify` responses begins with
      ``application/json`` (optionally followed by a ``; charset=...``
      suffix on some Flask configurations). The ``startswith``
      check accommodates both forms without locking the exact
      charset suffix.

    This is critical for orchestrators, CI tools, and downstream
    API clients that parse responses based on the Content-Type
    header. A regression where the handler returned a plain string
    (carrying ``text/html``) would silently break those consumers.
    """
    response = client.get("/api/")
    assert response.is_json, (
        f"GET /api/ did not return JSON (content_type={response.content_type!r})"
    )
    assert response.content_type.startswith("application/json"), (
        f"Expected content_type starting with 'application/json', got {response.content_type!r}"
    )


def test_api_placeholder_envelope_shape(client: FlaskClient) -> None:
    """Verify ``GET /api/`` response envelope has the documented shape.

    Expected JSON body per the
    :mod:`app.blueprints.api.routes` agent prompt and the
    centralized error envelope from :mod:`app.errors`::

        {
            "error": {
                "code": 501,
                "message": "Not Implemented",
                "detail": <string referencing the Node.js port / AAP §0.7.4>
            }
        }

    The outer ``{"error": {"code": <int>, "message": <str>}}``
    shape is the universal error contract from :mod:`app.errors`
    (registered by :func:`app.errors.register_error_handlers`); the
    nested ``detail`` field is a placeholder-only extension that
    documents the precondition gap from AAP §0.6.1 and points
    operators at AAP §0.7.4 for the open clarification questions.

    Assertions are made incrementally (top-level dict → ``error``
    key → nested dict → fields) so a regression at any level
    surfaces in pytest's report as the exact dimension that broke,
    rather than as one omnibus envelope failure. The literal
    ``detail`` string is intentionally NOT pinned: the placeholder
    contract allows non-breaking wording revisions and the
    upstream agent prompt explicitly permits the agent to adjust
    the message. Only structural invariants (non-empty string,
    presence) are asserted so the suite remains portable across
    future wording adjustments (AAP §0.7.2).
    """
    response = client.get("/api/")
    data = response.get_json()

    # ----- Top-level envelope -----
    assert isinstance(data, dict), (
        f"Expected JSON object (dict) at GET /api/, got {type(data).__name__}: {data!r}"
    )
    assert "error" in data, f"Response missing top-level 'error' key: {data!r}"

    # ----- Inner error object -----
    error = data["error"]
    assert isinstance(error, dict), f"'error' must be a dict, got {type(error).__name__}: {error!r}"

    # ----- Required keys per app/errors.py contract + api/routes.py extension -----
    assert error.get("code") == 501, f"Expected error.code == 501, got {error.get('code')!r}"
    assert error.get("message") == "Not Implemented", (
        f"Expected error.message == 'Not Implemented', got {error.get('message')!r}"
    )

    # ----- Placeholder-only 'detail' extension -----
    # The placeholder handler in app/blueprints/api/routes.py adds a
    # ``detail`` field documenting the precondition gap (AAP §0.6.1)
    # and pointing at the open clarification questions (AAP §0.7.4).
    # Structural assertions only — the exact wording is not pinned so
    # the suite remains portable across non-breaking revisions
    # (AAP §0.7.2).
    assert "detail" in error, (
        f"Placeholder must include 'detail' key documenting the precondition gap; "
        f"got error={error!r}"
    )
    assert isinstance(error["detail"], str), (
        f"'detail' must be a string, got {type(error['detail']).__name__}"
    )
    assert len(error["detail"]) > 0, "'detail' must be a non-empty string"


# =============================================================================
# Blueprint-registration smoke test
# =============================================================================
# A direct introspection of the :class:`flask.Flask` instance ensures the
# Blueprint is wired into the application factory the way the design
# intends — name ``"api"``, ``url_prefix="/api"``. This catches a class
# of regressions that the HTTP-layer tests can miss: for example, a
# Blueprint registered WITHOUT the URL prefix would still expose handlers
# (just at the wrong paths), so the HTTP test for ``/api/`` would fail
# with a 404 — but the failure mode would not pinpoint the *cause* (the
# missing prefix). This introspection test pins the contract explicitly.


def test_api_blueprint_is_registered(app: Flask) -> None:
    """Verify the ``api`` Blueprint is registered with ``url_prefix='/api'``.

    Two invariants are checked:

    1. The Blueprint name ``"api"`` appears as a key in
       :attr:`flask.Flask.blueprints` — confirming the application
       factory's ``app.register_blueprint(api_bp)`` call ran
       successfully.
    2. ``api_bp.url_prefix == "/api"`` — confirming the Blueprint
       is mounted at the ``/api`` URL prefix per AAP §0.4.1. The
       ``api`` Blueprint is the ONLY scaffold Blueprint that
       carries a URL prefix; ``health`` and ``main`` mount at the
       application root. The prefix is declared at Blueprint
       construction time
       (``Blueprint("api", __name__, url_prefix="/api")``) rather
       than at registration time, so this assertion catches the
       regression where the prefix is accidentally stripped or
       changed at either site.

    Sister Blueprints' expectations:

    * ``"health"`` — has ``url_prefix is None`` (asserted in
      :mod:`tests.test_health`).
    * ``"main"`` — has ``url_prefix is None`` (asserted in
      :mod:`tests.test_main`).

    Uses the ``app`` fixture from :mod:`tests.conftest` (the
    ``client`` fixture is not needed because the assertion inspects
    the Flask application object directly, not the HTTP surface).
    """
    assert "api" in app.blueprints, (
        f"'api' Blueprint missing from app.blueprints; registered names: "
        f"{sorted(app.blueprints.keys())}"
    )
    api_blueprint = app.blueprints["api"]
    assert api_blueprint.url_prefix == "/api", (
        f"Expected url_prefix='/api' for the 'api' Blueprint, got "
        f"{api_blueprint.url_prefix!r}; the 'api' Blueprint is the ONLY "
        f"scaffold Blueprint that carries a URL prefix — a missing or "
        f"changed prefix relocates every API endpoint and silently breaks "
        f"downstream consumers."
    )


# =============================================================================
# Trailing-slash redirect behaviour
# =============================================================================
# Werkzeug's default ``strict_slashes=True`` setting causes requests to
# ``/api`` (without trailing slash) to receive an HTTP 308 Permanent
# Redirect to the canonical ``/api/`` URL. This is documented Flask
# behaviour and is the *expected* contract for the placeholder. The test
# below locks the behaviour explicitly so a future regression (e.g.,
# someone setting ``strict_slashes=False`` on the Blueprint, or changing
# the Werkzeug default) is detected immediately.


def test_api_root_without_trailing_slash_redirects(client: FlaskClient) -> None:
    """Verify ``GET /api`` (no trailing slash) redirects to ``/api/``.

    Werkzeug's default ``strict_slashes=True`` causes requests to a
    URL that omits the trailing slash on a route that declares one
    to receive an HTTP 308 Permanent Redirect to the canonical URL.
    This is the documented Flask/Werkzeug behaviour and is the
    expected contract for the placeholder; this test documents and
    locks the behaviour so it does not silently change.

    The two-phase assertion:

    1. Request ``/api`` with ``follow_redirects=False`` to capture
       the raw redirect status code. Both ``301 Moved Permanently``
       and ``308 Permanent Redirect`` are accepted: ``308`` is the
       current Werkzeug default (introduced in Werkzeug 1.0+ to
       preserve the HTTP method on redirect, which ``301`` does not
       reliably do across browsers); ``301`` is tolerated so the
       test remains stable if a future Werkzeug release reverts to
       the older default. Other redirect codes (302, 303, 307) are
       explicitly rejected because they would change the semantic
       contract.

    2. Request ``/api`` with ``follow_redirects=True`` to verify
       the redirect chain ultimately lands on the 501 placeholder
       response. This catches the regression where the redirect
       target is wrong (e.g., a typo that redirects to ``/apii/``
       producing a 404) — the raw redirect status assertion alone
       would not catch that.

    Why both phases? Asserting only the follow_redirects=True path
    would not detect a regression where the redirect is implemented
    differently (e.g., via an HTTP 302 server-side handler that
    *also* lands on /api/); asserting only the raw redirect would
    not catch a broken redirect target. Together they pin both the
    redirect type and the redirect destination.
    """
    # Phase 1: raw redirect status.
    response = client.get("/api", follow_redirects=False)
    assert response.status_code in (301, 308), (
        f"Expected redirect (301 or 308) from GET /api (no trailing slash), "
        f"got {response.status_code}; Werkzeug's default strict_slashes=True "
        f"should produce a 308 Permanent Redirect to /api/"
    )

    # Phase 2: follow the redirect and verify the final response.
    response = client.get("/api", follow_redirects=True)
    assert response.status_code == 501, (
        f"Expected 501 after following redirect from GET /api, got "
        f"{response.status_code}; the redirect should land on /api/ which "
        f"returns the 501 placeholder"
    )

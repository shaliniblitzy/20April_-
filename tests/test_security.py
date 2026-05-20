"""Tests for the security-header policy in ``app/security.py``.

Purpose
-------
This module is the pytest test suite for
:func:`app.security.register_security_headers`. It verifies the
defense-in-depth response-header policy applied by the
``@app.after_request`` hook the function registers during application-factory
startup. The hook was added to close the QA Checkpoint 4 MINOR findings:

* **Issue 2** — Enterprise security hardening headers were absent on all
  responses (10 categories missing).
* **Issue 3** — The ``Server`` header disclosed the WSGI server identity.

Both findings are now verified at runtime by the tests below: every
endpoint response from the scaffold carries the documented header set
and the generic ``Server`` token.

Coverage summary
----------------
This module verifies:

1. Every documented security header is set on every endpoint's 200
   response (``GET /``, ``GET /version``, ``GET /healthz``,
   ``GET /readyz``).
2. The 501 placeholder response from ``GET /api/`` also carries every
   security header — the hook fires even on responses produced by view
   functions that return non-200 statuses.
3. Centralized error responses (404 on unknown path, 405 on
   method-not-allowed) ALSO carry every security header — the hook
   fires for responses produced by :mod:`app.errors`.
4. The ``Server`` header is overridden to the generic ``"api"`` value
   on every response (200, 404, 405, 501) — not the default
   ``Werkzeug/<version>`` from the test client (or ``gunicorn`` from
   the production server).
5. Module-level invariants: every header value documented in the QA
   report's Issue 2 finding is present in the
   ``app.security._SECURITY_HEADERS`` tuple, so the source-level
   contract cannot drift from the runtime behavior.

Test isolation
--------------
All tests consume the ``client`` fixture supplied by
:mod:`tests.conftest`, which wraps :meth:`flask.Flask.test_client` and
yields an in-process HTTP transport. Each test function receives its
own fresh Flask instance via the function-scoped fixture chain, so
tests run order-independently and may be parallelised.

References
----------
* QA Checkpoint 4 report — Issue 2 (security hardening headers absent)
  and Issue 3 (Server header discloses server identity).
* :mod:`app.security` — the module under test.
* AAP §0.6.7 — Cross-cutting concerns catalog (uniform response
  policy).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # ``flask.testing.FlaskClient`` is imported under TYPE_CHECKING so
    # type-checkers (mypy) validate the fixture's parameter type
    # annotation without forcing the heavier import at test-collection
    # time. ``from __future__ import annotations`` (above) keeps the
    # annotation as a string at runtime.
    from flask.testing import FlaskClient


# =============================================================================
# Header value contract — single source of truth
# =============================================================================
# The expected header set is duplicated here (rather than imported from
# :mod:`app.security`) so the test enforces the documented contract by
# value, not by reference. A regression that re-binds
# ``_SECURITY_HEADERS`` to a different value or that introduces a typo
# in either source or test would be caught because the two declarations
# must remain byte-identical. The values below mirror exactly the
# values declared in :data:`app.security._SECURITY_HEADERS`.
EXPECTED_SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": (
        "geolocation=(), camera=(), microphone=(), usb=(), payment=(), interest-cohort=()"
    ),
    "Content-Security-Policy": (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    ),
    "X-XSS-Protection": "0",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Embedder-Policy": "require-corp",
    "Cross-Origin-Resource-Policy": "same-origin",
}

# The generic Server token that replaces the WSGI server identity. Mirrors
# :data:`app.security._SERVER_TOKEN`.
EXPECTED_SERVER_TOKEN: str = "api"


# =============================================================================
# Helper: assert security headers on a response
# =============================================================================
def _assert_security_headers(response, context: str) -> None:
    """Assert every documented security header is set with the exact value.

    The helper centralises the assertions so each per-endpoint test
    remains a one-liner that surfaces the failing endpoint in pytest's
    report rather than burying it inside a generic per-header failure.

    Args:
        response: The :class:`flask.Response` whose headers should be
            inspected.
        context: A short description of the request that produced the
            response (e.g., ``"GET /healthz"``). Included in the
            assertion-failure message so the test report names the
            request that failed without requiring stack-trace
            inspection.
    """
    for header_name, expected_value in EXPECTED_SECURITY_HEADERS.items():
        actual_value = response.headers.get(header_name)
        assert actual_value == expected_value, (
            f"[{context}] Expected {header_name}={expected_value!r}, got {actual_value!r}"
        )


def _assert_server_header_overridden(response, context: str) -> None:
    """Assert the ``Server`` header was overridden to the generic token.

    Args:
        response: The :class:`flask.Response` whose ``Server`` header
            should be inspected.
        context: A short description of the request that produced the
            response, included in the assertion-failure message.
    """
    server_header = response.headers.get("Server")
    assert server_header == EXPECTED_SERVER_TOKEN, (
        f"[{context}] Expected Server={EXPECTED_SERVER_TOKEN!r}, got {server_header!r}"
    )


# =============================================================================
# Tests for 200 OK responses
# =============================================================================
# Every successful endpoint must carry every security header AND the
# generic Server token. The five scaffold endpoints below produce 200/501
# responses; tests cover all five so a regression that drops the hook
# for any one endpoint surfaces as a single named test failure.


def test_index_response_has_security_headers(client: FlaskClient) -> None:
    """Verify ``GET /`` response carries every security header.

    The ``main`` Blueprint's index endpoint returns 200 with the service
    banner JSON. Every security header documented in
    :data:`EXPECTED_SECURITY_HEADERS` must be present on the response;
    this test fails if the ``@app.after_request`` hook in
    :mod:`app.security` was removed, replaced, or fails to add a
    header.
    """
    response = client.get("/")
    assert response.status_code == 200, (
        f"Expected 200 from GET /, got {response.status_code}; "
        f"body={response.get_data(as_text=True)!r}"
    )
    _assert_security_headers(response, "GET /")


def test_version_response_has_security_headers(client: FlaskClient) -> None:
    """Verify ``GET /version`` response carries every security header.

    Same coverage rationale as :func:`test_index_response_has_security_headers`
    but exercises the ``/version`` route under the same Blueprint.
    """
    response = client.get("/version")
    assert response.status_code == 200, (
        f"Expected 200 from GET /version, got {response.status_code}; "
        f"body={response.get_data(as_text=True)!r}"
    )
    _assert_security_headers(response, "GET /version")


def test_healthz_response_has_security_headers(client: FlaskClient) -> None:
    """Verify ``GET /healthz`` response carries every security header.

    Probe endpoints are the most heavily-trafficked routes in a
    containerised deployment, so a missing security header here would
    be ten times more visible than a missing header on a regular
    endpoint. The probe responses are tiny but the headers must be
    present on every response — orchestrator probe responses are still
    real HTTP responses that hit the user agent.
    """
    response = client.get("/healthz")
    assert response.status_code == 200, (
        f"Expected 200 from GET /healthz, got {response.status_code}; "
        f"body={response.get_data(as_text=True)!r}"
    )
    _assert_security_headers(response, "GET /healthz")


def test_readyz_response_has_security_headers(client: FlaskClient) -> None:
    """Verify ``GET /readyz`` response carries every security header.

    Same coverage rationale as :func:`test_healthz_response_has_security_headers`
    but exercises the readiness probe.
    """
    response = client.get("/readyz")
    assert response.status_code == 200, (
        f"Expected 200 from GET /readyz, got {response.status_code}; "
        f"body={response.get_data(as_text=True)!r}"
    )
    _assert_security_headers(response, "GET /readyz")


def test_api_placeholder_response_has_security_headers(client: FlaskClient) -> None:
    """Verify ``GET /api/`` (501) carries every security header.

    The ``api`` Blueprint placeholder returns 501 Not Implemented. The
    ``after_request`` hook in :mod:`app.security` fires for ALL
    responses Flask returns, regardless of status code — this test
    catches the regression where the hook is mistakenly guarded by a
    status-code check (a common mistake).
    """
    response = client.get("/api/")
    assert response.status_code == 501, (
        f"Expected 501 from GET /api/, got {response.status_code}; "
        f"body={response.get_data(as_text=True)!r}"
    )
    _assert_security_headers(response, "GET /api/")


# =============================================================================
# Tests for error responses
# =============================================================================
# The centralized error handlers in :mod:`app.errors` produce 404, 405,
# and 500 responses. Flask's ``after_request`` hooks fire for these
# responses too — the security-header policy MUST apply uniformly to
# error responses or attackers could fingerprint the deployment by
# comparing header sets across status codes.


def test_404_response_has_security_headers(client: FlaskClient) -> None:
    """Verify 404 (not found) error response carries every security header.

    Issues a request to an unknown path so Flask invokes the
    centralized 404 handler in :mod:`app.errors`. The
    ``after_request`` hook from :mod:`app.security` MUST fire on this
    response too; the hook is registered on the Flask application, not
    on individual routes, so error responses are covered.

    The test path includes characters that are valid in URLs but
    obviously not a real endpoint (``/this-path-does-not-exist-XYZ``);
    a path collision with a future ported endpoint is therefore
    vanishingly unlikely.
    """
    response = client.get("/this-path-does-not-exist-XYZ")
    assert response.status_code == 404, (
        f"Expected 404 for unknown path, got {response.status_code}; "
        f"body={response.get_data(as_text=True)!r}"
    )
    _assert_security_headers(response, "GET /this-path-does-not-exist-XYZ (404)")


def test_405_response_has_security_headers(client: FlaskClient) -> None:
    """Verify 405 (method not allowed) response carries every security header.

    Issues a POST to a GET-only endpoint so Flask invokes the
    centralized 405 handler in :mod:`app.errors`. The
    ``after_request`` hook in :mod:`app.security` MUST coexist with
    the 405 handler's header-preservation logic (``Allow`` header
    forwarded from Werkzeug) — neither hook should clobber the
    other's headers.

    This test therefore double-asserts:

    * Every security header is present (this module's primary concern).
    * The ``Allow`` header is also present (the centralized 405
      handler's contract from :mod:`app.errors` — duplicated here as a
      regression guard against the security-header hook accidentally
      dropping it).
    """
    response = client.post("/healthz")
    assert response.status_code == 405, (
        f"Expected 405 from POST /healthz, got {response.status_code}; "
        f"body={response.get_data(as_text=True)!r}"
    )
    _assert_security_headers(response, "POST /healthz (405)")
    # Regression guard: the 405 handler's ``Allow`` header preservation
    # contract from :mod:`app.errors` must remain intact even with the
    # security-header hook registered.
    assert "Allow" in response.headers, (
        "The 405 response lost the 'Allow' header; the security-header "
        "hook in app/security.py may have dropped it. Inspect the "
        "after_request implementation."
    )
    assert "GET" in response.headers["Allow"], (
        f"Expected the Allow header to contain 'GET', got {response.headers['Allow']!r}"
    )


# =============================================================================
# Tests for the Server header override
# =============================================================================
# Issue 3 of the QA report: the response carried ``Server: gunicorn``
# (or ``Server: Werkzeug/<version>`` from the test client) disclosing
# the WSGI server identity. The after_request hook in app/security.py
# unconditionally replaces this with the generic ``api`` token; the
# tests below verify the replacement happens on a representative sample
# of response paths (200, 404, 405, 501).


def test_server_header_overridden_on_index(client: FlaskClient) -> None:
    """Verify ``GET /`` Server header is the generic ``api`` token.

    Without the override, Flask's test client carries
    ``Server: Werkzeug/<version> Python/<version>``; gunicorn would
    carry ``Server: gunicorn``. The override replaces either default
    with ``api``.
    """
    response = client.get("/")
    _assert_server_header_overridden(response, "GET /")


def test_server_header_overridden_on_healthz(client: FlaskClient) -> None:
    """Verify ``GET /healthz`` Server header is the generic ``api`` token.

    Probe endpoints are typically called from monitoring infrastructure
    that may log response headers; the Server token should not
    fingerprint the deployment.
    """
    response = client.get("/healthz")
    _assert_server_header_overridden(response, "GET /healthz")


def test_server_header_overridden_on_404(client: FlaskClient) -> None:
    """Verify 404 response Server header is the generic ``api`` token.

    Error responses are a common reconnaissance vector — an attacker
    may probe for known paths and inspect the response headers. The
    Server token must be identical across success and error responses
    so the deployment cannot be fingerprinted by status code.
    """
    response = client.get("/this-path-does-not-exist-ABC")
    _assert_server_header_overridden(response, "GET /this-path-does-not-exist-ABC (404)")


def test_server_header_overridden_on_405(client: FlaskClient) -> None:
    """Verify 405 response Server header is the generic ``api`` token.

    Same rationale as :func:`test_server_header_overridden_on_404` —
    error responses must not leak the WSGI server identity.
    """
    response = client.post("/healthz")
    _assert_server_header_overridden(response, "POST /healthz (405)")


def test_server_header_overridden_on_api_placeholder(client: FlaskClient) -> None:
    """Verify ``GET /api/`` (501) Server header is the generic ``api`` token.

    The 501 placeholder response from the API blueprint should also
    carry the generic Server token — the override is in
    ``after_request``, which fires for every response status.
    """
    response = client.get("/api/")
    _assert_server_header_overridden(response, "GET /api/ (501)")


# =============================================================================
# Module-level contract tests
# =============================================================================
# These tests import the constants from app.security directly and assert
# the module-level contract matches the documented behavior. They catch
# regressions at the source level (e.g., someone editing
# _SECURITY_HEADERS without updating the test contract), independent of
# the runtime tests above.


def test_security_headers_constant_matches_expected_set() -> None:
    """Verify ``app.security._SECURITY_HEADERS`` matches expected contract.

    The module-level constant is the single source of truth for which
    headers the hook applies. This test imports it directly and asserts:

    * Every header in :data:`EXPECTED_SECURITY_HEADERS` is present in
      the constant (with matching value).
    * The constant does not contain unexpected headers — additions
      require an explicit test update.

    Importing private module symbols (``_SECURITY_HEADERS`` prefixed
    with underscore) from a test is a deliberate convention here: the
    test is intentionally tightly coupled to the implementation so
    drift between the documented contract and the source is caught
    early.
    """
    from app.security import _SECURITY_HEADERS

    actual_headers = dict(_SECURITY_HEADERS)

    # ----- Every expected header is present with the expected value -----
    for header_name, expected_value in EXPECTED_SECURITY_HEADERS.items():
        assert header_name in actual_headers, (
            f"Expected header {header_name!r} missing from "
            f"app.security._SECURITY_HEADERS; got {sorted(actual_headers.keys())!r}"
        )
        assert actual_headers[header_name] == expected_value, (
            f"Header {header_name} value mismatch: expected "
            f"{expected_value!r}, got {actual_headers[header_name]!r}"
        )

    # ----- No unexpected headers are declared -----
    # If new headers are added to ``_SECURITY_HEADERS``, this test must
    # be updated explicitly. The set-difference assertion makes the
    # change auditable: anyone adding a new header must justify it in
    # the same PR that updates this expected set.
    unexpected = set(actual_headers.keys()) - set(EXPECTED_SECURITY_HEADERS.keys())
    assert not unexpected, (
        f"Unexpected headers in app.security._SECURITY_HEADERS: "
        f"{sorted(unexpected)!r}. If these are intentional, add them to "
        f"EXPECTED_SECURITY_HEADERS in tests/test_security.py."
    )


def test_server_token_constant_matches_expected_value() -> None:
    """Verify ``app.security._SERVER_TOKEN`` matches expected contract.

    The generic Server identifier is declared as a module-level
    constant for the same single-source-of-truth reason as
    :data:`app.security._SECURITY_HEADERS`. This test pins the value
    so a regression that changes the token (e.g., back to a more
    descriptive identifier) is caught at the source level.
    """
    from app.security import _SERVER_TOKEN

    assert _SERVER_TOKEN == EXPECTED_SERVER_TOKEN, (
        f"Expected _SERVER_TOKEN={EXPECTED_SERVER_TOKEN!r}, got {_SERVER_TOKEN!r}"
    )


def test_register_security_headers_is_callable() -> None:
    """Verify ``app.security.register_security_headers`` is callable.

    Smoke test that the public API surface exists and is the documented
    type (callable). Catches regressions where the function is
    accidentally renamed, removed, or replaced with a non-callable
    object.
    """
    from app.security import register_security_headers

    assert callable(register_security_headers), (
        f"register_security_headers must be callable; got {type(register_security_headers)}"
    )


def test_register_security_headers_is_in_public_api() -> None:
    """Verify ``register_security_headers`` is exported via ``__all__``.

    The module's ``__all__`` declaration controls what
    ``from app.security import *`` exposes. The public function MUST
    be in that list — otherwise downstream consumers using star-imports
    would silently fail to find it.
    """
    import app.security as security_module

    assert hasattr(security_module, "__all__"), (
        "app.security module must declare __all__ for explicit public API"
    )
    assert "register_security_headers" in security_module.__all__, (
        f"register_security_headers must be in __all__; got {security_module.__all__!r}"
    )

"""Centralized HTTP error handler registration for the Flask application.

Purpose
-------
This module is the single, authoritative location where HTTP error semantics
are defined for the Python/Flask runtime. It exposes one public function,
:func:`register_error_handlers`, which the application factory in
:mod:`app` calls during startup to wire every HTTP error response through a
common JSON envelope.

Pattern
-------
:func:`register_error_handlers` registers per-status handlers via Flask's
``@app.errorhandler`` decorator for the most common client-input and server
failure modes — ``400 Bad Request``, ``404 Not Found``, ``405 Method Not
Allowed``, and ``500 Internal Server Error`` — plus a catch-all handler
keyed on :class:`werkzeug.exceptions.HTTPException`. The catch-all ensures
that *any* HTTP error subclass without an explicit per-code registration
(e.g. ``403 Forbidden``, ``410 Gone``, ``503 Service Unavailable``) still
receives the standardized JSON envelope instead of falling back to Flask's
default HTML error page.

Response contract
-----------------
Every error response produced by the handlers below uses the same shape::

    {"error": {"code": <status>, "message": <reason>}}

Where:

* ``code`` is the integer HTTP status code (e.g. ``404``), guaranteed to
  match the HTTP status header.
* ``message`` is a short, human-readable description of the error (e.g.
  ``"Not Found"``) sourced from the canonical HTTP status name. The message
  intentionally does NOT include implementation details such as stack
  traces or file paths — those are emitted to the application log via
  :func:`logger.exception`, never to the HTTP response.

Protocol-header preservation
----------------------------
HTTP error responses sometimes carry status-specific headers whose
semantics are part of the HTTP standard (RFC 9110) — the response body
is not the only thing that matters. Examples include:

* ``Allow`` on ``405 Method Not Allowed`` — RFC 9110 §15.5.6 REQUIRES the
  ``Allow`` header on every 405 response, listing the methods that are
  supported by the target resource. Clients (notably API gateways and
  browsers' CORS preflight machinery) rely on this header to discover the
  supported method set.
* ``WWW-Authenticate`` on ``401 Unauthorized`` — RFC 9110 §15.5.2
  REQUIRES the ``WWW-Authenticate`` header on every 401 response,
  identifying the authentication scheme(s) the client may use. Without
  it, clients cannot satisfy the challenge.
* ``Retry-After`` on ``503 Service Unavailable`` and ``429 Too Many
  Requests`` — RFC 9110 §10.2.3 / §15.5.20 specify this hint to clients
  for when to retry.

Werkzeug's :class:`~werkzeug.exceptions.HTTPException` subclasses already
attach these headers to the response they generate (e.g.
:class:`werkzeug.exceptions.MethodNotAllowed` accepts ``valid_methods``
and emits ``Allow`` automatically). Naively replacing that response with a
fresh :func:`jsonify` body discards those headers — the prior version of
this module had exactly that bug and was flagged by Checkpoint 3 review.

The handlers below now read the headers Werkzeug already attached to the
canonical response via :meth:`werkzeug.exceptions.HTTPException.get_response`
and merge them onto the JSON response BEFORE returning it. ``Content-Type``
and ``Content-Length`` are intentionally excluded from the merge because
they describe Werkzeug's HTML body, not our JSON body. Every other header
is preserved verbatim.

Centralizing this contract here (rather than scattering ``jsonify(...)``
calls across every blueprint) is the explicit design decision recorded in
Agent Action Plan (AAP) §0.3.3 *Centralized Error Handlers* and §0.6.7
*Cross-cutting concerns catalog*. Routes that need to emit an HTTP error
should simply call :func:`flask.abort` or raise a
:class:`werkzeug.exceptions.HTTPException` subclass and let the handlers
below produce the response.

Future Node.js port contract
----------------------------
Per AAP §0.6.2 the Node.js idiom of ``res.status(404).json({error: "Not
Found"})`` inside route handlers should NOT be re-implemented per-route in
the Python port. Instead, the equivalent Python idiom is
``abort(404)`` (or ``raise werkzeug.exceptions.NotFound()``) at the call
site, and *this* module is responsible for shaping the JSON envelope. This
keeps every route's response contract identical regardless of where the
error was raised.

Behavioural notes
-----------------
* Handlers must NEVER raise an exception themselves — if they did, Flask
  would fall back to its default HTML error page and break the JSON
  contract. Each handler below is deliberately a one-liner that delegates
  to the local :func:`_make_error_response` helper.
* Handlers always return the explicit ``(response, status)`` tuple form so
  the HTTP status header matches the JSON ``code`` field byte-for-byte.
* The ``500`` handler is the only one that calls :func:`logger.exception`
  — the others handle expected client-input errors that are not server
  faults and would only generate log noise.
* When Flask runs with ``DEBUG=True`` the Werkzeug interactive debugger
  may intercept unhandled exceptions BEFORE the 500 handler runs. This is
  documented Flask behaviour and is intentional — the production handlers
  still apply when ``DEBUG=False`` (i.e. under :class:`ProductionConfig`).

References
----------
* AAP §0.3.3 — Centralized Error Handlers (design pattern)
* AAP §0.4.1 — Transformation table row for ``app/errors.py``
* AAP §0.4.2 — Import graph (``app/__init__.py`` imports
  :func:`register_error_handlers` from this module)
* AAP §0.6.2 — Node→Python idiom translation (error-handling row)
* AAP §0.6.7 — Cross-cutting concerns catalog (error semantics
  centralized)
* Flask docs — ``@app.errorhandler`` decorator semantics
* Werkzeug docs — ``werkzeug.exceptions.HTTPException`` hierarchy
* RFC 9110 §15.5.2 — ``WWW-Authenticate`` on 401 responses (REQUIRED)
* RFC 9110 §15.5.6 — ``Allow`` on 405 responses (REQUIRED)
* RFC 9110 §10.2.3, §15.5.20 — ``Retry-After`` on 503/429 responses
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from flask import jsonify
from werkzeug.exceptions import HTTPException

# ---------------------------------------------------------------------------
# Type-only imports.
# ---------------------------------------------------------------------------
# The Flask class is needed exclusively as the type annotation for the
# `app` parameter of `register_error_handlers`. Guarding the import behind
# `TYPE_CHECKING` keeps it out of the runtime import graph entirely — the
# annotation is evaluated as a string by `from __future__ import
# annotations` above. This pattern avoids paying the cost of resolving the
# Flask class at module-import time (a measurable optimization for cold
# starts in serverless contexts) while still giving static type checkers
# (mypy, pyright) the symbol they need to validate call sites.
if TYPE_CHECKING:
    from flask import Flask


# ---------------------------------------------------------------------------
# Module-level logger.
# ---------------------------------------------------------------------------
# Per the AAP `app/` package convention, every module obtains its logger
# via `logging.getLogger(__name__)` so that hierarchical filtering rules
# configured in `app.logging_config.configure_logging` apply uniformly.
# This logger is used inside the 500-handler below to record the
# underlying exception's traceback via `logger.exception(...)`.
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers.
# ---------------------------------------------------------------------------

# Headers that describe Werkzeug's HTML error body rather than the JSON
# body we substitute. They MUST NOT be carried over from the Werkzeug
# response, because copying them would either misdescribe the JSON body
# (``Content-Type: text/html``) or cause downstream caches/clients to
# truncate or refuse the body (``Content-Length`` mismatch).
#
# A ``frozenset`` is used so the membership test in
# :func:`_extract_preserved_headers` is O(1) and the constant is immutable.
# Comparison is case-insensitive because HTTP header names are
# case-insensitive (RFC 9110 §5.1); the entries are stored upper-cased and
# every input is upper-cased before comparison.
_HEADERS_NOT_PRESERVED: frozenset[str] = frozenset({"CONTENT-TYPE", "CONTENT-LENGTH"})


def _extract_preserved_headers(error: HTTPException) -> list[tuple[str, str]]:
    """Extract protocol/security headers from a Werkzeug HTTPException response.

    Werkzeug's HTTPException subclasses encode status-specific headers on
    the canonical response they generate. The most important examples
    relevant to this scaffold:

    * :class:`werkzeug.exceptions.MethodNotAllowed` attaches an ``Allow``
      header populated from the route's registered methods.
    * :class:`werkzeug.exceptions.Unauthorized` attaches a
      ``WWW-Authenticate`` header derived from its ``www_authenticate``
      keyword argument (or its :attr:`Unauthorized.www_authenticate`
      attribute), unless an explicit "no challenge" sentinel is supplied.
    * :class:`werkzeug.exceptions.TooManyRequests` and
      :class:`werkzeug.exceptions.ServiceUnavailable` may attach a
      ``Retry-After`` header.

    Naively building a new :func:`jsonify` response and returning it
    discards all of the above. This helper reads the headers that
    Werkzeug already attached to the response it would have rendered
    and returns the protocol-significant ones so the caller can merge
    them onto the JSON response.

    Filtering rules:

    * Header names compared case-insensitively (RFC 9110 §5.1).
    * ``Content-Type`` is dropped — our response carries
      ``application/json``, not Werkzeug's ``text/html; charset=utf-8``.
    * ``Content-Length`` is dropped — our JSON body has a different byte
      length than Werkzeug's HTML body, and an incorrect length is
      treated as a hard error by HTTP/1.1 clients.
    * Every other header (``Allow``, ``WWW-Authenticate``, ``Retry-After``,
      vendor extensions, etc.) is preserved verbatim.

    Defensive handling:

    * If :meth:`error.get_response` raises (e.g. because a custom
      :class:`HTTPException` subclass overrides it with a broken
      implementation), the function returns an empty list rather than
      letting the exception propagate. Error handlers must NEVER raise
      themselves — see the module docstring.

    Args:
        error: The :class:`werkzeug.exceptions.HTTPException` whose
            response headers should be inspected. Typically the same
            ``error`` object Flask passes positionally to the
            ``@app.errorhandler``-registered function.

    Returns:
        A list of ``(name, value)`` tuples containing the headers worth
        preserving on the JSON response, in the order Werkzeug supplied
        them. Empty list if no preserved headers are present or if
        accessing ``error.get_response()`` failed.
    """
    try:
        werkzeug_response = error.get_response()
    except Exception:  # pragma: no cover - defensive: handlers must not raise
        return []

    preserved: list[tuple[str, str]] = []
    # ``werkzeug.datastructures.Headers`` supports iteration as
    # ``(name, value)`` tuples — the canonical way to enumerate headers
    # without lifting them into a dict (a dict would lose duplicate
    # entries, which the HTTP spec permits for some headers).
    for name, value in werkzeug_response.headers.items():
        if name.upper() in _HEADERS_NOT_PRESERVED:
            continue
        preserved.append((name, value))
    return preserved


def _make_error_response(
    status: int,
    message: str,
    extra_headers: list[tuple[str, str]] | None = None,
) -> tuple:
    """Build the standard JSON error response envelope.

    This is the SINGLE source of truth for the error response shape used
    across every handler in :func:`register_error_handlers`. Centralising
    construction here guarantees that the envelope is identical regardless
    of which handler produced it, which in turn lets clients rely on a
    stable shape contract across all HTTP error statuses.

    The function returns a 2-tuple of ``(Response, status)`` rather than a
    bare :class:`flask.Response`. Flask interprets the second element of
    such tuples as the HTTP status code and applies it to the underlying
    response, guaranteeing that the JSON body's ``code`` field and the
    HTTP status header always match byte-for-byte. Returning the tuple
    form (rather than mutating ``response.status_code`` after construction)
    keeps the function pure and trivially unit-testable.

    Header preservation:

    When ``extra_headers`` is supplied, each ``(name, value)`` pair is
    added to the response BEFORE returning. This is used by the 405
    handler and the ``HTTPException`` catch-all to carry protocol-required
    headers (``Allow``, ``WWW-Authenticate``, ``Retry-After``) from
    Werkzeug's canonical response onto our JSON response — see the
    module docstring's "Protocol-header preservation" section for the
    standards-compliance rationale. The caller is responsible for
    filtering out ``Content-Type`` / ``Content-Length`` before passing
    headers in; :func:`_extract_preserved_headers` is the canonical
    source of correctly-filtered header lists.

    Args:
        status: HTTP status code to apply to the response and embed in the
            envelope's ``code`` field (e.g. ``404``).
        message: Short, human-readable error description embedded in the
            envelope's ``message`` field (e.g. ``"Not Found"``). Should NOT
            contain implementation details (stack traces, internal paths,
            secrets) — those belong in the log, not the HTTP body.
        extra_headers: Optional list of ``(name, value)`` tuples to attach
            to the response. Used to preserve protocol-required headers
            (``Allow``, ``WWW-Authenticate``, ``Retry-After``) from
            Werkzeug responses. ``None`` (the default) leaves the
            response headers untouched apart from ``Content-Type``
            (which :func:`flask.jsonify` sets to ``application/json``).

    Returns:
        A ``(response, status)`` tuple where ``response`` is a
        :class:`flask.Response` carrying the JSON body
        ``{"error": {"code": status, "message": message}}`` with
        ``Content-Type: application/json`` plus every header from
        ``extra_headers`` (if supplied), and ``status`` is the integer
        code passed in.
    """
    response = jsonify({"error": {"code": status, "message": message}})
    if extra_headers:
        # Use ``Headers.add`` rather than dict-style assignment so headers
        # that legitimately appear multiple times (e.g. ``Set-Cookie``)
        # are preserved. ``jsonify`` does not emit duplicate headers,
        # so this iteration is purely additive.
        for name, value in extra_headers:
            response.headers.add(name, value)
    return response, status


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------
def register_error_handlers(app: Flask) -> None:
    """Register HTTP error handlers on the given Flask application.

    Handlers registered (in order of declaration):

    * **400 Bad Request** — generic client-input validation failure.
    * **404 Not Found** — requested resource does not exist.
    * **405 Method Not Allowed** — HTTP method not supported by the
      matched route.
    * **500 Internal Server Error** — uncaught exception bubbled out of a
      view function or middleware. This handler additionally logs the
      underlying exception via :func:`logger.exception` so the stack
      trace is preserved in the application log without leaking
      implementation details to the HTTP response body.
    * **HTTPException catch-all** — any other HTTP error subclass raised
      explicitly via :func:`flask.abort` or by user code (e.g.
      :class:`werkzeug.exceptions.Forbidden`,
      :class:`werkzeug.exceptions.Gone`,
      :class:`werkzeug.exceptions.ServiceUnavailable`). Flask's handler
      resolution prefers the most specific match, so the per-status
      handlers above always take precedence when their code applies; this
      catch-all only fires for HTTP error subclasses without an explicit
      registration.

    The function returns ``None`` because its side effect — registering
    handlers on ``app`` — is the entire point. The application factory in
    :mod:`app` discards the return value.

    Args:
        app: The :class:`flask.Flask` application instance constructed by
            the application factory. Handlers are attached to this
            instance only; calling :func:`register_error_handlers`
            multiple times with the same ``app`` will overwrite the
            previously registered handlers (Flask's documented
            behaviour) but is otherwise safe.
    """

    # ------------------------------------------------------------------ 400
    @app.errorhandler(400)
    def bad_request(error):  # noqa: ARG001
        """Return the standard JSON envelope for HTTP 400 Bad Request.

        ``error`` is the :class:`werkzeug.exceptions.BadRequest` instance
        Flask passes positionally to the handler; we discard it because
        the envelope's message is sourced from the canonical HTTP status
        name (``"Bad Request"``), not from the exception's free-form
        description. This avoids leaking framework-internal details into
        the wire response.
        """
        return _make_error_response(400, "Bad Request")

    # ------------------------------------------------------------------ 404
    @app.errorhandler(404)
    def not_found(error):  # noqa: ARG001
        """Return the standard JSON envelope for HTTP 404 Not Found.

        Triggered for any request whose URL did not match a registered
        route as well as for explicit ``abort(404)`` calls within view
        functions. The ``error`` argument is unused for the same reason
        as documented on :func:`bad_request`.
        """
        return _make_error_response(404, "Not Found")

    # ------------------------------------------------------------------ 405
    @app.errorhandler(405)
    def method_not_allowed(error: HTTPException):
        """Return the standard JSON envelope for HTTP 405 Method Not Allowed.

        Triggered when a request's HTTP method does not match any
        registered method for the matched route — for example, a ``POST``
        request to a route declared as ``@bp.get(...)``.

        Header preservation
        -------------------
        RFC 9110 §15.5.6 REQUIRES every 405 response to carry an
        ``Allow`` header listing the methods supported by the target
        resource. Werkzeug's
        :class:`~werkzeug.exceptions.MethodNotAllowed` populates that
        header automatically from Flask's URL map; this handler extracts
        it (and any other non-body headers Werkzeug attached) via
        :func:`_extract_preserved_headers` and merges them onto our JSON
        response so the wire response remains standards-compliant.

        Without this preservation step (the bug fixed in Checkpoint 3),
        clients calling ``OPTIONS`` to discover allowed methods, API
        gateways performing CORS preflight, and any RFC-conformant HTTP
        client would receive a 405 with no ``Allow`` header — a hard
        violation of the HTTP specification.

        Args:
            error: The :class:`werkzeug.exceptions.MethodNotAllowed`
                instance Flask passes positionally. Its
                :meth:`get_response` method yields the canonical
                Werkzeug response from which protocol headers are
                copied.
        """
        headers = _extract_preserved_headers(error)
        return _make_error_response(405, "Method Not Allowed", extra_headers=headers)

    # ------------------------------------------------------------------ 500
    @app.errorhandler(500)
    def internal_server_error(error):
        """Return the standard JSON envelope for HTTP 500 Internal Server Error.

        Triggered when an uncaught exception bubbles out of a view
        function or middleware. Unlike the client-input handlers above,
        this handler ALSO logs the underlying exception via
        :func:`logger.exception`, which records the current traceback at
        ``ERROR`` level. The traceback stays in the log; only the
        canonical ``"Internal Server Error"`` string reaches the HTTP
        body, ensuring no implementation details (file paths, library
        versions, secrets embedded in object reprs) leak out over the
        wire.

        Args:
            error: The exception that triggered the 500. We pass it to
                :func:`logger.exception` as the formatted message
                argument to give operators a one-line summary above the
                rendered traceback in log output.
        """
        logger.exception("Internal server error: %s", error)
        return _make_error_response(500, "Internal Server Error")

    # --------------------------------------------------- HTTPException (catch-all)
    @app.errorhandler(HTTPException)
    def http_exception(error: HTTPException):
        """Return the standard JSON envelope for any other HTTP error.

        This handler is the universal fallback for HTTP error subclasses
        without an explicit per-code registration above — typical
        examples include ``401 Unauthorized``, ``403 Forbidden``,
        ``410 Gone``, ``413 Request Entity Too Large``,
        ``415 Unsupported Media Type``, and ``503 Service Unavailable``.

        Flask's handler resolution algorithm matches by exception class
        in the most-specific-first order, so the per-status handlers
        registered above always run in preference to this one for the
        codes they cover. This catch-all only fires for HTTP errors
        that do NOT match one of those specific codes.

        Header preservation
        -------------------
        Several HTTP error statuses REQUIRE response headers whose
        semantics are part of the HTTP standard:

        * ``401 Unauthorized`` MUST carry ``WWW-Authenticate``
          (RFC 9110 §15.5.2).
        * ``503 Service Unavailable`` SHOULD carry ``Retry-After``
          (RFC 9110 §15.5.20).
        * ``429 Too Many Requests`` SHOULD carry ``Retry-After``
          (RFC 6585 §4).

        Werkzeug's :class:`~werkzeug.exceptions.HTTPException` subclasses
        already attach these headers to the canonical response they
        produce; this handler extracts them via
        :func:`_extract_preserved_headers` and merges them onto our JSON
        response so the catch-all path remains standards-compliant
        regardless of which HTTP error subclass was raised.

        Defensive handling:

        * ``error.code`` is defined by every standard
          :class:`werkzeug.exceptions.HTTPException` subclass, but
          custom subclasses are permitted to set it to ``None``. We
          fall back to ``500`` in that case so the response always
          carries a valid HTTP status code.
        * ``error.name`` is similarly populated by every standard
          subclass with the canonical status name; we fall back to a
          generic ``"HTTP Error"`` string if it is missing or empty.

        Args:
            error: The :class:`werkzeug.exceptions.HTTPException`
                instance Flask passes positionally. Its ``code`` and
                ``name`` attributes determine the response body; its
                attached response headers determine the preserved
                header set.
        """
        status = error.code if error.code is not None else 500
        message = error.name if error.name else "HTTP Error"
        headers = _extract_preserved_headers(error)
        return _make_error_response(status, message, extra_headers=headers)


# ---------------------------------------------------------------------------
# Public API export.
# ---------------------------------------------------------------------------
# Explicitly enumerate the public surface of this module so that:
#   * `from app.errors import *` exposes only the documented function;
#   * static analysers and IDEs treat the private helper
#     `_make_error_response` as internal-only;
#   * future additions to this module are forced through a deliberate
#     update of `__all__` rather than slipping in as accidental public
#     API.
__all__ = ["register_error_handlers"]

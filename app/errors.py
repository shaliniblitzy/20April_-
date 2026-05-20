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
def _make_error_response(status: int, message: str) -> tuple:
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

    Args:
        status: HTTP status code to apply to the response and embed in the
            envelope's ``code`` field (e.g. ``404``).
        message: Short, human-readable error description embedded in the
            envelope's ``message`` field (e.g. ``"Not Found"``). Should NOT
            contain implementation details (stack traces, internal paths,
            secrets) — those belong in the log, not the HTTP body.

    Returns:
        A ``(response, status)`` tuple where ``response`` is a
        :class:`flask.Response` carrying the JSON body
        ``{"error": {"code": status, "message": message}}`` with
        ``Content-Type: application/json``, and ``status`` is the
        integer code passed in.
    """
    response = jsonify({"error": {"code": status, "message": message}})
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
    def method_not_allowed(error):  # noqa: ARG001
        """Return the standard JSON envelope for HTTP 405 Method Not Allowed.

        Triggered when a request's HTTP method does not match any
        registered method for the matched route — for example, a ``POST``
        request to a route declared as ``@bp.get(...)``. Flask
        automatically generates an ``Allow`` header listing the
        supported methods; this handler returns a JSON body in addition
        to (not in place of) Flask's default header behaviour.
        """
        return _make_error_response(405, "Method Not Allowed")

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
                ``name`` attributes determine the response body.
        """
        status = error.code if error.code is not None else 500
        message = error.name if error.name else "HTTP Error"
        return _make_error_response(status, message)


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

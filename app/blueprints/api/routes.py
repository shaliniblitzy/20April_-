"""Route handlers for the ``api`` Blueprint (placeholder until Node.js port).

Purpose
-------
This module is the canonical location for HTTP view functions attached to
the :data:`app.blueprints.api.api_bp` Flask :class:`flask.Blueprint`. The
Blueprint is instantiated in the sibling package initializer
(:mod:`app.blueprints.api`) with ``url_prefix="/api"``, so every route
declared here is mounted under ``/api/*`` once
:meth:`flask.Flask.register_blueprint` has wired the Blueprint into the
WSGI application produced by the :func:`app.create_app` factory.

Current status — placeholder
----------------------------
Because no Node.js source code exists in the repository today (see Agent
Action Plan (AAP) §0.6.1 and §0.7.4 for the precondition gap and the
open clarification questions, respectively), this module ships exactly
ONE handler: a placeholder bound to ``GET /api/`` that returns HTTP 501
Not Implemented. The placeholder response body intentionally re-uses the
centralized error envelope shape defined in :mod:`app.errors`
(``{"error": {"code": <int>, "message": <str>}}``) and adds a
placeholder-specific ``detail`` key carrying a human-readable porting
note that points back to AAP §0.7.4.

When the original Node.js source becomes available, the placeholder is
removed and the ported endpoints are added below it. The marker comment
block at the end of this file documents the canonical idiom translation
table and serves as a recipe for the next agent (or human reviewer).

Node.js → Python/Flask idiom translation (AAP §0.6.2)
-----------------------------------------------------
Ported endpoints should follow these mechanical conversions:

* ``app.METHOD(path, handler)``      → ``@api_bp.METHOD(path) def handler(): ...``
* ``req.body``                       → ``request.get_json(silent=True)``
* ``req.query.x``                    → ``request.args.get("x")``
* ``req.params.id`` (Express)        → ``<int:id>`` converter + function arg
* ``res.status(N).json(obj)``        → ``return jsonify(obj), N``
* ``next(err)`` / error-middleware   → ``abort(N)`` or raise
                                         :class:`werkzeug.exceptions.HTTPException`
                                         and let :mod:`app.errors` handle it

Layered architecture seed (AAP §0.3.3)
--------------------------------------
This file is the *HTTP boundary*. Once endpoints are ported, business
logic MUST NOT live here. The canonical handler shape is:

    1. Parse the request (``request.args``, ``request.get_json()``,
       ``request.headers``).
    2. Validate inputs (raising :class:`werkzeug.exceptions.BadRequest`
       or :func:`flask.abort` on failure so :mod:`app.errors` produces
       the standard JSON envelope).
    3. Delegate to a service function under ``app/services/`` (not yet
       created — these modules will be introduced during the port).
    4. Serialize the service's return value with :func:`flask.jsonify`
       and return an explicit ``(response, status)`` tuple.

References
----------
* AAP §0.3.1 — Refactored Structure (``app/blueprints/api/`` subtree)
* AAP §0.3.3 — Blueprint modularization; Layered architecture seed
* AAP §0.4.1 — Transformation table row for
  ``app/blueprints/api/routes.py``
* AAP §0.4.2 — Import graph
* AAP §0.6.1 — Precondition gap (no Node source available)
* AAP §0.6.2 — Node→Python idiom translation
* AAP §0.7.4 — Open Questions Requiring User Clarification
* :mod:`app.errors` — centralized error envelope shape this module mirrors
* :mod:`app.blueprints.api` — Blueprint singleton (mount point
  ``/api``) imported by this module
"""

from __future__ import annotations

from flask import jsonify

from app.blueprints.api import api_bp

# =============================================================================
# Constants — placeholder response payload
# =============================================================================
# The placeholder body is sourced from these module-level constants so the
# strings remain identical across runtime, tests, and future changes. Pulling
# the literal out of the handler also makes the wire contract explicit and
# greppable: changes to either field require touching this section, not the
# handler body.
#
# The ``code`` field is an integer that matches the HTTP status header
# byte-for-byte (per the centralized error contract documented in
# :mod:`app.errors`). The ``message`` field carries the canonical IANA HTTP
# reason phrase for status 501. The ``detail`` field is a placeholder-only
# extension that explains the precondition gap; once the Node.js source is
# ported, the placeholder handler is removed and this constant becomes
# unused (the linter will then flag it for deletion).
# -----------------------------------------------------------------------------
_PLACEHOLDER_STATUS: int = 501
_PLACEHOLDER_MESSAGE: str = "Not Implemented"
_PLACEHOLDER_DETAIL: str = (
    "API endpoints will be ported from the original Node.js source. See AAP §0.7.4."
)


# =============================================================================
# Placeholder handler — ``GET /api/``
# =============================================================================
# Registered on :data:`api_bp` via the Flask 2.0+ method-specific decorator
# ``@api_bp.get(...)`` (preferred over the older
# ``@api_bp.route(..., methods=["GET"])`` form per the modern Flask 3.1.x
# style guide). The route path is ``/`` — combined with the Blueprint's
# ``url_prefix="/api"``, the externally addressable URL is ``/api/``.
#
# The trailing slash matters: Werkzeug's default ``strict_slashes=True``
# behaviour causes requests to ``/api`` (without trailing slash) to receive
# an HTTP 308 Permanent Redirect to ``/api/``. This is documented Flask
# behaviour and is the expected contract for this placeholder.
# -----------------------------------------------------------------------------
@api_bp.get("/")
def api_placeholder():
    """Placeholder endpoint reserved for the ported Node.js API surface.

    This view function exists solely to give the ``api`` Blueprint a
    well-defined response at its mount point while the repository awaits
    the original Node.js source (see Agent Action Plan §0.6.1, §0.7.4).
    Once the source is supplied, this handler is removed and replaced by
    the ported endpoints; the inline marker comment block immediately
    below this function documents the recommended porting pattern.

    Behaviour
    ---------
    Every request to ``GET /api/`` (or, by Werkzeug's default
    ``strict_slashes=True`` rewrite, ``GET /api`` followed by a 308
    redirect to the canonical URL) receives the same response:

    * HTTP status: ``501 Not Implemented`` — the IANA-canonical code for
      a request whose method is recognised by the server but the
      functionality required to satisfy it has not been implemented.
    * ``Content-Type: application/json`` — set automatically by
      :func:`flask.jsonify`.
    * JSON body — the centralized error envelope shape used elsewhere in
      the scaffold (mirroring :mod:`app.errors`), extended with a
      ``detail`` field that carries the porting note::

          {
              "error": {
                  "code": 501,
                  "message": "Not Implemented",
                  "detail": "API endpoints will be ported from the "
                            "original Node.js source. See AAP §0.7.4."
              }
          }

    The handler is intentionally side-effect-free: it performs no I/O,
    consults no configuration, and reads no request fields. This makes
    the placeholder trivially safe to call repeatedly (a feature
    container-orchestrator liveness probes occasionally rely on when
    operators forget to point them at ``/healthz``) and avoids ever
    raising an exception that would shadow the 501 status with a 500
    from :mod:`app.errors`.

    Returns:
        A ``(response, status)`` 2-tuple as understood by Flask's view
        return-value protocol: the first element is a
        :class:`flask.Response` carrying the JSON body, and the second
        element is the integer HTTP status code (``501``) applied to
        the response. The explicit tuple form (rather than a bare
        :class:`flask.Response`) guarantees the status header matches
        the ``code`` field embedded in the JSON body byte-for-byte.
    """
    response = jsonify(
        {
            "error": {
                "code": _PLACEHOLDER_STATUS,
                "message": _PLACEHOLDER_MESSAGE,
                "detail": _PLACEHOLDER_DETAIL,
            }
        }
    )
    return response, _PLACEHOLDER_STATUS


# ---------------------------------------------------------------------------
# PORTED NODE.JS ENDPOINTS GO BELOW THIS LINE
# ---------------------------------------------------------------------------
#
# When the original Node.js source is provided (see AAP §0.7.4), REMOVE the
# :func:`api_placeholder` handler above and add ported endpoints below
# following the AAP §0.6.2 idiom map. Recommended template:
#
#     from flask import request
#
#     @api_bp.get("/items")
#     def list_items():
#         # Map Node's ``req.query.limit`` -> ``request.args.get("limit")``
#         limit = request.args.get("limit", default=20, type=int)
#         # Delegate to a future ``app/services/items.py`` module — DO NOT
#         # embed business logic in this routes module (AAP §0.3.3).
#         items = ...
#         return jsonify({"items": items}), 200
#
#     @api_bp.post("/items")
#     def create_item():
#         # Map Node's ``req.body`` -> ``request.get_json(silent=True)``
#         payload = request.get_json(silent=True) or {}
#         # Validate, delegate to service, return result.
#         return jsonify({"item": ...}), 201
#
#     @api_bp.get("/items/<int:item_id>")
#     def get_item(item_id: int):
#         # Map Express ``req.params.id`` -> typed route converter +
#         # function argument. ``flask.abort(404)`` raises a
#         # ``werkzeug.exceptions.NotFound`` which is caught by the
#         # centralized handler in :mod:`app.errors` and rendered as the
#         # standard ``{"error": {"code": 404, "message": "Not Found"}}``
#         # envelope.
#         item = ...
#         if item is None:
#             from flask import abort
#             abort(404)
#         return jsonify({"item": item}), 200
#
# Layered architecture note (AAP §0.3.3): business logic MUST NOT live in
# this module. Future ``app/services/`` and ``app/repositories/`` modules
# will host that logic; route handlers here should only:
#
#   1. Parse the request (args, body, headers).
#   2. Delegate to a service function (one call per handler — fan-out
#      belongs in the service, not the route).
#   3. Serialize the service's return value with :func:`flask.jsonify`
#      and return an explicit ``(response, status)`` tuple.
#
# Error semantics MUST go through :mod:`app.errors`: call
# :func:`flask.abort` or raise :class:`werkzeug.exceptions.HTTPException`
# subclasses rather than constructing ``{"error": ...}`` envelopes inline.
# This guarantees the wire-level error contract stays identical across
# every Blueprint regardless of where the failure occurred.
# ---------------------------------------------------------------------------

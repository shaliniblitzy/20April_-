"""Route handlers for the ``main`` Blueprint (service-identity endpoints).

Purpose
-------
This module exposes the two service-identity endpoints that operators,
downstream automation, and external monitoring systems call to confirm
the service is alive and to discover its identity:

* ``GET /``        — Service banner JSON with helpful endpoint links.
* ``GET /version`` — ``{"name": ..., "version": ..., "python": ...}``
  for service identification.

The :data:`app.blueprints.main.main_bp` Blueprint (defined in the
sibling :mod:`app.blueprints.main` package initializer) has no
``url_prefix``, so the paths above are absolute. Both handlers use the
Flask 2.0+ method-specific decorator form (``@main_bp.get(...)``) per
the modern Flask 3.1.x style guide and return JSON via
:func:`flask.jsonify`, which sets ``Content-Type: application/json`` and
defaults the response to HTTP 200.

Behavioural contract
--------------------
Both endpoints are intentionally UNAUTHENTICATED for service-discovery
access. The banner and version responses are static-ish (the ``python``
field varies with the runtime version) and do not leak operational
secrets. They are safe to expose to load balancers, smoke-test scripts,
and uptime monitors without credentials.

Version resolution
------------------
The ``/version`` endpoint reports the scaffold's declared version
sourced from :data:`app.__version__` (the canonical single source of
truth that mirrors ``[project].version`` in ``pyproject.toml``). The
import is wrapped in a defensive ``try/except ImportError`` block —
falling back to a hardcoded ``"0.1.0"`` — to keep this routes module
loadable even in the rare scenario where the ``app`` package is only
partially initialised when this module is imported. The Python runtime
version comes from :func:`platform.python_version`, which returns
strings like ``"3.12.3"``.

References
----------
* AAP §0.3.1 — Refactored Structure (``app/blueprints/main/`` subtree)
* AAP §0.3.3 — Blueprint modularization; Service identity discovery
* AAP §0.4.1 — Transformation table row for
  ``app/blueprints/main/routes.py``
* AAP §0.4.2 — Import graph
"""

from __future__ import annotations

import platform

from flask import Response, jsonify

from app.blueprints.main import main_bp

# ---------------------------------------------------------------------------
# Version constant resolution.
# ---------------------------------------------------------------------------
# ``__version__`` lives in :mod:`app.__init__` as the canonical single
# source of truth, mirroring ``[project].version`` in ``pyproject.toml``.
# The try/except guard makes this module robust to the rare circular-import
# scenario where :mod:`app` is only partially initialised when this module
# is loaded (Flask Blueprint chain loading order). The hardcoded fallback
# value MUST stay in lock-step with ``app.__version__`` whenever the
# version is bumped.
try:
    from app import __version__ as APP_VERSION
except ImportError:  # pragma: no cover - defensive fallback
    APP_VERSION = "0.1.0"

# ---------------------------------------------------------------------------
# Service name constant.
# ---------------------------------------------------------------------------
# Sourced from the original repository identity recorded in AAP §0.8.2.
# The value carries no semantic meaning beyond service identification and
# may diverge from ``pyproject.toml``'s ``name`` field — which has stricter
# PEP 503 distribution-name constraints (digits-leading and trailing
# hyphens disallowed) that the human-readable service name need not honour.
SERVICE_NAME = "20April_-"


@main_bp.get("/")
def index() -> Response:
    """Service banner endpoint.

    Returns a JSON envelope identifying the service and listing the
    helpful endpoints clients can call to learn more about the
    running scaffold. The ``endpoints`` array is a self-documenting
    directory: operators hitting ``/`` should be able to discover the
    other addressable surfaces of the service without external docs.

    Returns:
        A :class:`flask.Response` containing a JSON object with the
        following keys:

        * ``service``: Human-readable service name (e.g.
          ``"20April_-"``).
        * ``message``: Brief description of the running scaffold.
        * ``endpoints``: List of helper paths exposed by the scaffold
          (``/healthz``, ``/readyz``, ``/version``, ``/api/``).

        Status: HTTP 200 (Flask default for :func:`flask.jsonify`
        responses); ``Content-Type: application/json``. The explicit
        :class:`flask.Response` return annotation (rather than a looser
        :data:`~flask.typing.ResponseReturnValue` union) documents that
        this handler always returns the concrete
        :class:`flask.Response` object produced by :func:`flask.jsonify`.
    """
    return jsonify(
        {
            "service": SERVICE_NAME,
            "message": "Flask scaffold",
            "endpoints": ["/healthz", "/readyz", "/version", "/api/"],
        }
    )


@main_bp.get("/version")
def version() -> Response:
    """Service version/identification endpoint.

    Returns a JSON envelope identifying the service by name, declared
    version, and the Python runtime version. Operators, deployment
    automation, and canary verifiers use this endpoint to confirm
    *what* is running — independent of orchestrator labels or build
    metadata that may be unavailable at the network edge.

    Returns:
        A :class:`flask.Response` containing a JSON object with the
        following keys:

        * ``name``: Human-readable service name (e.g.
          ``"20April_-"``).
        * ``version``: Declared scaffold version (e.g. ``"0.1.0"``)
          sourced from :data:`app.__version__`.
        * ``python``: Python runtime version reported by
          :func:`platform.python_version` (e.g. ``"3.12.3"``).

        Status: HTTP 200 (Flask default for :func:`flask.jsonify`
        responses); ``Content-Type: application/json``. The explicit
        :class:`flask.Response` return annotation matches the sibling
        :func:`index` handler so the public service-identity surface
        carries a uniform typed signature.
    """
    return jsonify(
        {
            "name": SERVICE_NAME,
            "version": APP_VERSION,
            "python": platform.python_version(),
        }
    )

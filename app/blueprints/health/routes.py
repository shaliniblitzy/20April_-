"""Route handlers for the ``health`` Blueprint (liveness/readiness probes).

Purpose
-------
This module exposes the two probe endpoints that container
orchestrators (Kubernetes, Docker Swarm, ECS, etc.) call to determine
container liveness and readiness:

* ``GET /healthz`` → ``{"status": "ok"}``    — liveness probe (HTTP 200)
* ``GET /readyz``  → ``{"status": "ready"}`` — readiness probe (HTTP 200)

The :data:`app.blueprints.health.health_bp` Blueprint (defined in the
sibling :mod:`app.blueprints.health` package initializer) has no
``url_prefix``, so the paths above are absolute. The ``-z`` suffix
matches the de-facto Kubernetes naming convention for machine-readable
probe endpoints.

Behavioural contract
--------------------
The probes are intentionally STATIC and UNAUTHENTICATED:

* **Static** — they return constant JSON regardless of application
  state. Deep health checks (database connectivity, downstream service
  pings, queue depths) are out of scope until persistence is introduced
  during the Node.js port (see AAP §0.7.4). Adding such checks here
  without explicit user requirements would make the probes susceptible
  to transient downstream failures and could cause spurious pod
  restarts.
* **Unauthenticated** — orchestrators must be able to probe them
  without credentials. Adding auth here would defeat the very purpose
  of the endpoints.

Both handlers use the Flask 2.0+ method-specific decorator form
(``@health_bp.get(...)``) per the modern Flask 3.1.x style guide; the
older ``@health_bp.route(..., methods=["GET"])`` form is no longer
preferred. JSON responses are produced by :func:`flask.jsonify`, which
sets ``Content-Type: application/json`` and defaults the status to
HTTP 200.

References
----------
* AAP §0.3.1 — Refactored Structure (``app/blueprints/health/`` subtree)
* AAP §0.3.3 — Blueprint modularization design pattern
* AAP §0.4.1 — Transformation table row for
  ``app/blueprints/health/routes.py``
* AAP §0.4.2 — Import graph
* AAP §0.6.7 — Cross-cutting concerns: health/readiness isolated in
  its own Blueprint
"""

from __future__ import annotations

from flask import Response, jsonify

from app.blueprints.health import health_bp


@health_bp.get("/healthz")
def healthz() -> Response:
    """Liveness probe endpoint.

    Returns a static JSON envelope confirming the Python process is
    alive and the Flask application can serve a request. Used by
    orchestrators (Kubernetes ``livenessProbe``, Docker ``HEALTHCHECK``,
    ECS health check, etc.) to decide whether to restart the container.

    MUST NOT perform deep health checks (database pings, downstream
    service calls, etc.). The endpoint is intentionally side-effect-free
    so it can be hit at high frequency without inducing load on
    downstream systems.

    Returns:
        A :class:`flask.Response` carrying the JSON body
        ``{"status": "ok"}`` with HTTP status 200 (Flask default for
        :func:`flask.jsonify` responses). The explicit
        :class:`flask.Response` return annotation (rather than a looser
        :data:`~flask.typing.ResponseReturnValue` union) documents that
        this handler always returns the concrete
        :class:`flask.Response` object produced by :func:`flask.jsonify`
        and never a ``(body, status)`` tuple or bare string — useful
        signal for static analysers and for human reviewers
        cross-referencing the endpoint contract.
    """
    return jsonify({"status": "ok"})


@health_bp.get("/readyz")
def readyz() -> Response:
    """Readiness probe endpoint.

    Returns a static JSON envelope confirming the service is ready to
    accept traffic. Used by orchestrators (Kubernetes
    ``readinessProbe``, load balancers, etc.) to decide whether to
    route traffic to the container.

    MUST NOT perform deep readiness checks (database migrations applied,
    cache warmed, queue connections established). Once the Node.js
    source is ported and external dependencies are wired in, deep
    readiness logic may be added — but only behind a configuration
    flag, never by default, to preserve the current low-latency probe
    semantics.

    Returns:
        A :class:`flask.Response` carrying the JSON body
        ``{"status": "ready"}`` with HTTP status 200 (Flask default
        for :func:`flask.jsonify` responses). The explicit
        :class:`flask.Response` return annotation matches the sibling
        :func:`healthz` handler so the probe pair has a uniform typed
        signature for static analysers and reviewers.
    """
    return jsonify({"status": "ready"})

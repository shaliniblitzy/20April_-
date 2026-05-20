"""``app.blueprints.health`` package initializer.

Purpose
-------
This module is the package initializer for the :mod:`app.blueprints.health`
sub-package. It defines the :data:`health_bp` Flask
:class:`flask.Blueprint` singleton WITHOUT a ``url_prefix`` — the routes
``/healthz`` (liveness) and ``/readyz`` (readiness) are exposed at the
application root as absolute paths, matching the de-facto Kubernetes
``-z`` probe naming convention (the trailing ``z`` is the historical
``machine-readable probe`` marker that orchestrators look for). The
sibling :mod:`app.blueprints.main` Blueprint is the only other prefix-less
Blueprint in the scaffold; :mod:`app.blueprints.api` is the *only*
Blueprint that carries a URL prefix (``/api``), per the explicit design
decision recorded in Agent Action Plan (AAP) §0.3.1.

Pattern
-------
Two side effects occur at module-import time, in this specific order:

1. The :data:`health_bp` Blueprint singleton is instantiated at module
   scope.
2. The sibling :mod:`app.blueprints.health.routes` module is imported
   *after* the Blueprint exists. ``routes.py`` uses ``@health_bp.route(...)``
   / ``@health_bp.get(...)`` decorators to attach view functions to the
   Blueprint; those decorators run during the import of ``routes.py``.

The ordering is non-negotiable: ``routes.py`` does
``from app.blueprints.health import health_bp`` and would raise
:class:`ImportError` if its import ran before the Blueprint was bound in
the package namespace. This is the standard Flask Blueprint package
layout documented across the Flask 3.1.x tutorials and reference docs
[web:flask-docs:installation].

Naming
------
The Blueprint *name* (the first positional argument to
:class:`flask.Blueprint`) is the string ``"health"``. Note that the
Blueprint name carries NO trailing ``z`` — the ``-z`` suffix is a
*route-path* convention (``/healthz``, ``/readyz``), not a
*blueprint-name* convention. This name:

* Is the prefix used by :func:`flask.url_for` — every view function
  ``handler`` declared on :data:`health_bp` is addressable as
  ``url_for("health.handler")`` (for example ``url_for("health.healthz")``
  resolves to ``/healthz`` and ``url_for("health.readyz")`` resolves to
  ``/readyz``).
* Appears in the output of ``flask routes`` as
  ``health.<view_function_name>``.
* Appears in the keys of :attr:`flask.Flask.blueprints` after
  ``app.register_blueprint(health_bp)`` — i.e. ``"health" in app.blueprints``
  is ``True`` once the application factory has run.

Changing the string here would silently break URL generation throughout
the application; it is treated as part of the public API.

Mount point
-----------
This Blueprint is instantiated WITHOUT a ``url_prefix`` keyword argument
on purpose. The two routes declared on :data:`health_bp` (``/healthz``
and ``/readyz``) are mounted as *absolute* paths at the application
root. Adding a ``url_prefix="/health"`` (or any other prefix) here would
relocate those endpoints under the prefix and silently break:

* Container-orchestrator liveness and readiness probes hitting
  ``/healthz`` and ``/readyz``. Kubernetes, Docker Swarm, ECS, Nomad,
  and most cloud load balancers default to these unprefixed paths.
* External monitoring services that scrape ``/healthz`` for uptime
  checks.
* The matching expectations recorded in :mod:`tests.test_health`.

The Flask application factory in :mod:`app` registers the Blueprint via
``app.register_blueprint(health_bp)``; no ``url_prefix`` keyword is
passed at registration either (AAP §0.6.2, Node→Python idiom
translation: ``app.use(probesRouter)`` →
``app.register_blueprint(health_bp)``).

Status
------
The two routes hosted by this Blueprint — ``GET /healthz`` (liveness:
``{"status": "ok"}``) and ``GET /readyz`` (readiness:
``{"status": "ready"}``) — are *real* scaffold endpoints, not
placeholders. They are operational the moment the application factory
runs and remain operational regardless of whether the original Node.js
source the user referenced is ever ported into this repository (see
AAP §0.6.1 for the precondition gap and AAP §0.7.4 for the open
clarification questions that gate the broader port).

The probes are intentionally STATIC (no database, downstream service,
or external dependency checks) and UNAUTHENTICATED (so orchestrators
can probe them without credentials). Deep health checks — checking
database connectivity, downstream API liveness, queue depths, etc. —
are out of scope until persistence and integrations are introduced
during the port (see AAP §0.7.4). Adding such checks here without
explicit user requirements would make the probes susceptible to
transient downstream failures and could cause spurious pod restarts.

Public API
----------
Only :data:`health_bp` is part of this package's public surface. The
``routes`` module is an implementation detail and is imported solely
for its side effect of attaching view functions to the Blueprint. The
explicit ``__all__`` declaration at the bottom of this file enforces
that contract for ``from app.blueprints.health import *`` consumers and
for static analysers.

References
----------
* AAP §0.3.1 — Refactored Structure (``app/blueprints/health/`` subtree).
* AAP §0.3.3 — Blueprint modularization design pattern.
* AAP §0.4.1 — Transformation table row for
  ``app/blueprints/health/__init__.py``.
* AAP §0.4.2 — Import graph (``app/__init__.py`` imports
  :data:`health_bp` from this package; ``app/blueprints/__init__.py``
  re-exports :data:`health_bp`).
* AAP §0.6.2 — Node→Python idiom translation
  (``express.Router()`` → :class:`flask.Blueprint`; ``app.use(router)``
  → :meth:`flask.Flask.register_blueprint`).
* AAP §0.6.7 — Cross-cutting concerns catalog: health/readiness
  isolated in its own Blueprint so liveness/readiness reasoning is
  independent of business-endpoint behaviour.
"""

from __future__ import annotations

from flask import Blueprint

# =============================================================================
# Blueprint singleton
# =============================================================================
# The Blueprint is instantiated at module scope so it can be imported by:
#
#   * ``app/__init__.py``  — to call ``app.register_blueprint(health_bp)``
#   * ``app/blueprints/__init__.py`` — to re-export ``health_bp`` from the
#     parent ``app.blueprints`` package
#   * ``app/blueprints/health/routes.py`` — to attach view functions via
#     the ``@health_bp.get(...)``, ``@health_bp.post(...)``, etc.
#     decorators
#
# Constructor arguments (in order):
#
#   1. ``"health"`` — the Blueprint NAME. Used by :func:`flask.url_for`
#      as the prefix in endpoint identifiers (``url_for("health.<view>")``)
#      and appears in the output of ``flask routes`` as ``health.<view>``.
#      Keep this string lowercase snake_case (it is part of the public
#      URL generation contract). Note the absence of a trailing ``z`` —
#      the ``-z`` suffix is a route-path convention (``/healthz``,
#      ``/readyz``), not a blueprint-name convention.
#
#   2. ``__name__`` — the import name. Flask uses this to resolve the
#      package's root path, which it needs even when no static folder /
#      template folder is declared (no templates or static assets exist
#      in this scaffold; see AAP §0.2.3 and §0.3.4).
#
# Deliberate omissions:
#
#   * NO ``url_prefix=...`` keyword — the routes ``/healthz`` and
#     ``/readyz`` are mounted at the application root as absolute paths.
#     This is the explicit design choice recorded in AAP §0.3.1 and
#     reiterated in the assigned-folder Conventions. Adding any prefix
#     here would silently break container-orchestrator probes (see the
#     "Mount point" section of the module docstring above).
#   * NO ``template_folder`` or ``static_folder`` kwargs — this
#     Blueprint serves JSON only (AAP §0.2.3, §0.3.4). Adding either
#     would be confusing dead weight that the future port can introduce
#     when (and if) the Node.js source turns out to render HTML.
health_bp = Blueprint("health", __name__)
"""Blueprint singleton for the liveness/readiness probe endpoints (mounted at the application root).

Attributes of interest after construction:

* ``health_bp.name == "health"`` — used by :func:`flask.url_for` as the
  endpoint prefix (``url_for("health.healthz")``,
  ``url_for("health.readyz")``).
* ``health_bp.url_prefix is None`` — no URL prefix; routes declared on
  this Blueprint are exposed at absolute paths once the Blueprint is
  registered on a Flask application via
  :meth:`flask.Flask.register_blueprint`.

The Blueprint is imported by:

* :mod:`app` — the application factory calls
  ``app.register_blueprint(health_bp)`` to mount it.
* :mod:`app.blueprints` — the package aggregator re-exports it.
* :mod:`app.blueprints.health.routes` — view functions attach to it via
  decorators.

The Blueprint hosts:

* ``GET /healthz`` — liveness probe returning ``{"status": "ok"}``.
* ``GET /readyz``  — readiness probe returning ``{"status": "ready"}``.

Both probes are intentionally static and unauthenticated; see the
"Status" section of the module docstring above for the rationale.
"""

# =============================================================================
# Route registration side effect
# =============================================================================
# The ``routes`` module is imported AFTER ``health_bp`` is defined so the
# decorator-based handler registrations in ``routes.py`` (e.g.
# ``@health_bp.get("/healthz")``, ``@health_bp.get("/readyz")``) can
# attach to the already-bound :data:`health_bp` symbol. This is the
# canonical Flask Blueprint package layout documented across Flask 3.1.x
# tutorials.
#
# Lint suppressions on this single line are intentional:
#
#   * ``E402`` — "module-level import not at top of file". The ordering
#     (Blueprint declaration BEFORE this import) is REQUIRED for Flask
#     Blueprint registration to function. Reversing the order produces
#     an :class:`ImportError` at module load.
#   * ``F401`` — "imported but unused". The import is for its SIDE
#     EFFECT (registering view functions on :data:`health_bp`), not for
#     using the :mod:`routes` symbol directly. The package-level
#     ``per-file-ignores`` rule in ``pyproject.toml`` already tolerates
#     ``F401`` in ``__init__.py`` modules, but the explicit ``noqa``
#     keeps the intent legible without relying on that global rule.
#
# The relative import form (``from . import routes``) is used here per
# the checkpoint-prescribed blueprint-initializer pattern (see the
# Checkpoint 2 review finding MINOR/health-init). The relative form is
# the canonical Flask-tutorial idiom for blueprint package initializers
# because it makes the intra-package side-effect explicit: the
# ``routes`` module lives in the SAME package as this initializer and
# is imported solely to trigger its decorator-based route-registration
# side effects. The absolute form ``from app.blueprints.health import
# routes`` produces identical runtime behaviour but obscures the
# intra-package relationship; the relative form keeps the import
# graph's locality visible in a single line.
from . import routes  # noqa: E402, F401

# =============================================================================
# Public API declaration
# =============================================================================
# Explicitly enumerate the public surface of this package. Anything not
# listed below is considered private to :mod:`app.blueprints.health` and
# may change without notice.
#
# Only :data:`health_bp` is exposed:
#
#   * The :mod:`routes` module is an implementation detail; its handlers
#     are reachable via the Blueprint, not via direct import.
#   * The :class:`flask.Blueprint` class itself is re-exported by
#     :mod:`flask` and should be imported from there, not from this
#     package.
#
# ``__all__`` is also consulted by static analysers (ruff/pyflakes) to
# recognise that :data:`health_bp` is intentionally re-exportable and
# therefore not an "imported but unused" symbol when consumed via
# ``from app.blueprints.health import health_bp``.
__all__ = ["health_bp"]

"""``app.blueprints.api`` package initializer.

Purpose
-------
This module is the package initializer for the :mod:`app.blueprints.api`
sub-package. It defines the :data:`api_bp` Flask :class:`flask.Blueprint`
singleton with ``url_prefix="/api"`` — the *only* Blueprint in the
scaffold that carries a URL prefix. The sibling Blueprints
:mod:`app.blueprints.health` and :mod:`app.blueprints.main` mount at the
application root, per the explicit design decision recorded in Agent
Action Plan (AAP) §0.3.1.

Pattern
-------
Two side effects occur at module-import time, in this specific order:

1. The :data:`api_bp` Blueprint singleton is instantiated at module scope.
2. The sibling :mod:`app.blueprints.api.routes` module is imported *after*
   the Blueprint exists. ``routes.py`` uses ``@api_bp.route(...)`` /
   ``@api_bp.get(...)`` decorators to attach view functions to the
   Blueprint; those decorators run during the import of ``routes.py``.

The ordering is non-negotiable: ``routes.py`` does
``from app.blueprints.api import api_bp`` and would raise
:class:`ImportError` if its import ran before the Blueprint was bound in
the package namespace. This is the standard Flask Blueprint package
layout documented across the Flask 3.1.x tutorials and reference docs
[web:flask-docs:installation].

Naming
------
The Blueprint *name* (the first positional argument to
:class:`flask.Blueprint`) is the string ``"api"``. This name:

* Is the prefix used by :func:`flask.url_for` — every view function
  ``handler`` declared on :data:`api_bp` is addressable as
  ``url_for("api.handler")``.
* Appears in the output of ``flask routes`` as ``api.<view_function_name>``.
* Appears in the keys of :attr:`flask.Flask.blueprints` after
  ``app.register_blueprint(api_bp)``.

Changing the string here would silently break URL generation throughout
the application; it is treated as part of the public API.

Mount point
-----------
The keyword argument ``url_prefix="/api"`` namespaces every route declared
on :data:`api_bp` under ``/api/*``. The Flask application factory in
:mod:`app` registers the Blueprint via ``app.register_blueprint(api_bp)``;
no second ``url_prefix`` argument is passed at registration because the
prefix is already declared on the Blueprint itself (AAP §0.6.2,
Node→Python idiom translation: ``app.use("/api", apiRouter)`` →
``app.register_blueprint(api_bp)``).

Status
------
The Blueprint currently hosts only a placeholder handler returning
HTTP 501 (see AAP §0.6.1) because the original Node.js source the user
referenced is not present in this repository. Ported endpoints will be
added to ``routes.py`` once the original source is supplied — see
AAP §0.7.4 for the open clarification questions that gate that work.

Public API
----------
Only :data:`api_bp` is part of this package's public surface. The
``routes`` module is an implementation detail and is imported solely for
its side effect of attaching view functions to the Blueprint. The
explicit ``__all__`` declaration at the bottom of this file enforces that
contract for ``from app.blueprints.api import *`` consumers and for
static analysers.

References
----------
* AAP §0.3.1 — Refactored Structure (``app/blueprints/api/`` subtree).
* AAP §0.3.3 — Blueprint modularization design pattern.
* AAP §0.4.1 — Transformation table row for
  ``app/blueprints/api/__init__.py``.
* AAP §0.4.2 — Import graph (``app/__init__.py`` imports
  :data:`api_bp` from this package; ``app/blueprints/__init__.py``
  re-exports :data:`api_bp`).
* AAP §0.6.1 — Precondition gap (no Node source available).
* AAP §0.6.2 — Node→Python idiom translation (``express.Router()`` →
  ``flask.Blueprint``).
* AAP §0.7.4 — Open Questions Requiring User Clarification.
"""

from __future__ import annotations

from flask import Blueprint

# =============================================================================
# Blueprint singleton
# =============================================================================
# The Blueprint is instantiated at module scope so it can be imported by:
#
#   * ``app/__init__.py``  — to call ``app.register_blueprint(api_bp)``
#   * ``app/blueprints/__init__.py`` — to re-export ``api_bp`` from the
#     parent ``app.blueprints`` package
#   * ``app/blueprints/api/routes.py`` — to attach view functions via the
#     ``@api_bp.get(...)``, ``@api_bp.post(...)``, etc. decorators
#
# Constructor arguments (in order):
#
#   1. ``"api"`` — the Blueprint NAME. Used by :func:`flask.url_for` as the
#      prefix in endpoint identifiers (``url_for("api.<view>")``) and
#      appears in the output of ``flask routes`` as ``api.<view>``. Keep
#      this string lowercase snake_case (it is part of the public URL
#      generation contract).
#
#   2. ``__name__`` — the import name. Flask uses this to resolve the
#      package's root path, which it needs even when no static folder /
#      template folder is declared (no templates or static assets exist
#      in this scaffold; see AAP §0.2.3 and §0.3.4).
#
#   3. ``url_prefix="/api"`` — every route declared on this Blueprint is
#      mounted under ``/api/*``. This is the ONLY Blueprint in the
#      scaffold that carries a URL prefix; ``health_bp`` and ``main_bp``
#      mount at the application root.
#
# No ``template_folder`` or ``static_folder`` kwargs are supplied: this
# Blueprint serves JSON only (AAP §0.2.3, §0.3.4). Adding either would be
# confusing dead weight that the future port can introduce when (and if)
# the Node.js source turns out to render HTML.
api_bp = Blueprint("api", __name__, url_prefix="/api")
"""Blueprint singleton for the JSON API surface (mounted at ``/api/*``).

Attributes of interest after construction:

* ``api_bp.name == "api"`` — used by :func:`flask.url_for` as the
  endpoint prefix.
* ``api_bp.url_prefix == "/api"`` — every route declared on this
  Blueprint is exposed under this prefix once the Blueprint is
  registered on a Flask application via
  :meth:`flask.Flask.register_blueprint`.

The Blueprint is imported by:

* :mod:`app` — the application factory calls
  ``app.register_blueprint(api_bp)`` to mount it.
* :mod:`app.blueprints` — the package aggregator re-exports it.
* :mod:`app.blueprints.api.routes` — view functions attach to it via
  decorators.
"""

# =============================================================================
# Route registration side effect
# =============================================================================
# The ``routes`` module is imported AFTER ``api_bp`` is defined so the
# decorator-based handler registrations in ``routes.py`` (e.g.
# ``@api_bp.get("/")``) can attach to the already-bound :data:`api_bp`
# symbol. This is the canonical Flask Blueprint package layout documented
# across Flask 3.1.x tutorials.
#
# Lint suppressions on this single line are intentional:
#
#   * ``E402`` — "module-level import not at top of file". The ordering
#     (Blueprint declaration BEFORE this import) is REQUIRED for Flask
#     Blueprint registration to function. Reversing the order produces an
#     :class:`ImportError` at module load.
#   * ``F401`` — "imported but unused". The import is for its SIDE EFFECT
#     (registering view functions on :data:`api_bp`), not for using the
#     :mod:`routes` symbol directly. The package-level
#     ``per-file-ignores`` rule in ``pyproject.toml`` already tolerates
#     ``F401`` in ``__init__.py`` modules, but the explicit ``noqa``
#     keeps the intent legible without relying on that global rule.
#
# The absolute import form (``from app.blueprints.api import routes``)
# is preferred over the relative form (``from . import routes``) for
# consistency with the absolute-import convention used elsewhere in the
# scaffold and for clarity in IDE jump-to-definition operations. Both
# forms produce identical runtime behaviour.
from app.blueprints.api import routes  # noqa: E402, F401

# =============================================================================
# Public API declaration
# =============================================================================
# Explicitly enumerate the public surface of this package. Anything not
# listed below is considered private to :mod:`app.blueprints.api` and may
# change without notice.
#
# Only :data:`api_bp` is exposed:
#
#   * The :mod:`routes` module is an implementation detail; its handlers
#     are reachable via the Blueprint, not via direct import.
#   * The :class:`flask.Blueprint` class itself is re-exported by
#     :mod:`flask` and should be imported from there, not from this
#     package.
#
# ``__all__`` is also consulted by static analysers (ruff/pyflakes) to
# recognise that :data:`api_bp` is intentionally re-exportable and
# therefore not an "imported but unused" symbol when consumed via
# ``from app.blueprints.api import api_bp``.
__all__ = ["api_bp"]

"""``app.blueprints`` package initializer (re-export aggregator).

Purpose
-------
This module is the package initializer for the :mod:`app.blueprints`
package. Its SOLE purpose is to re-export the three Blueprint singleton
objects defined in the sibling sub-packages so that callers can import
them with a clean, single-statement-per-blueprint pattern::

    from app.blueprints import health_bp, main_bp, api_bp

The canonical-path imports continue to work in parallel, for example::

    from app.blueprints.health import health_bp

Both access paths are valid. The aggregator is a convenience layer; the
sub-package paths remain the authoritative source of each Blueprint.

Pattern
-------
This file is a pure re-export module. It contains no functions, classes,
loggers, or runtime side effects beyond the import statements
themselves. The Blueprint singletons it aggregates are constructed in
their respective sibling sub-packages (:mod:`app.blueprints.health`,
:mod:`app.blueprints.main`, :mod:`app.blueprints.api`); see those
modules for the actual instantiation logic, the URL-prefix decisions,
and the route-binding side effects.

Public API
----------
Only the three Blueprint singletons are part of this package's public
surface:

* :data:`health_bp` — health/readiness probe Blueprint
  (``url_prefix=None``; exposes ``/healthz`` and ``/readyz``).
* :data:`main_bp` — main service-identity Blueprint
  (``url_prefix=None``; exposes ``/`` and ``/version``).
* :data:`api_bp` — API placeholder Blueprint
  (``url_prefix="/api"``; exposes ``/api/`` and future ported endpoints).

The explicit ``__all__`` declaration at the bottom of this module also
acts as a documented re-export marker that satisfies ruff's
``__init__.py``-aware lint rule for "imported but unused" symbols.

References
----------
* AAP §0.3.1 — Refactored Structure (``app/blueprints/`` subtree)
* AAP §0.3.3 — Blueprint modularization design pattern
* AAP §0.4.1 — Transformation table row for ``app/blueprints/__init__.py``
* AAP §0.4.2 — Import graph
* AAP §0.6.7 — Cross-cutting concerns catalog
"""

from __future__ import annotations

from app.blueprints.api import api_bp
from app.blueprints.health import health_bp
from app.blueprints.main import main_bp

# Public API surface. Listed in the AAP §0.3.1 / §0.4.1 declaration order
# (health → main → api) so the public surface mirrors the registration
# order used by :func:`app.create_app`. The aggregator deliberately omits
# every internal helper (``Blueprint`` class, ``routes`` modules) so the
# package's contract stays minimal.
__all__ = [
    "health_bp",
    "main_bp",
    "api_bp",
]

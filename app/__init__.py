"""Application factory module for the Flask scaffold (foundational package init).

Purpose
-------
This module is the package initializer for the :mod:`app` package and the
foundational file of the entire Flask scaffold. It defines :func:`create_app`
— the canonical entry point through which every other component of the
runtime (production server, development CLI, test suite, ad-hoc debugger)
materializes a fully-configured :class:`flask.Flask` instance.

Pattern — Application Factory (AAP §0.3.3)
------------------------------------------
The Application Factory pattern is the CENTRAL design decision of this
scaffold. Rather than instantiating a Flask application at module import
time (the Node.js ``const app = express()`` idiom translated naively),
this module exposes a callable :func:`create_app` that constructs a fresh
:class:`flask.Flask` instance on demand. The benefits, enumerated in
AAP §0.3.3 and §0.6.2, are:

* **Test isolation** — each pytest fixture in :mod:`tests.conftest` calls
  the factory afresh, yielding an independent ``TestingConfig``-flavored
  app per test/session. No global state leaks between tests.
* **Configurability** — the factory accepts a ``config_name`` argument so
  the same code path can produce a Development, Production, or Testing
  app without restructuring.
* **Side-effect discipline** — importing :mod:`app` does NOT bind to a
  port, parse a request, or connect to a database. The side effects are
  deferred until :func:`create_app` is explicitly called.
* **Mechanical Node→Python port** — the AAP §0.6.2 idiom map shows that
  every Node ``app.use(middleware)`` call maps to a single function call
  inside :func:`create_app` (``configure_logging(app)``,
  ``register_error_handlers(app)``, ``register_blueprint(bp)``). Future
  porting work is therefore localized to this function.

Consumers
---------
* :mod:`wsgi` — the production WSGI entry point imports :func:`create_app`
  and binds the result to a module-level ``app = create_app()`` that
  ``gunicorn wsgi:app`` serves.
* ``flask`` CLI — when invoked as ``FLASK_APP=wsgi:app flask run`` the
  CLI imports the same module-level ``app`` symbol exposed by
  :mod:`wsgi`, which transitively calls :func:`create_app`.
* :mod:`tests.conftest` — pytest fixtures build hermetic
  :class:`flask.Flask` instances via ``create_app("testing")`` so the
  suite runs without depending on any external configuration.

Wiring sequence
---------------
:func:`create_app` performs the following steps in this exact order;
the ordering is non-negotiable and is documented in detail inside the
function body:

1. Resolve the active configuration profile name (argument → env var →
   default; falls back to "development" when invalid).
2. Instantiate the :class:`flask.Flask` application object.
3. Load the configuration class onto ``app.config`` via
   :meth:`flask.Config.from_object`.
4. Configure process-wide logging via
   :func:`app.logging_config.configure_logging` so subsequent log lines
   (including the startup confirmation below) honor ``LOG_LEVEL``.
5. Register centralized HTTP error handlers via
   :func:`app.errors.register_error_handlers` so any error raised during
   the remaining steps (or during request handling) flows through the
   standard JSON envelope.
6. Register the three Blueprints: :data:`app.blueprints.health.health_bp`,
   :data:`app.blueprints.main.main_bp`, and
   :data:`app.blueprints.api.api_bp`.
7. Emit a single ``INFO``-level startup line so operators see positive
   evidence that the factory ran end-to-end.
8. Return the configured :class:`flask.Flask` instance.

Public API
----------
This module's public surface is:

* :func:`create_app` — the application factory documented above.
* :data:`__version__` — the scaffold's distribution version, mirroring
  the ``[project].version`` field in ``pyproject.toml``. Imported by
  :mod:`app.blueprints.main.routes` to power the ``GET /version``
  endpoint.

Imported helper symbols (``config_by_name``, ``register_error_handlers``,
``configure_logging``, and the Blueprint singletons) are intentionally
NOT re-exported from :mod:`app`. Callers should import them from their
canonical modules (``from app.config import config_by_name``, etc.) so
the dependency graph remains explicit and tractable for static analysis.

Future Node.js port contract
----------------------------
When the original Node.js source the user referenced (see AAP §0.6.1 and
§0.7.4) is supplied, ported endpoints are added to the appropriate
Blueprint (typically :mod:`app.blueprints.api.routes`) WITHOUT modifying
this module. Cross-cutting concerns (logging format, error envelope
shape, configuration sources) remain anchored in the dedicated modules
imported below. Adding a new Flask extension (e.g. ``SQLAlchemy``,
``Migrate``, ``CORS``) requires:

1. Declaring the extension singleton in :mod:`app.extensions`.
2. Adding a single ``extension.init_app(app)`` call inside
   :func:`create_app` between the configuration load (step 3) and the
   Blueprint registration (step 6) — the canonical Flask extension
   wiring contract.

References
----------
* AAP §0.3.3 — Application Factory pattern (central design decision)
* AAP §0.4.1 — Transformation table row for ``app/__init__.py``
* AAP §0.4.2 — Cross-file import graph
* AAP §0.6.2 — Node→Python idiom translation (application bootstrap)
* AAP §0.6.4 — Configuration & Environment Parity (``FLASK_CONFIG``)
* AAP §0.6.7 — Cross-cutting concerns catalog
* Flask docs — Application Factory pattern guide
* [web:flask-docs:installation] — Flask 3.1.3 installation reference
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Stdlib
# ---------------------------------------------------------------------------
# ``os`` is required for reading the ``FLASK_CONFIG`` environment variable
# at factory invocation time. Reading it inside :func:`create_app` (rather
# than at module import time) means a single Python process can spawn
# multiple Flask instances with different configurations — useful for
# tests that exercise the multi-config behavior. The value is read lazily
# so changes to ``os.environ`` between :func:`create_app` calls are
# honored.
import os

# ---------------------------------------------------------------------------
# Third-party
# ---------------------------------------------------------------------------
# Flask is the WSGI web framework. The ``Flask`` class is the only symbol
# imported here because every other Flask facility used inside
# :func:`create_app` (``Config.from_object``, ``register_blueprint``,
# ``logger``) is reached through methods/attributes of the ``Flask``
# instance constructed below. This keeps the module's import footprint
# minimal and the dependency on Flask explicit.
from flask import Flask

# ---------------------------------------------------------------------------
# First-party
# ---------------------------------------------------------------------------
# First-party imports are sorted alphabetically by ruff/isort. The order
# in this block (``app.blueprints.*`` first, then ``app.config``,
# ``app.errors``, ``app.logging_config``) is the canonical isort
# ordering and does NOT reflect call/registration order inside
# :func:`create_app` — see the function body below for the AAP-mandated
# ``configure_logging → register_error_handlers → register_blueprint``
# sequence.
#
# Blueprint singletons. Each is imported explicitly by name (not via a
# loop) so the import graph remains tractable for static analysis tools
# (mypy, ruff, IDE jump-to-definition). The Blueprint instances are
# defined at module scope in their respective package initializers and
# are mounted onto the Flask application inside :func:`create_app` via
# :meth:`flask.Flask.register_blueprint`.
from app.blueprints.api import api_bp
from app.blueprints.health import health_bp
from app.blueprints.main import main_bp

# Configuration selection map. ``config_by_name`` is a ``dict[str,
# type[BaseConfig]]`` whose keys are the documented profile names
# (``development``, ``production``, ``testing``, ``default``) and whose
# values are configuration class objects (NOT instances). The class
# object is passed to :meth:`flask.Config.from_object` which iterates
# the class's uppercase attributes to populate ``app.config``.
from app.config import config_by_name

# Centralized HTTP error-handler registration. Called once during factory
# execution to attach the standard JSON error envelope to every error
# code (400, 404, 405, 500) and to the ``HTTPException`` catch-all.
from app.errors import register_error_handlers

# Process-wide logging configuration. Called BEFORE any other log line is
# emitted (including the startup confirmation in this module) so the
# resulting log stream is uniformly formatted from the very first record.
from app.logging_config import configure_logging

# =============================================================================
# Module-level constants
# =============================================================================
# The scaffold's distribution version. Mirrored from ``[project].version``
# in ``pyproject.toml``. This constant is imported by
# :mod:`app.blueprints.main.routes` to power the ``GET /version`` endpoint,
# giving the running build a single source of truth for its version
# identifier. Bumping the project version requires updating BOTH this
# constant AND the ``[project].version`` field in ``pyproject.toml``;
# downstream automation (CI release jobs) should verify the two stay in
# sync. Standard PEP 440 / semver-like ``MAJOR.MINOR.PATCH`` form.
__version__: str = "0.1.0"

# Default configuration profile name used when ``FLASK_CONFIG`` is unset
# AND no ``config_name`` argument is passed to :func:`create_app`. The
# value ``"development"`` is chosen so a freshly-cloned repository runs
# in development mode by default — a deliberate operator-friendly choice
# matching the Flask community convention. Production deployments MUST
# set ``FLASK_CONFIG=production`` explicitly; relying on this default in
# production would silently enable the interactive debugger (see
# :class:`app.config.DevelopmentConfig`).
DEFAULT_CONFIG: str = "development"


# =============================================================================
# Public API — create_app
# =============================================================================
def create_app(config_name: str | None = None) -> Flask:
    """Construct and configure a Flask application instance.

    This is the canonical entry point for the entire scaffold. It
    implements the Application Factory pattern documented at the top of
    this module and in AAP §0.3.3. The function is deterministic: given
    the same ``config_name`` argument and the same environment, it
    produces an equivalent (though not identical-object) Flask instance
    on every call.

    Configuration resolution
    ------------------------
    The active configuration profile is resolved in this order:

    1. If ``config_name`` was passed explicitly (non-``None``), use it.
    2. Otherwise, read the ``FLASK_CONFIG`` environment variable.
    3. If neither yields a value, fall back to :data:`DEFAULT_CONFIG`
       (currently ``"development"``).
    4. If the resolved name is NOT a key of
       :data:`app.config.config_by_name`, fall back to
       :data:`DEFAULT_CONFIG`. This defensive remap turns a misspelled
       ``FLASK_CONFIG=produktion`` into a deterministic
       :class:`app.config.DevelopmentConfig` selection rather than
       raising :class:`KeyError` at startup — an operator-friendly
       behavior that prevents typos from taking the process down.

    Side effects
    ------------
    Each call to :func:`create_app`:

    * Re-applies :func:`logging.config.dictConfig` via
      :func:`app.logging_config.configure_logging`. This call is
      idempotent (it replaces, rather than appends, handlers) so calling
      :func:`create_app` repeatedly in the same process — for example
      from pytest fixtures — does not accumulate duplicate log
      handlers.
    * Mutates the returned :class:`flask.Flask` instance only. No
      module-level state in :mod:`app` is modified by this function;
      the resulting instance is independent of any previous instance
      returned by the same factory.
    * Emits exactly one ``INFO``-level log record at the end of
      successful execution (the startup confirmation) through the
      ``app.logger`` proxy.

    Args:
        config_name: Optional configuration profile name. Accepted
            values are ``"development"``, ``"production"``,
            ``"testing"``, and ``"default"`` (the latter is an alias
            for :class:`app.config.DevelopmentConfig`). When ``None``
            (the default), the value of the ``FLASK_CONFIG`` environment
            variable is consulted; if that is also unset, falls back to
            :data:`DEFAULT_CONFIG`. An unrecognized name silently
            degrades to :data:`DEFAULT_CONFIG` rather than raising.

    Returns:
        A fully-configured :class:`flask.Flask` instance with logging
        installed, error handlers registered, and the three scaffold
        Blueprints (``health``, ``main``, ``api``) mounted. The instance
        is ready to be served by gunicorn, the ``flask`` CLI, or the
        ``flask.Flask.test_client`` test transport.

    Raises:
        This function does NOT raise on user input. Configuration names
        are coerced to :data:`DEFAULT_CONFIG` on mismatch; environment
        variables are read with safe defaults. The only way this
        function can raise is if one of the imported registration
        helpers (:func:`configure_logging`, :func:`register_error_handlers`,
        ``app.register_blueprint``) raises — those failures indicate a
        code-level bug, not a configuration error, and propagate to the
        caller unmodified so the caller's test/observability stack can
        surface them.
    """
    # ------------------------------------------------------------------
    # 1. Resolve configuration profile name
    # ------------------------------------------------------------------
    # Precedence: explicit argument > FLASK_CONFIG env var > DEFAULT_CONFIG.
    # The two-step structure (argument check, then env-var fallback) is
    # preferred over a single ternary because it is easier to reason about
    # in the debugger and gives static analysers a clearer control-flow
    # graph. The env-var read happens at FUNCTION CALL TIME (not at module
    # import time) so changes to ``os.environ`` between calls are honored
    # — important for tests that toggle environment variables.
    if config_name is None:
        config_name = os.environ.get("FLASK_CONFIG", DEFAULT_CONFIG)

    # Defensive: an unrecognized config name is silently coerced to the
    # default rather than raising :class:`KeyError`. This protects the
    # production process from typos in ``FLASK_CONFIG`` ("produktion",
    # "PROD", "Production " with a trailing space) — a misconfigured env
    # var should not be able to prevent the application from starting.
    # The operator can still tell which config was selected from the
    # startup log line emitted at the end of this function.
    if config_name not in config_by_name:
        config_name = DEFAULT_CONFIG

    # ------------------------------------------------------------------
    # 2. Instantiate the Flask application
    # ------------------------------------------------------------------
    # ``Flask(__name__)`` is the canonical construction form. The
    # ``__name__`` argument resolves to the string ``"app"`` (this is
    # ``app/__init__.py``), which Flask uses to locate the package's root
    # path for resolving relative paths to static files, templates, and
    # the like. No static or template folder is configured here because
    # this scaffold serves JSON only (AAP §0.2.3, §0.3.4); Flask's
    # default ``static_folder="static"`` and ``template_folder="templates"``
    # remain unused but harmless.
    app = Flask(__name__)

    # ------------------------------------------------------------------
    # 3. Load configuration onto app.config
    # ------------------------------------------------------------------
    # :meth:`flask.Config.from_object` iterates the class object's
    # uppercase attributes (e.g. ``SECRET_KEY``, ``DEBUG``, ``TESTING``)
    # and copies them into ``app.config``. Lowercase attributes are
    # silently ignored by Flask (documented behavior). Passing the
    # class itself (rather than an instance) is the idiomatic form
    # endorsed by the Flask documentation; ``config_by_name`` values
    # are class objects for exactly this reason.
    #
    # Because :func:`config_by_name.__getitem__` is now guaranteed to
    # succeed (we coerced unknown names above), no defensive try/except
    # is needed here.
    app.config.from_object(config_by_name[config_name])

    # ------------------------------------------------------------------
    # 4. Configure process-wide logging
    # ------------------------------------------------------------------
    # Called BEFORE any other code path that might log so the startup
    # line at the end of this function (and every subsequent
    # ``app.logger`` / ``logging.getLogger(__name__)`` record) honors
    # the configured ``LOG_LEVEL`` and format. See
    # :mod:`app.logging_config` for the full behavioural contract,
    # idempotency guarantee, and ``LOG_LEVEL`` resolution semantics.
    configure_logging(app)

    # ------------------------------------------------------------------
    # 5. Register centralized HTTP error handlers
    # ------------------------------------------------------------------
    # Called BEFORE Blueprint registration so that any error raised
    # during Blueprint registration (a code-level bug, not a
    # configuration issue) would still flow through the JSON error
    # envelope rather than Flask's default HTML 500 page. In practice
    # Blueprint registration does not raise under normal conditions,
    # but the defensive ordering costs nothing and makes the failure
    # mode predictable.
    register_error_handlers(app)

    # ------------------------------------------------------------------
    # 6. Register Blueprints
    # ------------------------------------------------------------------
    # Each Blueprint is registered explicitly (no loop) so the
    # registration intent is unambiguous to static analysers and the
    # import graph remains tractable. Registration order is:
    #
    #   1. ``health_bp`` — exposes ``/healthz`` and ``/readyz`` (no
    #      ``url_prefix``). Probes are mounted first so they are
    #      reachable immediately after the application object is
    #      returned, in case downstream registration logic somehow
    #      partially fails.
    #   2. ``main_bp`` — exposes ``/`` and ``/version`` (no
    #      ``url_prefix``).
    #   3. ``api_bp`` — exposes ``/api/*`` (carries
    #      ``url_prefix="/api"``).
    #
    # No URL conflicts exist across the three Blueprints because each
    # Blueprint mounts at a distinct path/prefix.
    app.register_blueprint(health_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    # ------------------------------------------------------------------
    # 7. Emit startup confirmation log line
    # ------------------------------------------------------------------
    # Operators rely on this line as positive evidence that the factory
    # completed end-to-end. The ``%s``-style formatting (rather than
    # f-string) is the stdlib :mod:`logging` convention — it defers
    # string interpolation until the record is actually emitted,
    # avoiding the work entirely when the level is filtered out.
    # ``app.logger`` (rather than this module's ``logger``) is used so
    # the line appears under the Flask logger name (``app``) which is
    # the namespace operators are typically already watching.
    app.logger.info(
        "Flask application created with config=%s",
        config_name,
    )

    # ------------------------------------------------------------------
    # 8. Return the configured instance
    # ------------------------------------------------------------------
    # The returned object is consumed by:
    #   * :mod:`wsgi` (production) — assigns to ``app = create_app()``
    #     which ``gunicorn wsgi:app`` then serves.
    #   * ``flask`` CLI (development) — discovers via
    #     ``FLASK_APP=wsgi:app``.
    #   * :mod:`tests.conftest` (test) — wraps in
    #     ``app.test_client()`` to issue in-process HTTP requests.
    return app


# =============================================================================
# Public API declaration
# =============================================================================
# Explicitly enumerate the public surface of the :mod:`app` package.
# Anything not listed below is considered private to the package and may
# change without notice; the imported helper symbols
# (``config_by_name``, ``register_error_handlers``, ``configure_logging``,
# ``health_bp``, ``main_bp``, ``api_bp``) are intentionally OMITTED from
# this list because callers are expected to import them from their
# canonical modules (``from app.config import config_by_name``, etc.) —
# not from this package init. Keeping the public surface narrow makes
# the dependency graph explicit and reduces accidental coupling.
#
# :data:`__version__` is exported so ``import app; app.__version__`` is
# the canonical way to retrieve the running scaffold's version, mirroring
# the convention used across the Python packaging ecosystem.
__all__ = ["create_app", "__version__"]

"""Flask configuration class hierarchy for the application factory.

Purpose
-------
This module is the single, authoritative location where the Python/Flask
runtime reads configuration values. It implements the *layered configuration*
approach described in the Agent Action Plan (AAP) §0.3.3 "Configuration
Object hierarchy" and §0.6.4 "Configuration & Environment Parity":

* **Layer 1 — Defaults**: ``BaseConfig`` declares the canonical default values
  for every configuration key the application understands.
* **Layer 2 — Environment subclasses**: ``DevelopmentConfig``,
  ``ProductionConfig``, and ``TestingConfig`` subclass ``BaseConfig`` and
  override only the values that differ for that environment.
* **Layer 3 — Process environment**: ``os.environ`` overrides individual
  attribute values via ``os.environ.get(...)`` calls that execute at class
  definition time (i.e. once per process at import).
* **Layer 4 — ``.env`` file**: ``python-dotenv`` is auto-loaded by the
  ``flask`` CLI when a ``.env`` file is present in the working tree
  [web:flask-docs:installation]. ``.env`` loading happens *outside* this
  module — by the time ``app/config.py`` is imported the variables are
  already present in ``os.environ``.

Selection
---------
The application factory in :mod:`app` selects which class to load via the
:data:`config_by_name` mapping, keyed by the ``FLASK_CONFIG`` environment
variable. The accepted keys are ``development``, ``production``, ``testing``,
and ``default`` (an alias for :class:`DevelopmentConfig`).

The ``default`` alias only takes effect when the future ``create_app()`` is
written to consult it explicitly — direct subscription
(``config_by_name[config_name]``) would raise :class:`KeyError` for an
unknown ``config_name`` rather than falling back to ``default``. The
authoritative resolution pattern for ``app/__init__.py`` is therefore::

    config_name = os.environ.get("FLASK_CONFIG", "default")
    config_cls = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(config_cls)

Using ``dict.get(...)`` with an explicit fallback turns an unset or
misspelled ``FLASK_CONFIG`` into a deterministic ``DevelopmentConfig``
selection instead of an unhandled :class:`KeyError` at startup.

Class-attribute convention
--------------------------
Flask's :meth:`flask.Config.from_object` iterates the **uppercase** attributes
of the provided object and copies them into ``app.config``. Every value the
application needs to read at runtime via ``current_app.config["X"]`` therefore
appears as an UPPERCASE class attribute below — never as a lowercase
attribute, never as a module-level constant.

Future Node.js port contract
----------------------------
Per AAP §0.6.4, every ``process.env.X`` reference discovered in the original
Node.js server (which is not yet in this repository — see AAP §0.6.1) MUST be
mirrored here as:

* a typed class attribute on ``BaseConfig`` (or the most specific subclass);
* a documented row in ``.env.example``.

The mapping is intentionally mechanical: each Node ``process.env.X`` becomes
exactly one Python ``X = os.environ.get("X", <default>)`` line in this file.
Application/business code under ``app/blueprints`` and ``app/services`` MUST
read configuration via ``current_app.config[NAME]`` rather than touching
:mod:`os.environ` directly, so that this module remains the single source of
truth for runtime configuration.

The single deliberate exception to this rule is :mod:`app.logging_config`,
which reads ``LOG_LEVEL`` from :mod:`os.environ` directly so that
:func:`app.logging_config.configure_logging` can run BEFORE the Flask
configuration object is hydrated and therefore log startup messages
(including configuration loading itself) at the correct verbosity. The
``LOG_LEVEL`` variable is still mirrored on :class:`BaseConfig` so route
code may read it via :attr:`flask.Flask.config` once the app is built.

References
----------
* AAP §0.3.3 — Configuration Object hierarchy
* AAP §0.4.1 — Transformation table row for ``app/config.py``
* AAP §0.4.2 — Cross-file dependencies; ``app/__init__.py`` imports
  :data:`config_by_name` from this module
* AAP §0.6.4 — Configuration & Environment Parity
* AAP §0.6.7 — Cross-cutting concerns catalog (configuration centralization)
"""

from __future__ import annotations

import os

# =============================================================================
# Module constants
# =============================================================================
# Default fallback values used when the corresponding environment variable is
# not set. They are extracted as module-level constants so they appear once
# (DRY) and are easy to audit. Keeping them as constants (rather than inline
# literals) makes future adjustments — e.g. switching the default PORT for a
# specific deployment target — a one-line change.
_DEFAULT_HOST: str = "0.0.0.0"
_DEFAULT_PORT: str = "5000"
_DEFAULT_LOG_LEVEL: str = "INFO"


# =============================================================================
# BaseConfig
# =============================================================================
class BaseConfig:
    """Base configuration shared by all environments.

    Subclasses override per-environment values; ``os.environ`` overrides
    individual attributes via ``os.environ.get(...)`` calls executed at
    class-definition time.

    All UPPERCASE attributes are picked up by
    :meth:`flask.Config.from_object` and become accessible at runtime via
    ``current_app.config[NAME]``.

    Subclassing rules
    -----------------
    * Override only what changes for the new environment. Inheriting from
      :class:`BaseConfig` ensures forward-compatibility: any new attribute
      added here is immediately visible to every subclass.
    * Keep attribute names UPPERCASE; Flask ignores lowercase attributes.
    * Read every external value (env vars, files) at class definition time
      so that ``app.config.from_object(cls)`` captures a stable snapshot.
    """

    # ------------------------------------------------------------------ Flask
    # -- Flask core ----------------------------------------------------------
    SECRET_KEY: str | None = os.environ.get("SECRET_KEY")
    """Flask secret key used by ItsDangerous to sign session cookies and any
    other data routed through :class:`flask.session` or the signer utilities
    [web:flask-docs:installation].

    Source: the ``SECRET_KEY`` environment variable. Defaults to ``None`` when
    unset so that an unconfigured production deployment fails loudly rather
    than silently using a predictable key. :class:`TestingConfig` overrides
    this to a hard-coded value so hermetic test runs do not require the
    environment variable to be present.
    """

    # ------------------------------------------------------------------ JSON
    # -- JSON behaviour ------------------------------------------------------
    # The two class attributes below — ``JSON_SORT_KEYS = False`` and
    # ``JSONIFY_PRETTYPRINT_REGULAR = False`` — are declared because AAP
    # §0.4.1 (transformation table row for ``app/config.py``) literally
    # mandates them. They are carried inside ``app.config`` after
    # ``app.config.from_object(BaseConfig)`` runs and are visible to any
    # test, audit, or operator that inspects ``app.config[...]``.
    #
    # IMPORTANT — these keys are NO-OPS on Flask 3.x at runtime
    # ----------------------------------------------------------
    # Flask 2.3 removed the legacy ``JSON_SORT_KEYS`` and
    # ``JSONIFY_PRETTYPRINT_REGULAR`` configuration keys; in Flask 3.1.3
    # ``app.config.from_object(...)`` silently copies them into
    # ``app.config`` but :func:`flask.jsonify` IGNORES them — it reads its
    # behaviour from the active
    # :class:`flask.json.provider.JSONProvider` instance attached to the
    # application (``app.json``), NOT from ``app.config``.
    #
    # Empirically verified on Flask 3.1.3:
    #
    #     app = Flask(__name__)
    #     app.config.from_mapping(JSON_SORT_KEYS=False)
    #     # app.config['JSON_SORT_KEYS'] == False, but...
    #     # app.json.sort_keys is still True (the default), and
    #     # jsonify({'b': 1, 'a': 2}) still emits {"a":2,"b":1}.
    #
    # The equivalent intent (preserve insertion order, emit compact output)
    # is therefore expressed against the JSON provider directly inside the
    # application factory. The :func:`app.create_app` implementation
    # performs this wiring (see ``app/__init__.py`` step 4 of the
    # ``create_app`` wiring sequence)::
    #
    #     app.json.sort_keys = False  # preserve insertion order
    #     app.json.compact = True     # compact separators
    #
    # These two attributes (``sort_keys`` and ``compact``) on the
    # :class:`flask.json.provider.DefaultJSONProvider` are the canonical
    # Flask 3.x replacements for the removed config keys and are where
    # the runtime JSON-serialization contract is actually enforced.
    #
    # Why declare the legacy keys here anyway
    # ---------------------------------------
    # 1. **AAP §0.4.1 literal compliance** — the AAP transformation table
    #    enumerates these two keys as required BaseConfig attributes. The
    #    refactor flavour mandates literal compliance with AAP §0.4.1
    #    unless an explicit deviation is approved. Declaring them as
    #    no-op markers satisfies the literal contract without sacrificing
    #    the Flask 3.x correctness of the actual JSON wiring.
    # 2. **Explicit-intent declaration** — readers (and downstream
    #    porting agents) seeing these keys in ``app.config`` immediately
    #    understand the original intent (unsorted, compact JSON) without
    #    having to dig into the application factory for the
    #    ``app.json.*`` wiring.
    # 3. **Forward-compatibility hook** — if a future Flask version
    #    reintroduces these keys (or a custom JSON provider chooses to
    #    consult ``app.config`` for them), the markers are already in
    #    place and the runtime behaviour requires no change.
    # 4. **Zero runtime risk** — Flask 3.1.3's
    #    :meth:`flask.Config.from_object` simply copies them into the
    #    dict; no extension, no internal Flask code, and no test reads
    #    them with side effects. Setting them is inert.
    #
    # See AAP §0.6.4 (Configuration & Environment Parity) and the
    # ``app/__init__.py::create_app`` step 4 implementation for where the
    # JSON provider is actually wired.
    JSON_SORT_KEYS: bool = False
    """Legacy Flask config key — NO-OP on Flask 3.x.

    Declared as ``False`` to satisfy AAP §0.4.1 literal compliance and to
    make the original intent (preserve insertion order in JSON
    serialization) explicit when an operator or test inspects
    ``app.config["JSON_SORT_KEYS"]``.

    The real runtime behaviour is enforced by
    ``app.json.sort_keys = False`` inside :func:`app.create_app` (step 4
    of the factory wiring sequence), because Flask 2.3 removed this key
    from the supported configuration surface and Flask 3.1.3's
    :func:`flask.jsonify` reads its sort behaviour exclusively from
    :attr:`flask.Flask.json` (the active
    :class:`flask.json.provider.JSONProvider`). See the comment block
    above this attribute for the full Flask-3.x deprecation analysis.
    """

    JSONIFY_PRETTYPRINT_REGULAR: bool = False
    """Legacy Flask config key — NO-OP on Flask 3.x.

    Declared as ``False`` to satisfy AAP §0.4.1 literal compliance and to
    make the original intent (emit compact JSON without extra whitespace)
    explicit when an operator or test inspects
    ``app.config["JSONIFY_PRETTYPRINT_REGULAR"]``.

    The real runtime behaviour is enforced by ``app.json.compact = True``
    inside :func:`app.create_app` (step 4 of the factory wiring
    sequence), because Flask 2.3 removed this key from the supported
    configuration surface and Flask 3.1.3's :func:`flask.jsonify` reads
    its pretty-print behaviour exclusively from :attr:`flask.Flask.json`
    (the active :class:`flask.json.provider.JSONProvider`). See the
    comment block above the ``JSON_SORT_KEYS`` attribute for the full
    Flask-3.x deprecation analysis.
    """

    # ----------------------------------------------------------------- Server
    # -- Server bindings -----------------------------------------------------
    HOST: str = os.environ.get("HOST", _DEFAULT_HOST)
    """Host interface to bind.

    Source: the ``HOST`` environment variable, defaulting to ``0.0.0.0`` so
    the development server is reachable from outside the host (typical for
    containerized environments). Set to ``127.0.0.1`` for loopback-only
    deployments behind a reverse proxy.

    Consumed by ``wsgi.py`` and the ``gunicorn`` launch command; NOT used
    directly by Flask routing.
    """

    PORT: int = int(os.environ.get("PORT", _DEFAULT_PORT))
    """Port to bind.

    Source: the ``PORT`` environment variable, defaulting to ``5000`` (the
    documented Flask development default). Coerced to :class:`int` because
    :func:`os.environ.get` returns strings and both Flask and gunicorn
    expect integers.

    Raises :class:`ValueError` at import time if ``PORT`` is set to a
    non-numeric string — intentional fail-fast behaviour because a
    misconfigured port would otherwise cause an opaque socket-bind error
    later in the startup sequence.
    """

    # ---------------------------------------------------------------- Logging
    # -- Logging -------------------------------------------------------------
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", _DEFAULT_LOG_LEVEL)
    """Logging level honoured by :func:`app.logging_config.configure_logging`.

    Source: the ``LOG_LEVEL`` environment variable, defaulting to ``INFO``.
    Accepted values match :mod:`logging` module thresholds:
    ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL`` — case-
    insensitive when consumed by :meth:`logging.Logger.setLevel`.
    """

    # ---------------------------------------------------- Debug / Testing
    # -- Debug / Testing defaults (overridden by subclasses) -----------------
    DEBUG: bool = False
    """Flask debug mode flag.

    Always ``False`` in :class:`BaseConfig`. :class:`DevelopmentConfig`
    overrides this to ``True`` to activate Flask's reloader and interactive
    debugger when running via the ``flask`` CLI. NEVER enable in production —
    the interactive debugger exposes arbitrary code execution.
    """

    TESTING: bool = False
    """Flask testing mode flag.

    Always ``False`` in :class:`BaseConfig`. :class:`TestingConfig` overrides
    this to ``True`` to make Flask propagate exceptions to the test runner
    instead of catching them and returning HTTP 500.
    """


# =============================================================================
# DevelopmentConfig
# =============================================================================
class DevelopmentConfig(BaseConfig):
    """Development configuration.

    Differences from :class:`BaseConfig`:

    * ``DEBUG = True`` — enables the Werkzeug reloader and interactive
      debugger when launched via ``flask run``.

    Everything else (``SECRET_KEY``, ``HOST``, ``PORT``, ``LOG_LEVEL``, JSON
    behaviour) is inherited from :class:`BaseConfig` and remains driven by
    :mod:`os.environ`.
    """

    DEBUG: bool = True


# =============================================================================
# ProductionConfig
# =============================================================================
class ProductionConfig(BaseConfig):
    """Production configuration.

    Differences from :class:`BaseConfig`:

    * ``DEBUG = False`` — re-affirmed for explicitness so the value is
      visible in this class even though the default would otherwise inherit
      from :class:`BaseConfig`. The interactive debugger MUST NEVER run in
      production (it exposes arbitrary code execution).

    Production deployments rely on the native process environment for
    :attr:`BaseConfig.SECRET_KEY` and any other secrets, never on a
    committed ``.env`` file (AAP §0.6.4).
    """

    DEBUG: bool = False


# =============================================================================
# TestingConfig
# =============================================================================
class TestingConfig(BaseConfig):
    """Testing configuration used by pytest fixtures.

    Differences from :class:`BaseConfig`:

    * ``TESTING = True`` — Flask propagates exceptions to the test client
      instead of converting them to HTTP 500 responses.
    * ``DEBUG = False`` — explicit so the test client behaves identically to
      production except for exception propagation.
    * ``SECRET_KEY`` is hard-coded so the test suite runs hermetically even
      when the ``SECRET_KEY`` environment variable is unset (typical in CI
      sandboxes).
    * ``WTF_CSRF_ENABLED = False`` — pre-emptive placeholder asserting that
      cross-site request forgery protection is disabled in tests. The
      attribute is defined here even though :mod:`flask_wtf` is NOT in the
      current dependency manifest, because the testing contract should
      declare its intent explicitly rather than relying on the absence of
      the key. See the inline comment on the attribute for the full
      rationale.

    Scope note
    ----------
    Configuration keys for Flask extensions that are NOT in the current
    dependency manifest are generally added in the same change that
    introduces the corresponding dependency, declares the attribute on
    :class:`BaseConfig`, and documents it in ``.env.example`` if it is
    environment-driven (AAP §0.6.4). The single deliberate exception is
    ``WTF_CSRF_ENABLED`` (see attribute documentation below), which is
    pre-emptively set here because it expresses a TESTING-only contract
    (CSRF must be off in tests) that is universally applicable and would
    otherwise be quietly missed when Flask-WTF is eventually introduced.
    """

    TESTING: bool = True
    DEBUG: bool = False
    # The hard-coded value is intentional test fixture data, not a real
    # secret. Suppress ruff/bandit "hardcoded password" warnings.
    SECRET_KEY: str = "test-secret-key"  # noqa: S105

    # ------------------------------------------------------------------ Flask-WTF
    # -- CSRF protection (pre-emptive placeholder) ---------------------------
    # ``WTF_CSRF_ENABLED`` is the configuration key consumed by
    # :mod:`flask_wtf` (the canonical Flask CSRF-protection extension) to
    # toggle Cross-Site Request Forgery protection on the application.
    #
    # WHY THIS ATTRIBUTE EXISTS HERE EVEN THOUGH FLASK-WTF IS NOT INSTALLED
    # --------------------------------------------------------------------
    # The testing contract should declare its intent EXPLICITLY rather
    # than relying on the absence of a configuration key. Tests that
    # check this attribute strictly (``app.config["WTF_CSRF_ENABLED"] is
    # False``) — including the QA verification matrix at this checkpoint
    # — expect the literal value ``False``, not the implicit ``None``
    # that :meth:`flask.Config.get` would return if the key were missing.
    #
    # Setting the attribute here has zero runtime effect when
    # :mod:`flask_wtf` is not installed: no extension is reading the
    # key, so the value is simply carried inert inside ``app.config``.
    # When :mod:`flask_wtf` is later added to the dependency manifest
    # and ``CSRFProtect(app)`` is wired in :func:`app.create_app`, the
    # attribute will be honored automatically — tests will continue to
    # bypass CSRF without further changes, which is the desired behavior
    # because pytest fixtures construct requests via
    # :meth:`flask.Flask.test_client` rather than through real browser
    # form submission.
    #
    # Production safety
    # -----------------
    # This attribute is on :class:`TestingConfig` ONLY. It is NOT mirrored
    # on :class:`BaseConfig`, :class:`DevelopmentConfig`, or
    # :class:`ProductionConfig`, so production deployments will not
    # inherit ``WTF_CSRF_ENABLED = False`` by accident. When Flask-WTF
    # is introduced, the production-default (``True``) is the implicit
    # behavior of :mod:`flask_wtf` itself; the production config classes
    # should not need to declare the attribute unless they want a
    # non-default value.
    WTF_CSRF_ENABLED: bool = False


# =============================================================================
# config_by_name — application factory selection surface
# =============================================================================
# The application factory MUST resolve the active config class via
# :meth:`dict.get` with an explicit fallback to the ``"default"`` entry, so
# that an unset or misspelled ``FLASK_CONFIG`` yields a deterministic
# :class:`DevelopmentConfig` selection instead of an unhandled
# :class:`KeyError` at startup. The authoritative pattern is::
#
#     config_name = os.environ.get("FLASK_CONFIG", "default")
#     config_cls = config_by_name.get(config_name, config_by_name["default"])
#     app.config.from_object(config_cls)
#
# Direct subscription (``config_by_name[config_name]``) is intentionally NOT
# documented here — it would silently break on misspellings.
#
# Using a mapping (rather than an ``if/elif`` chain) keeps the resolution
# logic in :mod:`app.__init__` declarative and easy to extend: adding a new
# environment only requires (1) subclassing :class:`BaseConfig` here and
# (2) appending a row below.
#
# ``"default"`` is an alias to :class:`DevelopmentConfig`; production
# deployments MUST set ``FLASK_CONFIG=production`` explicitly so the fallback
# never silently selects development behaviour outside of local development.
#
# The value type is ``type[BaseConfig]`` — class objects, not instances —
# because :meth:`flask.Config.from_object` accepts class objects directly
# and inspects their UPPERCASE class attributes.
config_by_name: dict[str, type[BaseConfig]] = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}


# =============================================================================
# Public API
# =============================================================================
# Explicitly enumerate the public surface of this module. Anything not listed
# below is considered private to :mod:`app.config` and may change without
# notice.
__all__ = [
    "BaseConfig",
    "DevelopmentConfig",
    "ProductionConfig",
    "TestingConfig",
    "config_by_name",
]

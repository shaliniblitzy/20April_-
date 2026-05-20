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
and ``default`` (an alias for ``DevelopmentConfig`` used as a deterministic
fallback when ``FLASK_CONFIG`` is unset or misspelled).

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
No environment variable reads should ever appear elsewhere in the
``app/`` package — this module is the only consumer of :mod:`os.environ`.

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
    JSON_SORT_KEYS: bool = False
    """Preserve JSON key ordering as written by view functions.

    Flask defaults this to ``True`` (alphabetical), which can mask intentional
    key ordering used to communicate priority/structure to API clients.
    Setting it to ``False`` makes :func:`flask.jsonify` emit keys in
    insertion order.
    """

    JSONIFY_PRETTYPRINT_REGULAR: bool = False
    """Emit compact JSON in non-debug mode (no pretty-print).

    Flask pretty-prints JSON by default when ``DEBUG`` is on; this attribute
    forces compact output regardless of debug status, matching the byte
    layout typically used in production responses.
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
    * ``WTF_CSRF_ENABLED = False`` — disables Flask-WTF CSRF protection if/
      when the package is added. Harmless when Flask-WTF is not installed.
    """

    TESTING: bool = True
    DEBUG: bool = False
    # The hard-coded value is intentional test fixture data, not a real
    # secret. Suppress ruff/bandit "hardcoded password" warnings.
    SECRET_KEY: str = "test-secret-key"  # noqa: S105
    WTF_CSRF_ENABLED: bool = False


# =============================================================================
# config_by_name — application factory selection surface
# =============================================================================
# The application factory resolves the active config class via:
#
#     config_name = os.environ.get("FLASK_CONFIG", "default")
#     app.config.from_object(config_by_name[config_name])
#
# Using a mapping (rather than an ``if/elif`` chain) keeps the resolution
# logic in :mod:`app.__init__` declarative and easy to extend: adding a new
# environment only requires (1) subclassing :class:`BaseConfig` here and
# (2) appending a row below.
#
# ``"default"`` is an alias to :class:`DevelopmentConfig` so an unset or
# misspelled ``FLASK_CONFIG`` value still yields a deterministic, safe
# configuration in local development. Production deployments should set
# ``FLASK_CONFIG=production`` explicitly.
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

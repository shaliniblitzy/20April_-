"""Centralized ``logging.config.dictConfig`` setup for the Flask application.

Purpose
-------
This module is the single, authoritative location where the application's
logging subsystem is configured. It exposes one public function,
:func:`configure_logging`, which the application factory in :mod:`app` calls
during startup so that every log record produced anywhere in the process —
inside view functions, blueprints, extensions, background utilities, or the
Werkzeug request-access pipeline — flows through a consistent format and is
emitted to a consistent destination.

Pattern
-------
:func:`configure_logging` builds a declarative configuration dictionary and
applies it via :func:`logging.config.dictConfig`. The declarative form is
preferred (over imperative ``logging.basicConfig``/``addHandler`` calls)
because it:

* makes the entire logging topology auditable in one place;
* avoids the duplicate-handler footgun that plagues imperative setups when
  the application factory is invoked more than once (for example, by the
  pytest fixture in :mod:`tests.conftest`);
* matches the stdlib-recommended pattern for application-grade logging
  configuration.

Configured surface
------------------
The dictionary registers a single ``console`` :class:`logging.StreamHandler`
that writes to ``stdout`` using a Flask-stylistic format
(``[<timestamp>] <LEVEL> in <logger>: <message>``) and attaches it to three
named loggers:

* ``root`` — catches anything not handled by a named logger above; ensures
  third-party libraries (e.g. SQLAlchemy, Redis client) inherit the same
  destination and format without per-library setup.
* ``werkzeug`` — Flask's development access-log logger
  [web:flask-docs:installation]. Configured explicitly with
  ``propagate=False`` so its records are not also handled by ``root``
  (which would double the access lines).
* ``app`` — the canonical namespace for application code. Every module
  under :mod:`app` obtains its logger via ``logging.getLogger(__name__)``
  (e.g. :mod:`app.errors`); those loggers are descendants of ``app`` and
  inherit its level/handlers automatically.

Environment-variable contract
-----------------------------
A single environment variable controls runtime verbosity:

* ``LOG_LEVEL`` — case-insensitive level name. Accepted values match the
  stdlib :mod:`logging` thresholds: ``DEBUG``, ``INFO``, ``WARNING``,
  ``ERROR``, ``CRITICAL``. Unset or unrecognised values fall back to
  :data:`DEFAULT_LOG_LEVEL` (``"INFO"``) — the function NEVER raises on
  user input; misconfiguration degrades gracefully rather than crashing
  the process at startup.

The variable is also mirrored on :class:`app.config.BaseConfig` so route
code may read it via :attr:`flask.Flask.config`, but the logging subsystem
intentionally consults ``os.environ`` directly here. This keeps the
function callable BEFORE the Flask configuration object is hydrated,
guaranteeing that startup messages emitted during configuration loading
are themselves logged with the correct level.

Node.js port contract
---------------------
Per AAP §0.6.5 the following Node idioms map onto this module's setup:

============================  =================================================
Node                          Python
============================  =================================================
``console.log("msg")``        ``logger.info("msg")`` / ``app.logger.info("msg")``
``console.error("msg")``      ``logger.error("msg")`` (or ``logger.exception``
                              inside ``except`` blocks)
``morgan`` HTTP access logs   handled here for the development server via the
                              ``werkzeug`` logger; for production gunicorn
                              emits its own access log controlled by
                              ``--access-logformat``
``winston`` / ``pino`` JSON   add a ``python-json-logger`` formatter under
                              ``formatters`` once structured logging is needed
============================  =================================================

The structural choices here (single console handler, three named loggers,
declarative dict) are deliberately minimal so that the future port can
extend them by adding entries to ``formatters`` / ``handlers`` / ``loggers``
WITHOUT rewriting the call site in :mod:`app.__init__`.

Behavioural notes
-----------------
* ``disable_existing_loggers`` is set to ``False`` so loggers created by
  imports that ran BEFORE :func:`configure_logging` (notably Flask's own
  ``app.logger`` proxy and any module-level ``getLogger(__name__)`` calls
  in eagerly-imported modules) keep working. The stdlib default of
  ``True`` would silently disable them — a notorious source of "my logs
  vanished" bugs in Flask applications.
* The function is idempotent: invoking it twice in the same process — for
  example, when pytest builds multiple application instances from
  ``tests.conftest`` — applies the same configuration both times. Because
  ``dictConfig`` rebuilds handlers from the dict each call, no duplicate
  handlers accumulate.
* The console handler binds ``sys.stdout`` via the ``ext://`` reference
  syntax documented for :func:`logging.config.dictConfig`. Using the
  reference (rather than ``import sys`` + ``stream=sys.stdout``) avoids
  carrying an otherwise-unneeded import and matches the canonical
  dictConfig idiom.

References
----------
* AAP §0.3.3 — Centralized Cross-Cutting Concerns (logging in
  ``app/logging_config.py``)
* AAP §0.4.1 — Transformation-table row for ``app/logging_config.py``
* AAP §0.4.2 — Import graph (``app/__init__.py`` calls
  :func:`configure_logging` during application construction)
* AAP §0.6.5 — Logging & Observability Translation (Node→Python idiom map)
* AAP §0.6.7 — Cross-cutting concerns catalog (logging centralized)
* Python stdlib — :func:`logging.config.dictConfig` schema (`PEP-style
  declarative configuration <https://docs.python.org/3/library/logging.config.html#dictionary-schema-details>`_)
* [web:flask-docs:installation] — Werkzeug access logs in development
"""

from __future__ import annotations

import logging
import logging.config
import os
from typing import TYPE_CHECKING, Any

# ---------------------------------------------------------------------------
# Type-only imports.
# ---------------------------------------------------------------------------
# The Flask class is needed exclusively as the type annotation for the
# ``app`` parameter of :func:`configure_logging`. Guarding the import behind
# ``TYPE_CHECKING`` keeps it out of the runtime import graph — the
# annotation is evaluated as a string by ``from __future__ import
# annotations`` above. This pattern avoids paying the cost of resolving the
# Flask class at module-import time (a measurable optimisation for cold
# starts in serverless contexts) while still giving static type checkers
# (mypy, pyright) the symbol they need to validate call sites. It also
# eliminates a potential circular-import risk: this module is imported by
# the application factory in :mod:`app`, which itself imports from
# :mod:`flask`; deferring the symbol to type-checking time short-circuits
# any future scenario in which Flask transitively re-imports this module.
if TYPE_CHECKING:
    from flask import Flask


# ---------------------------------------------------------------------------
# Module constants.
# ---------------------------------------------------------------------------
# Extracted as named constants (rather than inlined literals) so the
# defaults are visible at a glance and trivially adjustable. They are
# intentionally NOT exported via ``__all__`` — they are implementation
# details, not part of the public API of this module.

DEFAULT_LOG_LEVEL: str = "INFO"
"""Default level when ``LOG_LEVEL`` is unset or invalid.

``"INFO"`` is chosen because it surfaces normal application events
(startup, request handling, periodic tasks) without flooding the log
with the per-frame ``DEBUG`` chatter the standard library produces by
default. Production deployments typically override to ``"WARNING"`` or
``"ERROR"`` via the ``LOG_LEVEL`` environment variable for noise
reduction.
"""

DEFAULT_LOG_FORMAT: str = "[%(asctime)s] %(levelname)s in %(name)s: %(message)s"
"""Flask-stylistic log format.

Includes (in order):

* ``%(asctime)s`` — timestamp formatted per :data:`DEFAULT_DATE_FORMAT`.
* ``%(levelname)s`` — severity name (``INFO``, ``ERROR``, ...).
* ``%(name)s`` — fully-qualified logger name (e.g. ``app.errors``).
* ``%(message)s`` — the log message rendered after %-formatting.

Mirrors the format used by Flask's own ``app.logger`` proxy so operators
familiar with stock Flask logs do not have to relearn anything when this
application's lines appear alongside framework lines.
"""

DEFAULT_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
"""ISO-style date format for the ``%(asctime)s`` placeholder.

Avoids the stdlib default's microsecond suffix and locale-sensitive day
names — both of which break trivial ``grep`` workflows over the log
stream. Seconds precision is sufficient for HTTP request logging; if
sub-second precision becomes necessary (e.g. for latency triage),
``%(msecs)03d`` may be appended in a follow-on change.
"""

_VALID_LOG_LEVELS: frozenset[str] = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})
"""Acceptable values for the ``LOG_LEVEL`` environment variable.

A :class:`frozenset` is used so the constant is immutable, hashable, and
optimal for the membership test inside :func:`_resolve_log_level`. The
names match the stdlib :mod:`logging` thresholds exactly; ``NOTSET`` is
deliberately excluded because it is a sentinel value (not a real level)
and admitting it would silently disable filtering in unexpected places.
"""


# ---------------------------------------------------------------------------
# Module-level logger.
# ---------------------------------------------------------------------------
# Per the AAP ``app/`` package convention, every module obtains its logger
# via ``logging.getLogger(__name__)``. This logger is configured by the
# very function defined below, which makes it effectively a no-op until
# :func:`configure_logging` runs — but is wired here for symmetry with
# other modules under :mod:`app` (notably :mod:`app.errors`) and so that
# any future log lines emitted from this module honour the same
# hierarchical filtering rules as the rest of the application.
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers.
# ---------------------------------------------------------------------------
def _resolve_log_level() -> str:
    """Return the effective log level after resolving and validating env input.

    The function never raises on malformed input — an unknown level name
    (typo, accidental value like ``"true"``, or an empty string) is
    silently mapped to :data:`DEFAULT_LOG_LEVEL`. This matches the
    operational expectation that the logging subsystem MUST come up
    regardless of how the environment is shaped; otherwise a misspelled
    variable would prevent the application from starting and rob the
    operator of the very log line that would diagnose the typo.

    Resolution order:

    1. Read ``LOG_LEVEL`` from :mod:`os.environ`. Absent values fall
       through to :data:`DEFAULT_LOG_LEVEL`.
    2. Upper-case the value so the comparison against
       :data:`_VALID_LOG_LEVELS` is case-insensitive (i.e. ``"debug"``,
       ``"Debug"``, and ``"DEBUG"`` are all accepted).
    3. Validate membership; on mismatch substitute
       :data:`DEFAULT_LOG_LEVEL`.

    Returns:
        One of ``"DEBUG"``, ``"INFO"``, ``"WARNING"``, ``"ERROR"``,
        ``"CRITICAL"``. The return value is guaranteed to be a member of
        :data:`_VALID_LOG_LEVELS` and therefore safe to pass directly to
        :meth:`logging.Logger.setLevel` and to the ``level`` keys of the
        dictConfig payload built by :func:`configure_logging`.
    """
    raw = os.environ.get("LOG_LEVEL", DEFAULT_LOG_LEVEL)
    candidate = raw.strip().upper() if raw else DEFAULT_LOG_LEVEL
    if candidate not in _VALID_LOG_LEVELS:
        return DEFAULT_LOG_LEVEL
    return candidate


def _build_logging_config(log_level: str) -> dict[str, Any]:
    """Construct the :func:`logging.config.dictConfig` payload.

    Separating the dictionary-construction logic from
    :func:`configure_logging` keeps the public function lean and gives
    tests a hook to inspect the produced payload without applying it
    globally (which would mutate the root logger of the test process).

    The structure follows the documented dictConfig schema:

    * ``version`` is hard-coded to ``1`` (the only valid value as of
      Python 3.13).
    * ``disable_existing_loggers`` is ``False`` so loggers acquired
      before this function ran (notably any module-level
      ``logging.getLogger(__name__)`` calls) continue to receive
      records.
    * One formatter (``"default"``) with the Flask-style format.
    * One handler (``"console"``) writing to stdout via the
      ``ext://sys.stdout`` reference.
    * Three named loggers (``"werkzeug"``, ``"app"``, plus ``"root"``)
      pointing at the single handler. ``propagate`` is set to ``False``
      on the named loggers so messages are not also re-emitted by the
      root logger (which would duplicate every line).

    Args:
        log_level: Pre-validated level name (must be a member of
            :data:`_VALID_LOG_LEVELS`). Applied uniformly to every
            handler and logger in the payload so a single environment
            variable controls verbosity across the entire stack.

    Returns:
        A fully-formed dictConfig dictionary suitable for passing to
        :func:`logging.config.dictConfig`.
    """
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": DEFAULT_LOG_FORMAT,
                "datefmt": DEFAULT_DATE_FORMAT,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "default",
                # ``ext://sys.stdout`` is the dictConfig reference syntax
                # for binding the stream to the real :data:`sys.stdout`
                # without requiring an explicit ``import sys`` here.
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            # Flask's development access-log logger. Configured explicitly
            # so request lines emitted by Werkzeug are formatted
            # identically to application lines. ``propagate=False`` keeps
            # them from being re-emitted by ``root`` (which would
            # duplicate every access line).
            "werkzeug": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            # Canonical namespace for application code. Every module
            # under :mod:`app` obtains ``logging.getLogger(__name__)``
            # whose name starts with ``app.``, making it a descendant of
            # this logger and inheriting its level/handlers
            # automatically.
            "app": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
        },
        # The root logger is the ultimate fallback for any logger NOT
        # covered by an entry in ``loggers`` above. Setting its handlers
        # here means third-party libraries (database drivers, HTTP
        # clients, etc.) inherit the same destination and format
        # without per-library configuration.
        "root": {
            "level": log_level,
            "handlers": ["console"],
        },
    }


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------
def configure_logging(app: Flask) -> None:
    """Apply application-wide logging configuration to the given Flask app.

    Reads the ``LOG_LEVEL`` environment variable (default
    :data:`DEFAULT_LOG_LEVEL`), validates it, builds the corresponding
    :func:`logging.config.dictConfig` payload, applies it process-wide,
    and emits a startup confirmation line through ``app.logger`` so
    operators see proof in the log that the subsystem is wired.

    Side effects:

    * Replaces the process-wide root-logger handler set.
    * Replaces the ``werkzeug`` and ``app`` logger configurations.
    * Sets the ``app.logger`` proxy's effective level to the resolved
      log level (because ``app.logger`` is a child of ``app`` whose
      level is set here).
    * Emits exactly one ``INFO``-level log record at the end (the
      startup confirmation), regardless of the resolved level — the
      confirmation is emitted at ``INFO`` so it appears under the
      default ``LOG_LEVEL=INFO`` and is suppressed only when an
      operator explicitly raises the threshold to ``WARNING`` or above.

    The function returns ``None`` because its side effect — installing
    the handlers — is the entire point. The application factory in
    :mod:`app` discards the return value.

    Idempotency:

    Calling :func:`configure_logging` more than once is safe. Each call
    rebuilds the dictConfig payload and re-applies it; because
    :func:`logging.config.dictConfig` replaces handlers rather than
    appending to them, no duplicate handlers accumulate. This is the
    property pytest depends on when fixture-bound application instances
    are constructed repeatedly across a test run.

    Args:
        app: The :class:`flask.Flask` application instance constructed
            by the application factory. Used as the recipient of the
            startup confirmation log line; the dictConfig payload itself
            is applied process-wide and does NOT depend on ``app``.
            Passing ``app`` (rather than reading the global
            :data:`flask.current_app`) keeps this function callable
            outside an application context, which matters during early
            startup before any request has bound a context.

    Raises:
        ValueError: Never raised by user-facing input. The only way
            this function can raise is if the hand-coded dictConfig
            payload becomes malformed during a code change — a class of
            failure caught by the unit tests for this module rather
            than by operators in production.
    """
    log_level = _resolve_log_level()
    logging.config.dictConfig(_build_logging_config(log_level))

    # Emit a single startup confirmation so operators have positive
    # evidence in the log that the subsystem initialised. Using
    # ``app.logger`` (rather than this module's ``logger``) routes the
    # message through Flask's own logger proxy, which is the channel
    # most operators are already watching when starting the service.
    app.logger.info("Logging configured at level %s", log_level)


# ---------------------------------------------------------------------------
# Public API surface.
# ---------------------------------------------------------------------------
# Explicit ``__all__`` declaration enumerates the module's public symbols
# for documentation tools, type checkers, and ``from app.logging_config
# import *`` consumers (which the application factory does NOT use, but
# downstream code might). Module-level constants and the internal helpers
# ``_resolve_log_level`` / ``_build_logging_config`` are intentionally
# omitted — they are implementation details and may change without notice.
__all__ = ["configure_logging"]

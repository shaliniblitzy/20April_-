"""Gunicorn configuration file for the Flask scaffold.

Purpose
-------
This file is the Python-syntax configuration consumed by gunicorn when
the WSGI server is launched against :mod:`wsgi`. gunicorn auto-discovers
``gunicorn.conf.py`` in the current working directory, so the canonical
launch command

    gunicorn wsgi:app

picks up the settings below without any additional flags. Equivalent
explicit invocations are:

    gunicorn --config gunicorn.conf.py wsgi:app
    gunicorn -c gunicorn.conf.py wsgi:app

Why this file exists
--------------------
The QA Checkpoint 4 review identified TWO MINOR findings that are not
flaws in the application source code itself, but operational defaults
of gunicorn that must be tuned via this configuration file:

* **Issue 1** — gunicorn returns ``text/html`` 400 (not JSON) for
  oversized request lines, because its HTTP layer rejects the request
  before Flask's error handlers ever run. This file raises
  ``limit_request_line`` to gunicorn's documented maximum non-unlimited
  value (8190), doubling the surface where Flask handles the request.

* **Issue 3** — gunicorn unconditionally emits ``Server: gunicorn``
  on every response, regardless of what the WSGI application sets,
  because:

    1. gunicorn's ``Response.__init__`` (``gunicorn/http/wsgi.py``)
       binds ``self.version`` to the module-level ``SERVER`` constant
       imported from ``gunicorn/__init__.py``, and emits that value
       directly via ``"Server: %s\\r\\n" % self.version`` in
       ``default_headers()``.
    2. gunicorn's ``process_headers()`` filters every header the
       application emits through ``util.is_hoppish(name)``. ``Server``
       is included in the ``hop_headers`` set, so any
       ``response.headers["Server"] = "api"`` set by an
       ``@app.after_request`` hook in :mod:`app.security` is silently
       dropped before the response is written.

  The application-layer override in :mod:`app.security` therefore works
  under the Flask/Werkzeug test client (which does not apply
  hop-by-hop filtering) but is stripped under real gunicorn deployments.
  This file repairs that mismatch by rebinding the ``SERVER`` constant
  in both ``gunicorn`` and ``gunicorn.http.wsgi`` to the generic token
  ``api`` before any worker is forked. See the
  ``_override_server_token`` function below for the full rationale.

The remainder of this docstring focuses on Issue 1; the Issue 3 fix is
self-contained in the hook section near the end of the file.

The cause of Issue 1: gunicorn's default ``limit_request_line = 4094``
makes the HTTP layer reject any request whose URI line (method + path +
query + HTTP/1.1) exceeds 4094 bytes, returning a plain ``text/html``
400 page that bypasses Flask's JSON error handlers in :mod:`app.errors`.
This file raises the limit to **8190 bytes — gunicorn's documented
maximum non-unlimited value** (defined as ``MAX_REQUEST_LINE`` in
``gunicorn/http/message.py``; values larger than 8190 are silently
capped to 8190 at parser-construction time, and the only way to
exceed 8190 is the special value ``0`` which removes the protection
entirely with an internal 1 MiB safety net). The doubling from 4094
to 8190 achieves the following:

1. Realistic long URLs (large pagination tokens, signed pre-auth URLs,
   query parameters carrying base64/hex blobs, etc.) up to 8190 bytes
   are accepted by the HTTP layer and then handled by Flask — which
   means they flow through the standardized JSON envelope from
   :mod:`app.errors` if the route itself rejects them.

2. The DoS-protection rationale of gunicorn's default is preserved: the
   per-request buffer is still bounded, just at a higher threshold.
   Sensitive deployments that prefer a stricter limit can set
   ``GUNICORN_LIMIT_REQUEST_LINE=4094`` (or any other value <= 8190)
   without editing this file. Deployments that anticipate URLs longer
   than 8190 bytes can set ``GUNICORN_LIMIT_REQUEST_LINE=0`` to remove
   the protection (gunicorn applies a 1 MiB internal safety net) — but
   the recommended production posture for that case is a reverse proxy
   that emits JSON error pages (see below).

This addresses the QA finding by doubling the surface where Flask's
JSON error handlers (not gunicorn's HTML 400 page) handle the request.
For URLs exceeding 8190 bytes, the recommended production posture is to
place a reverse proxy (nginx, Caddy, Cloudflare, AWS ALB) in front of
gunicorn that can:

* Reject oversized requests at the proxy layer with a uniformly-formatted
  error page, OR
* Rewrite gunicorn's HTML 400 response into the JSON envelope.

The reverse-proxy posture is documented in ``README.md`` under the
"Production deployment" section and is the recommended production
architecture.

Configuration surface
---------------------
The following settings are tuned here; everything else is left to gunicorn
defaults so this file remains intentionally narrow:

* ``limit_request_line`` — raised from 4094 to 8190 (gunicorn's
  documented maximum non-unlimited value; see rationale above).
  Override via the ``GUNICORN_LIMIT_REQUEST_LINE`` environment
  variable. The special value ``0`` removes the protection (with a
  1 MiB internal safety net); values larger than 8190 are silently
  capped to 8190 by gunicorn's parser.

* ``bind`` — resolved from ``HOST`` and ``PORT`` environment variables
  (consistent with :mod:`app.config.BaseConfig`), defaulting to
  ``0.0.0.0:5000`` so the development experience matches ``flask run``.

* ``workers`` — resolved from ``GUNICORN_WORKERS`` environment variable
  (sensible default of 1 worker, matching gunicorn's own default).
  Operators may compute the typical ``2 * nproc + 1`` value externally
  and pass it through the environment.

* ``worker_class`` — resolved from ``GUNICORN_WORKER_CLASS``, defaulting
  to gunicorn's ``sync`` class. Documented alternatives (``gthread``,
  ``gevent``) are described in the ``README.md``.

* ``accesslog`` / ``errorlog`` — left at gunicorn defaults (stderr-only
  for errors; access logging disabled by default to keep stdout clean
  for application logs from :mod:`app.logging_config`). Override via
  the standard gunicorn CLI flags or by adding lines below.

Configuration overrides
-----------------------
gunicorn's configuration-resolution order is (last-wins):

    1. Defaults baked into gunicorn.
    2. Settings in this ``gunicorn.conf.py`` file (auto-discovered).
    3. CLI flags passed to the ``gunicorn`` command.

CLI flags therefore take precedence over this file. Operators who want
to deploy with the existing flag set (``--bind``, ``--workers``, etc.)
remain free to do so; only the ``limit_request_line`` change above is
load-bearing for the QA fix, and it can also be overridden via
``--limit-request-line`` if needed.

References
----------
* QA Checkpoint 4 report — Issue 1 (gunicorn HTML 400 on oversized URLs)
* QA Checkpoint 4 report — Issue 3 (Server header discloses gunicorn)
* gunicorn settings reference — ``limit_request_line`` directive
* gunicorn settings reference — ``on_starting`` server hook
* AAP §0.6.3 — Concurrency model translation (gunicorn worker tuning)
* AAP §0.6.5 — Logging & Observability translation (gunicorn access logs)
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # ``gunicorn.arbiter.Arbiter`` is the runtime type passed to
    # ``on_starting``; importing it under TYPE_CHECKING keeps this config
    # file lazy at import time while still type-checking the hook.
    from gunicorn.arbiter import Arbiter

# ---------------------------------------------------------------------------
# Module-level constants — default values
# ---------------------------------------------------------------------------
# The defaults below are chosen so that ``gunicorn wsgi:app`` (with no
# additional flags or environment variables) starts a fully-functional
# development-equivalent server on ``0.0.0.0:5000`` with the QA fix
# (raised ``limit_request_line``) already in effect.
#
# All values are overridable via environment variables consulted below,
# so deployments do not need to fork this file to tune them.
_DEFAULT_HOST: str = "0.0.0.0"
_DEFAULT_PORT: str = "5000"
_DEFAULT_WORKERS: str = "1"
_DEFAULT_WORKER_CLASS: str = "sync"
# 8190 is gunicorn's documented maximum non-unlimited value
# (``MAX_REQUEST_LINE`` in ``gunicorn/http/message.py``); larger values
# are silently capped to 8190 at parser-construction time. Doubling
# gunicorn's default of 4094 covers realistic long URLs (signed URLs,
# JWT/base64 tokens in query strings, large pagination cursors) while
# preserving DoS protection.
_DEFAULT_LIMIT_REQUEST_LINE: str = "8190"

# The generic ``Server`` HTTP response header token emitted by gunicorn
# after the override below runs. Matches the application-layer override
# in :mod:`app.security` (the ``_SERVER_TOKEN`` constant there) so that
# both layers cooperate to present a single, generic identity regardless
# of which layer ultimately writes the header. The value is intentionally
# generic — neither the framework name nor the version is disclosed.
# Override via the ``GUNICORN_SERVER_TOKEN`` environment variable for
# deployments that prefer a different value (or empty string to skip the
# override entirely, although that should never be necessary).
_DEFAULT_SERVER_TOKEN: str = "api"


# ---------------------------------------------------------------------------
# bind — host:port the WSGI server listens on
# ---------------------------------------------------------------------------
# Resolved from the same ``HOST`` and ``PORT`` environment variables
# consumed by :class:`app.config.BaseConfig`, so a single ``.env`` file
# configures both the Flask application and the gunicorn server.
# ``str(int(...))`` coerces non-numeric port values to a ValueError at
# startup rather than producing an opaque bind error later — a deliberate
# fail-fast posture matching the BaseConfig.PORT attribute.
_host: str = os.environ.get("HOST", _DEFAULT_HOST)
_port: int = int(os.environ.get("PORT", _DEFAULT_PORT))
bind: str = f"{_host}:{_port}"


# ---------------------------------------------------------------------------
# workers — number of worker processes
# ---------------------------------------------------------------------------
# Default is 1 (matching gunicorn's own default) so the development
# experience is uncomplicated. Production deployments should compute the
# canonical value ``2 * nproc + 1`` for I/O-bound workloads (or higher
# for CPU-bound) and pass it via ``GUNICORN_WORKERS``. See AAP §0.6.3
# and the README.md "Production deployment" section for sizing guidance.
workers: int = int(os.environ.get("GUNICORN_WORKERS", _DEFAULT_WORKERS))


# ---------------------------------------------------------------------------
# worker_class — concurrency model
# ---------------------------------------------------------------------------
# Default is gunicorn's ``sync`` class (one request per worker process at
# a time). Documented alternatives:
#
#   * ``gthread`` — combine with ``threads`` to handle multiple requests
#     per worker via a thread pool. Use for I/O-bound workloads with
#     blocking calls (database queries, outbound HTTP).
#   * ``gevent``  — install ``gevent`` separately; use for genuinely
#     async-style I/O via monkey-patched coroutines.
#
# Switching the class requires installing the corresponding extra (e.g.,
# ``pip install gevent``) and passing ``GUNICORN_WORKER_CLASS=gevent``.
worker_class: str = os.environ.get("GUNICORN_WORKER_CLASS", _DEFAULT_WORKER_CLASS)


# ---------------------------------------------------------------------------
# limit_request_line — maximum size of the HTTP request line
# ---------------------------------------------------------------------------
# The CORE FIX for QA Checkpoint 4 Issue 1.
#
# gunicorn's default is 4094 bytes. Setting it to 8190 here:
#
#   * Doubles the surface where Flask's JSON error handlers handle the
#     request (rather than gunicorn's HTML 400 page).
#   * Uses gunicorn's documented maximum non-unlimited value. The
#     gunicorn source (``MAX_REQUEST_LINE = 8190`` in
#     ``gunicorn/http/message.py``) silently caps any value above 8190
#     to 8190 at parser-construction time, so 8190 is the highest
#     non-zero value that has effect.
#   * Preserves DoS protection at the highest documented bounded
#     value.
#   * Remains overridable via ``GUNICORN_LIMIT_REQUEST_LINE`` for
#     deployments that want a different threshold without forking
#     this file.
#
# IMPORTANT: gunicorn's limit_request_line setting has a documented
# special value of ``0`` which DISABLES the explicit limit (the
# parser then falls back to an internal 1 MiB safety net rather than
# being truly unlimited). We intentionally do NOT default to 0 — an
# effectively-unlimited request line is a DoS vector — but operators
# can opt in by setting ``GUNICORN_LIMIT_REQUEST_LINE=0`` after
# auditing the deployment. Values strictly greater than 8190 are
# silently capped by gunicorn; the env override has no special
# handling for those (a value of, say, 16384 set via the env var
# yields the same runtime behavior as 8190).
limit_request_line: int = int(
    os.environ.get("GUNICORN_LIMIT_REQUEST_LINE", _DEFAULT_LIMIT_REQUEST_LINE)
)


# ---------------------------------------------------------------------------
# Server header override — gunicorn-layer fix for QA Checkpoint 4 Issue 3
# ---------------------------------------------------------------------------
# Background
# ----------
# QA Checkpoint 4 Issue 3 reported that gunicorn emits ``Server: gunicorn``
# on every response, advertising the WSGI server identity to clients (and
# therefore to reconnaissance tooling). The application-layer fix in
# :mod:`app.security` sets ``response.headers["Server"] = "api"`` in an
# ``@app.after_request`` hook. That works under the Flask/Werkzeug test
# client, but under real gunicorn it does NOT, because:
#
#   * gunicorn's ``util.hop_headers`` set includes ``server``. Every header
#     the WSGI application emits is filtered in
#     ``Response.process_headers()`` via ``util.is_hoppish(name)``; matching
#     headers are dropped silently, never written to the wire.
#   * gunicorn then emits its OWN ``Server`` line in
#     ``Response.default_headers()`` using ``self.version``, which is
#     bound at instance-construction time to the module-level ``SERVER``
#     name imported into ``gunicorn.http.wsgi`` from ``gunicorn/__init__``.
#
# Result: regardless of what the application sets, the wire response
# contains gunicorn's own ``Server: gunicorn``.
#
# Fix strategy
# ------------
# Rebind the ``SERVER`` (and ``SERVER_SOFTWARE``) module-level constants
# in BOTH ``gunicorn`` and ``gunicorn.http.wsgi`` to a generic token
# (default ``"api"``). Because ``gunicorn.http.wsgi`` performs
# ``from gunicorn import SERVER_SOFTWARE, SERVER`` at its own import
# time, patching only ``gunicorn.SERVER`` is insufficient — the rebind
# must be applied directly to the wsgi module's namespace as well.
#
# This runs once in the master (arbiter) process via the ``on_starting``
# hook below, BEFORE any worker is forked. POSIX ``fork()`` semantics
# guarantee that workers inherit the master's already-patched module
# state in their address spaces, so every worker emits the new token
# without re-running the patch.
#
# The patch is also applied at module-load time as defense-in-depth.
# Some deployment topologies (e.g., ``--preload``) reorder when the
# config file vs. workers vs. the wsgi module are imported; applying
# the patch both eagerly and via the hook ensures the override takes
# effect regardless of ordering.
#
# Why this approach is safe
# -------------------------
# * No gunicorn private API is being called — only public module-level
#   attribute assignment is used, equivalent to setting any global from
#   another module.
# * The patched value is a plain ASCII token; gunicorn's HTTP serialiser
#   uses it verbatim. It must contain no CR/LF (sanitised below).
# * Reverting is a single env-var change (``GUNICORN_SERVER_TOKEN=...``)
#   — the patch is not a code-level hard-pin.
# * The application-layer override in :mod:`app.security` remains in
#   place as defense-in-depth for non-gunicorn deployments (``flask
#   run``, uWSGI, etc.) where the hop-by-hop filter does not apply.
# ---------------------------------------------------------------------------
def _override_server_token(token: str | None = None) -> None:
    """Rebind gunicorn's ``SERVER`` constants to a generic token.

    The function mutates ``gunicorn.SERVER``, ``gunicorn.SERVER_SOFTWARE``,
    ``gunicorn.http.wsgi.SERVER``, and ``gunicorn.http.wsgi.SERVER_SOFTWARE``
    so that subsequent ``Response`` instances emit ``Server: <token>`` on
    every response.

    Parameters
    ----------
    token:
        The replacement value. ``None`` means "read from the
        ``GUNICORN_SERVER_TOKEN`` environment variable, falling back to
        the module-level :data:`_DEFAULT_SERVER_TOKEN`". An empty string
        skips the override (gunicorn's own value remains in effect),
        which is provided as an explicit opt-out for diagnostic scenarios
        but is not the production posture.

    Notes
    -----
    * The token is sanitised by stripping CR/LF characters before being
      written to the module namespaces, defending against header
      injection if the environment variable is supplied from an
      untrusted source.
    * Import is performed inside the function so that the gunicorn
      package does not have to be importable at the moment this config
      file is *parsed* (it is, of course, importable at the moment this
      function is *called* — gunicorn itself is the caller). This makes
      the file slightly more forgiving for non-gunicorn tooling that may
      attempt to import it for analysis.
    """
    import gunicorn  # noqa: PLC0415 — late import is intentional, see docstring
    import gunicorn.http.wsgi as _wsgi_mod  # noqa: PLC0415

    resolved = (
        token
        if token is not None
        else os.environ.get("GUNICORN_SERVER_TOKEN", _DEFAULT_SERVER_TOKEN)
    )
    # Defensive sanitisation — the token is written verbatim into an HTTP
    # header line, so CR/LF must never appear in it. Trim surrounding
    # whitespace too for operator convenience.
    safe_token = resolved.replace("\r", "").replace("\n", "").strip()
    if not safe_token:
        # Empty string means "do not override". Operator explicitly opted
        # out, so leave gunicorn's defaults intact.
        return

    gunicorn.SERVER = safe_token
    gunicorn.SERVER_SOFTWARE = safe_token
    _wsgi_mod.SERVER = safe_token
    _wsgi_mod.SERVER_SOFTWARE = safe_token


def on_starting(server: Arbiter) -> None:  # noqa: ARG001 — hook signature
    """gunicorn lifecycle hook — runs once in the master before fork.

    Parameters
    ----------
    server:
        The arbiter instance (unused here; kept for the gunicorn hook
        contract).

    This is the canonical gunicorn hook for one-shot master-process
    initialisation. We use it to apply the Server-token override before
    any worker is forked, so all workers inherit the patched module
    state (POSIX ``fork()`` semantics).
    """
    _override_server_token()


# Eager defense-in-depth: apply the override at config-load time too.
# In the default (non-preload) topology, ``gunicorn.http.wsgi`` is already
# imported by the time the config module is loaded (it is referenced by
# the worker types that the Arbiter resolves during start-up), so the
# rebind takes immediate effect. In ``--preload`` deployments, both this
# eager call AND the ``on_starting`` hook above ensure the patch is
# applied regardless of the precise import ordering.
_override_server_token()

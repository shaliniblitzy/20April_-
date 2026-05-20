"""Centralized HTTP response security-header middleware for the Flask application.

Purpose
-------
This module is the single, authoritative location where defense-in-depth HTTP
response headers and the response ``Server`` identifier are configured for the
Python/Flask runtime. It exposes one public function,
:func:`register_security_headers`, which the application factory in :mod:`app`
calls during startup to attach a single ``@app.after_request`` hook that
applies the headers to **every** response — successful, redirected, and
error — produced by the application.

Why this module exists
----------------------
The QA Checkpoint 4 review identified three security-hardening findings on
the scaffold:

* **MINOR — Issue 2**: "Enterprise security hardening headers absent on all
  responses." Ten common defense-in-depth headers were absent on every
  response (``X-Content-Type-Options``, ``X-Frame-Options``,
  ``Referrer-Policy``, ``Permissions-Policy``,
  ``Content-Security-Policy``, ``X-XSS-Protection``,
  ``Cross-Origin-Opener-Policy``, ``Cross-Origin-Embedder-Policy``,
  ``Cross-Origin-Resource-Policy``). ``Strict-Transport-Security`` was
  flagged separately as not-applicable absent HTTPS termination.
* **MINOR — Issue 3**: "Server header discloses server identity." All
  responses carried ``Server: gunicorn`` from the WSGI server, marginally
  aiding reconnaissance.

This module addresses both findings in a single, narrow surface: one
``@app.after_request`` hook registered by :func:`register_security_headers`
that (a) sets the ten missing headers and (b) overrides the ``Server`` header
to a generic ``api`` token that does not name the runtime.

Pattern — ``@app.after_request`` hook
-------------------------------------
:func:`register_security_headers` follows the same registration-helper
pattern used by :mod:`app.errors` (:func:`register_error_handlers`) and
:mod:`app.logging_config` (:func:`configure_logging`) so the application
factory's wiring sequence remains uniform:

    1. ``configure_logging(app)`` — emit-time logging contract.
    2. ``register_error_handlers(app)`` — JSON error envelope contract.
    3. ``register_security_headers(app)`` — response header contract (this module).
    4. ``app.register_blueprint(...)`` — route registration.

Centralising header injection in a single hook (rather than per-route or
per-blueprint) guarantees the headers are applied to **every** response:

* Successful 200 OK responses from the ``main``, ``health``, and ``api``
  blueprints.
* Error responses (404, 405, 500, 501) produced by the centralized handlers
  in :mod:`app.errors`.
* Any future routes added downstream when the original Node.js server is
  ported — no per-route opt-in required.

Header set rationale
--------------------

* **X-Content-Type-Options: nosniff** — Disables MIME-sniffing by browsers
  so a response served with ``Content-Type: application/json`` cannot be
  reinterpreted as ``text/html`` and rendered as a script. Universally
  supported by modern browsers. Cost: ~30 bytes per response.
* **X-Frame-Options: DENY** — Forbids embedding any response inside a
  ``<frame>``, ``<iframe>``, ``<embed>``, or ``<object>``. The API has no
  HTML surface that would justify framing; ``DENY`` is therefore safe and
  the strongest available value (vs. ``SAMEORIGIN``). The successor header
  (CSP ``frame-ancestors``) is also set below; both are emitted for
  belt-and-suspenders compatibility with older browsers that only honour
  one of the two.
* **Referrer-Policy: no-referrer** — Suppresses the ``Referer`` header on
  outbound requests originating from this service so embedded URLs do not
  leak into third-party server logs. Appropriate default for an API that
  serves no user-clickable HTML.
* **Permissions-Policy** — Disables hardware-sensitive capabilities the API
  has no use for: geolocation, camera, microphone, USB, payment, etc.
  Browser policy headers are no-ops on backend API responses but cost
  nothing to send and harden a future HTML surface should one be added.
* **Content-Security-Policy** — Restrictive default-src/script-src for the
  JSON-only API: ``default-src 'none'`` denies every loadable resource by
  default (since JSON responses do not load resources); ``frame-ancestors
  'none'`` is the modern successor to ``X-Frame-Options: DENY``. The
  ``base-uri 'none'`` and ``form-action 'none'`` clauses make a hypothetical
  HTML response inert if one is added later by mistake.
* **X-XSS-Protection: 0** — Explicitly DISABLES legacy browser XSS
  auditors. Modern guidance (OWASP, Chromium dev recommendations) is to
  set this to ``0`` because the legacy auditors introduced
  vulnerabilities they were supposed to mitigate. Modern browsers ignore
  the header entirely; this declaration is a defence against any
  remaining legacy installations.
* **Cross-Origin-Opener-Policy: same-origin** — Isolates the browsing
  context group so cross-origin windows cannot directly access this
  origin's ``window`` object. No-op for non-browser callers; safe for
  JSON APIs.
* **Cross-Origin-Embedder-Policy: require-corp** — Ensures any
  cross-origin resource embedded into a page that includes this origin
  must explicitly opt-in via CORP. JSON APIs are not typically embedded
  this way, but the header costs nothing and hardens against future
  pivots.
* **Cross-Origin-Resource-Policy: same-origin** — Blocks ``no-cors``
  cross-origin requests from reading the response body. Appropriate for
  an API whose responses are sensitive by default.

Strict-Transport-Security is intentionally NOT set here:

    HSTS is only meaningful when the application is reached over HTTPS;
    setting it on a plain-HTTP response is at best a no-op and at worst
    confusing to operators inspecting headers behind a TLS-terminating
    reverse proxy. The proper place for HSTS injection is the
    TLS-terminating proxy (nginx, Caddy, AWS ALB, Cloudflare) where TLS
    state is known. This decision is documented in the QA report's
    Issue 2 finding (``Strict-Transport-Security`` listed as
    "N/A without HTTPS termination").

Server header override rationale
--------------------------------
gunicorn does not expose a built-in option to suppress its own ``Server``
header on application responses (only on its own 4xx/5xx error pages). The
``@app.after_request`` hook below therefore overrides the value to the
generic token ``api`` — non-identifying, no version, no implementation
hint. Werkzeug's development server is similarly identified by default
(``Server: Werkzeug/<version> Python/<version>``); the same override
applies in development.

Future Node.js port contract
----------------------------
When the original Node.js source the user referenced (see AAP §0.6.1 and
§0.7.4) is supplied, additional content-type-specific tightening can be
layered on top of this hook without breaking the contract:

* If HTML rendering is introduced, the CSP can be relaxed for ``text/html``
  responses to allow specific script/style sources while keeping the JSON
  contract intact.
* If HTTPS termination is moved into the application tier (e.g., for
  embedded deployments without a reverse proxy), an ``Strict-Transport-
  Security`` header can be added conditionally below.
* If cookies are introduced via :class:`flask.session`, ``SameSite=Strict``
  and ``Secure=True`` should be set on session cookies via
  :class:`app.config.ProductionConfig` rather than in this module.

These are all callable from the same after-request seam, so this module
remains the single point of header policy.

References
----------
* AAP §0.3.3 — Cross-cutting concerns catalog (cross-cutting policy
  centralized in dedicated modules)
* AAP §0.6.7 — Cross-cutting concerns: response policy uniformly applied
* OWASP Secure Headers Project — header recommendations
* MDN ``Content-Security-Policy`` — CSP directive reference
* MDN ``Permissions-Policy`` — Permissions-Policy directive reference
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# ---------------------------------------------------------------------------
# Type-only imports.
# ---------------------------------------------------------------------------
# The :class:`flask.Flask` and :class:`flask.Response` classes are needed
# exclusively for type annotations. Guarding the imports behind
# ``TYPE_CHECKING`` keeps them out of the runtime import graph entirely —
# the annotations are evaluated as strings under
# ``from __future__ import annotations`` above. This mirrors the pattern
# used in :mod:`app.errors`: type-checkers (mypy) see the symbols; the
# runtime does not pay the import cost.
if TYPE_CHECKING:
    from flask import Flask, Response


# ---------------------------------------------------------------------------
# Module constants — header values
# ---------------------------------------------------------------------------
# The security headers and their values are declared as a module-level
# constant so that:
#
#   1. The single source of truth is auditable in one place.
#   2. Tests can import ``_SECURITY_HEADERS`` (via ``app.security``) to
#      assert the exact contract without duplicating header strings.
#   3. Future header additions or value changes require a single edit.
#
# A list of ``(name, value)`` tuples (rather than a dict) is used because:
#
#   * The header order in the on-the-wire response is preserved (some
#     middleware ordering tools rely on stable ordering).
#   * ``flask.Response.headers`` is a :class:`werkzeug.datastructures.Headers`
#     instance whose ``.setdefault`` and ``.set`` methods accept ``(name,
#     value)`` pairs naturally.
#
# The values below are tuned for an API that returns JSON only (see
# module docstring "Header set rationale"). When HTML rendering is
# introduced by the Node.js port, the CSP value will need refinement —
# but the structural seam (this list) and the helper function below
# remain stable.
_SECURITY_HEADERS: tuple[tuple[str, str], ...] = (
    # Disables MIME-sniffing; a JSON response cannot be reinterpreted as
    # text/html and executed as a script.
    ("X-Content-Type-Options", "nosniff"),
    # Forbids framing the response in any browser context.
    ("X-Frame-Options", "DENY"),
    # Suppresses the Referer header on outbound navigation away from this
    # origin. Suitable default for an API with no user-clickable HTML.
    ("Referrer-Policy", "no-referrer"),
    # Disables hardware/feature capabilities the API does not use; values
    # use the structured-headers syntax ``feature=()`` to denote "no
    # origin allowed".
    (
        "Permissions-Policy",
        "geolocation=(), camera=(), microphone=(), usb=(), payment=(), interest-cohort=()",
    ),
    # Restrictive CSP for JSON-only responses. ``default-src 'none'`` blocks
    # all resource loads by default; ``frame-ancestors 'none'`` is the
    # modern successor to X-Frame-Options; ``base-uri`` and ``form-action``
    # are belt-and-suspenders against accidental HTML responses.
    (
        "Content-Security-Policy",
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
    ),
    # Explicitly disable the legacy XSS auditor (OWASP/Chromium guidance).
    ("X-XSS-Protection", "0"),
    # Cross-origin isolation: prevent cross-origin window access.
    ("Cross-Origin-Opener-Policy", "same-origin"),
    # Cross-origin isolation: require cross-origin resources to opt in.
    ("Cross-Origin-Embedder-Policy", "require-corp"),
    # Cross-origin isolation: block no-cors cross-origin reads of the body.
    ("Cross-Origin-Resource-Policy", "same-origin"),
)


# The generic ``Server`` token used to override the default
# ``Server: gunicorn`` (or ``Server: Werkzeug/...``) identification. The
# value is intentionally non-identifying: it does not name the runtime,
# server, or version — only the high-level role ("api"). An empty string
# would also work but some clients log a warning when the header is
# completely empty; the generic ``"api"`` token is therefore preferred.
_SERVER_TOKEN: str = "api"


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------
def register_security_headers(app: Flask) -> None:
    """Register the security-header ``after_request`` hook on the Flask app.

    Attaches a single ``@app.after_request`` callback that mutates the
    outgoing :class:`flask.Response` object to include the standard set
    of defense-in-depth headers documented in the module docstring AND
    override the ``Server`` header to a generic identifier.

    The hook is added at registration time, so every response Flask
    produces — including responses from blueprint handlers, error
    handlers in :mod:`app.errors`, and Flask's own internal routes
    (e.g., 404s for unmatched URLs) — flows through it and gains the
    headers. There is no opt-out: this is intentional, because every
    response from a JSON API should carry these headers.

    Idempotency
    -----------
    Calling :func:`register_security_headers` multiple times on the
    same :class:`flask.Flask` instance registers the hook multiple
    times. The application factory in :mod:`app` invokes this function
    exactly once per :class:`Flask` instance, so multi-registration
    is not a concern in practice. If a future caller does invoke this
    function repeatedly, the same headers are simply set multiple
    times — the final wire value is unchanged because each invocation
    sets the same value.

    Header value override semantics
    -------------------------------
    The hook uses :meth:`werkzeug.datastructures.Headers.set` (not
    :meth:`~werkzeug.datastructures.Headers.add`) so that:

    * The ``Server`` header from the WSGI server is REPLACED, not
      appended (the goal is to suppress disclosure).
    * The security headers are SET ONCE, not appended — guarding
      against double-application when the request lifecycle invokes
      the hook through nested middleware.

    For the security headers we additionally call ``.setdefault`` first
    so that any explicit per-route override (a hypothetical
    blueprint-specific stricter CSP, for example) is preserved. The
    ``Server`` header is unconditionally replaced because there is no
    legitimate reason to keep the WSGI server's default identifier.

    Args:
        app: The :class:`flask.Flask` application instance constructed
            by the application factory. The hook is attached to this
            instance only; other Flask instances in the same process
            (e.g., pytest fixtures building independent apps) each
            receive their own registration call from the factory.

    Returns:
        None. The side effect — registering the ``after_request`` hook
        on ``app`` — is the entire point. The application factory
        discards the return value.
    """

    @app.after_request
    def _apply_security_headers(response: Response) -> Response:
        """Apply security headers and override the Server identifier.

        Called by Flask after every request handler (including error
        handlers) and before the response is returned to the client.
        The function operates on the existing :class:`flask.Response`
        in place and returns it unchanged — the canonical
        ``after_request`` pattern.

        Args:
            response: The :class:`flask.Response` object Flask is
                preparing to return. Mutated in place to add the
                security headers and replace the ``Server`` header.

        Returns:
            The same :class:`flask.Response` instance after mutation.
            Returning the response is required by Flask's
            ``after_request`` contract; returning a NEW object
            (rather than mutating) would also work but is not used
            here because the existing response carries the body,
            status, and content-type already set by the handler.
        """
        # ----- Defense-in-depth headers -----
        # ``setdefault`` preserves any per-route override that may
        # already be set on the response (a future blueprint could
        # tighten the CSP without losing the rest of the policy here).
        # The hook is the LAST line of defence; it never overrides
        # narrower policy that an upstream handler explicitly set.
        for name, value in _SECURITY_HEADERS:
            response.headers.setdefault(name, value)

        # ----- Server header override -----
        # Use ``set`` (not ``setdefault``) so that the default
        # ``Server: gunicorn`` (or ``Server: Werkzeug/...``) value is
        # REPLACED by the generic identifier. There is no legitimate
        # reason for an upstream handler to want the WSGI server's
        # default identifier on the wire; replacing it is therefore
        # unconditional.
        response.headers["Server"] = _SERVER_TOKEN

        return response


# ---------------------------------------------------------------------------
# Public API export.
# ---------------------------------------------------------------------------
# Explicitly enumerate the public surface of this module so that:
#   * ``from app.security import *`` exposes only the documented function;
#   * static analysers and IDEs treat the private constants
#     (``_SECURITY_HEADERS``, ``_SERVER_TOKEN``) as internal-only;
#   * future additions to this module are forced through a deliberate
#     update of ``__all__`` rather than slipping in as accidental
#     public API.
__all__ = ["register_security_headers"]

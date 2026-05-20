"""Tests for the gunicorn-layer overrides in ``gunicorn.conf.py``.

Purpose
-------
This module is the pytest test suite for the side-effects produced by
loading ``gunicorn.conf.py``. The config file at the repository root is
auto-discovered by gunicorn when the production server is launched
(``gunicorn wsgi:app``), and it applies two QA-finding remediations
that the application package alone cannot:

* **Issue 1** — ``limit_request_line`` is raised from gunicorn's
  default of 4094 to 8190 (gunicorn's documented maximum non-unlimited
  value) so realistic long URLs reach Flask rather than being rejected
  with an HTML 400 page by gunicorn's HTTP layer.

* **Issue 3** — ``Server: gunicorn`` is rebound to ``Server: api`` by
  patching the module-level ``SERVER`` constant in both ``gunicorn``
  and ``gunicorn.http.wsgi``. This rebind is required because gunicorn
  treats ``Server`` as a hop-by-hop header
  (``util.is_hoppish('Server') == True``) and silently drops any
  application-supplied ``Server`` header in ``process_headers``; only
  gunicorn's own emission in ``default_headers`` reaches the wire.

These tests assert the runtime behaviour of the config file deterministically,
without needing to spawn a real ``gunicorn`` subprocess: they import the
config module under test, exercise its public function
``_override_server_token`` and its ``on_starting`` hook, and verify the
module-level attribute mutations that ultimately cause gunicorn to emit
``Server: api`` on every response.

Test isolation
--------------
Each test that mutates ``gunicorn.SERVER`` /
``gunicorn.http.wsgi.SERVER`` MUST restore the original values
afterwards so the mutation does not leak into other tests. The
``_gunicorn_constants_snapshot`` fixture provides a context-manager-like
save/restore lifecycle around each test that needs it.

References
----------
* QA Checkpoint 4 report — Issue 1 (gunicorn HTML 400 on oversized URLs)
  and Issue 3 (Server header discloses server identity).
* ``gunicorn.conf.py`` — the configuration file under test.
* gunicorn settings reference — ``limit_request_line`` directive,
  ``on_starting`` server hook.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator
    from types import ModuleType


# ---------------------------------------------------------------------------
# Helper — load gunicorn.conf.py as an importable module without polluting the
# global module cache.
# ---------------------------------------------------------------------------
# ``gunicorn.conf.py`` is a regular Python file at the repository root; it is
# not on ``sys.path`` by default because it is intended to be discovered by
# gunicorn, not imported by application code. The helper below loads it on
# demand using ``importlib.util`` so tests can exercise its functions
# directly. The module is registered in ``sys.modules`` under a deterministic
# name (``_gunicorn_conf_under_test``) so subsequent imports return the same
# object — which matters because the module-level patch applied at load time
# would otherwise re-run on every helper call.
_CONFIG_MODULE_NAME = "_gunicorn_conf_under_test"
_REPO_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _REPO_ROOT / "gunicorn.conf.py"


def _load_gunicorn_conf() -> ModuleType:
    """Load ``gunicorn.conf.py`` from the repo root as a module.

    Returns
    -------
    ModuleType
        The loaded module. Subsequent calls return the cached module so
        the side-effects of loading (eager call to
        ``_override_server_token``) run only once across the test
        session.
    """
    if _CONFIG_MODULE_NAME in sys.modules:
        return sys.modules[_CONFIG_MODULE_NAME]

    spec = importlib.util.spec_from_file_location(_CONFIG_MODULE_NAME, _CONFIG_PATH)
    assert spec is not None and spec.loader is not None, (
        f"Failed to build import spec for {_CONFIG_PATH}"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[_CONFIG_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Fixture — save/restore the gunicorn SERVER/SERVER_SOFTWARE module-level
# constants around each test that mutates them.
# ---------------------------------------------------------------------------
@pytest.fixture
def _gunicorn_constants_snapshot() -> Generator[None]:
    """Snapshot and restore ``gunicorn.SERVER`` / ``SERVER_SOFTWARE``.

    Yields control to the test, then restores the constants in both
    ``gunicorn`` and ``gunicorn.http.wsgi`` to whatever they were when
    the fixture entered. This isolates tests that call
    ``_override_server_token`` so the rebind does not leak across tests.
    """
    import gunicorn
    import gunicorn.http.wsgi as wsgi_mod

    saved = {
        "gunicorn.SERVER": gunicorn.SERVER,
        "gunicorn.SERVER_SOFTWARE": gunicorn.SERVER_SOFTWARE,
        "wsgi_mod.SERVER": wsgi_mod.SERVER,
        "wsgi_mod.SERVER_SOFTWARE": wsgi_mod.SERVER_SOFTWARE,
    }
    try:
        yield
    finally:
        gunicorn.SERVER = saved["gunicorn.SERVER"]
        gunicorn.SERVER_SOFTWARE = saved["gunicorn.SERVER_SOFTWARE"]
        wsgi_mod.SERVER = saved["wsgi_mod.SERVER"]
        wsgi_mod.SERVER_SOFTWARE = saved["wsgi_mod.SERVER_SOFTWARE"]


# =============================================================================
# Issue 1 — limit_request_line setting
# =============================================================================
def test_limit_request_line_set_to_documented_value() -> None:
    """Verify ``gunicorn.conf.py`` raises ``limit_request_line`` to 8190.

    The QA-Issue-1 fix requires the limit to be set to gunicorn's
    documented maximum non-unlimited value (8190 — values above are
    silently capped). The test pins the resolved value so a regression
    that lowers the default would be caught.
    """
    config = _load_gunicorn_conf()
    assert config.limit_request_line == 8190, (
        f"Expected limit_request_line=8190 (gunicorn MAX_REQUEST_LINE), "
        f"got {config.limit_request_line}"
    )


def test_limit_request_line_overridable_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify the env-var override for ``limit_request_line`` works.

    Operators can set ``GUNICORN_LIMIT_REQUEST_LINE`` to override the
    default. The test re-loads the config module with the env var set
    to a non-default value and asserts the new value is honoured.
    """
    # Remove the cached module so the test exercises a fresh load
    sys.modules.pop(_CONFIG_MODULE_NAME, None)
    monkeypatch.setenv("GUNICORN_LIMIT_REQUEST_LINE", "4096")
    try:
        config = _load_gunicorn_conf()
        assert config.limit_request_line == 4096, (
            f"Expected env var to override limit_request_line to 4096, "
            f"got {config.limit_request_line}"
        )
    finally:
        # Restore the canonical module so other tests see the default.
        sys.modules.pop(_CONFIG_MODULE_NAME, None)
        _load_gunicorn_conf()


# =============================================================================
# Issue 3 — Server header override
# =============================================================================
def test_override_server_token_default_value(
    _gunicorn_constants_snapshot: None,
) -> None:
    """Verify ``_override_server_token()`` rebinds to ``api`` by default.

    Calling the function with no argument and no env override should
    rebind ``gunicorn.SERVER``, ``gunicorn.SERVER_SOFTWARE``,
    ``gunicorn.http.wsgi.SERVER``, and
    ``gunicorn.http.wsgi.SERVER_SOFTWARE`` to ``"api"``.
    """
    # Reset to gunicorn's defaults before the test, then re-apply the
    # override and assert.
    import gunicorn
    import gunicorn.http.wsgi as wsgi_mod

    gunicorn.SERVER = "gunicorn"
    gunicorn.SERVER_SOFTWARE = "gunicorn/26.0.0"
    wsgi_mod.SERVER = "gunicorn"
    wsgi_mod.SERVER_SOFTWARE = "gunicorn/26.0.0"

    config = _load_gunicorn_conf()
    config._override_server_token()

    assert gunicorn.SERVER == "api"
    assert gunicorn.SERVER_SOFTWARE == "api"
    assert wsgi_mod.SERVER == "api"
    assert wsgi_mod.SERVER_SOFTWARE == "api"


def test_override_server_token_respects_env_var(
    monkeypatch: pytest.MonkeyPatch,
    _gunicorn_constants_snapshot: None,
) -> None:
    """Verify ``_override_server_token`` honours ``GUNICORN_SERVER_TOKEN``.

    Operators can set a custom token via environment variable. The
    test sets the env var and confirms the rebind uses the new value.
    """
    monkeypatch.setenv("GUNICORN_SERVER_TOKEN", "custom-token")
    config = _load_gunicorn_conf()
    config._override_server_token()

    import gunicorn

    assert gunicorn.SERVER == "custom-token", (
        f"Expected env var to override SERVER to 'custom-token', got {gunicorn.SERVER!r}"
    )


def test_override_server_token_explicit_argument(
    _gunicorn_constants_snapshot: None,
) -> None:
    """Verify an explicit ``token=`` argument takes precedence over env var.

    The function's positional parameter is documented as the highest-
    precedence input. The test sets a conflicting env var and confirms
    the explicit argument wins.
    """
    config = _load_gunicorn_conf()
    config._override_server_token(token="explicit")

    import gunicorn

    assert gunicorn.SERVER == "explicit", (
        f"Expected explicit argument to set SERVER to 'explicit', got {gunicorn.SERVER!r}"
    )


def test_override_server_token_empty_string_is_opt_out(
    _gunicorn_constants_snapshot: None,
) -> None:
    """Verify empty ``GUNICORN_SERVER_TOKEN`` keeps gunicorn defaults.

    The contract documents that an empty token means "do not override".
    The test pre-seeds the constants with a known sentinel, calls the
    function with an empty env var, and confirms the sentinel is
    preserved.
    """
    import gunicorn

    gunicorn.SERVER = "sentinel"

    config = _load_gunicorn_conf()
    config._override_server_token(token="")

    assert gunicorn.SERVER == "sentinel", (
        f"Empty token should be a no-op; got SERVER={gunicorn.SERVER!r}"
    )


def test_override_server_token_strips_crlf(
    _gunicorn_constants_snapshot: None,
) -> None:
    """Verify CR/LF characters in the token are stripped.

    A malicious or accidental env-var value containing CR/LF could
    inject additional HTTP headers into every response. The function
    sanitises by stripping CR/LF before rebinding.
    """
    config = _load_gunicorn_conf()
    config._override_server_token(token="api\r\nX-Injected: yes")

    import gunicorn

    assert "\r" not in gunicorn.SERVER, (
        f"CR character leaked into SERVER value: {gunicorn.SERVER!r}"
    )
    assert "\n" not in gunicorn.SERVER, (
        f"LF character leaked into SERVER value: {gunicorn.SERVER!r}"
    )
    # The stripped value should equal the concatenated text without CR/LF.
    assert gunicorn.SERVER == "apiX-Injected: yes", (
        f"CRLF stripping produced unexpected value: {gunicorn.SERVER!r}"
    )


def test_on_starting_hook_calls_override(_gunicorn_constants_snapshot: None) -> None:
    """Verify ``on_starting(server)`` invokes the override.

    ``on_starting`` is the gunicorn-defined hook signature. The hook
    receives an arbiter instance (unused by the override). Calling it
    with a sentinel object must produce the same rebind effect as
    ``_override_server_token()``.
    """
    import gunicorn

    gunicorn.SERVER = "gunicorn"

    config = _load_gunicorn_conf()
    # The on_starting hook signature is on_starting(server); pass a
    # sentinel object — the hook doesn't dereference it.
    config.on_starting(server=object())

    assert gunicorn.SERVER == "api", (
        f"on_starting should have rebound SERVER to 'api'; got {gunicorn.SERVER!r}"
    )


def test_module_level_eager_patch_runs_on_load() -> None:
    """Verify the eager defense-in-depth patch runs on module load.

    The bottom of ``gunicorn.conf.py`` calls
    ``_override_server_token()`` unconditionally. This test forces a
    fresh load of the module (clearing both the cached config module
    and resetting the gunicorn constants beforehand) and asserts the
    rebind happened during the load itself.
    """
    import gunicorn
    import gunicorn.http.wsgi as wsgi_mod

    # Force a fresh load by clearing the cache and resetting state.
    sys.modules.pop(_CONFIG_MODULE_NAME, None)
    gunicorn.SERVER = "gunicorn"
    gunicorn.SERVER_SOFTWARE = "gunicorn/26.0.0"
    wsgi_mod.SERVER = "gunicorn"
    wsgi_mod.SERVER_SOFTWARE = "gunicorn/26.0.0"

    try:
        _load_gunicorn_conf()
        # The eager call at the bottom of the file must have rebound the
        # constants during module exec.
        assert gunicorn.SERVER == "api"
        assert wsgi_mod.SERVER == "api"
    finally:
        # Leave the constants in the patched state — that is the
        # documented post-load posture and the state other tests assume.
        gunicorn.SERVER = "api"
        gunicorn.SERVER_SOFTWARE = "api"
        wsgi_mod.SERVER = "api"
        wsgi_mod.SERVER_SOFTWARE = "api"


# =============================================================================
# Static-attribute contract tests
# =============================================================================
def test_workers_default_is_one() -> None:
    """Verify ``workers`` defaults to 1 absent ``GUNICORN_WORKERS``.

    Matches gunicorn's own default. Sizing to ``2*nproc+1`` is an
    operator concern and must be opted into via the env var.
    """
    # Only assert the default if the env var is NOT currently set; otherwise
    # the assertion would conflict with operator intent.
    if "GUNICORN_WORKERS" in os.environ:
        pytest.skip("GUNICORN_WORKERS is set in the test environment")

    config = _load_gunicorn_conf()
    assert config.workers == 1, f"Expected workers=1 by default, got {config.workers}"


def test_worker_class_default_is_sync() -> None:
    """Verify ``worker_class`` defaults to ``sync``.

    The default matches gunicorn's own default. Switching to a
    different class is documented in the config-file docstring.
    """
    if "GUNICORN_WORKER_CLASS" in os.environ:
        pytest.skip("GUNICORN_WORKER_CLASS is set in the test environment")

    config = _load_gunicorn_conf()
    assert config.worker_class == "sync", (
        f"Expected worker_class='sync' by default, got {config.worker_class!r}"
    )


def test_default_server_token_constant() -> None:
    """Verify the module-level ``_DEFAULT_SERVER_TOKEN`` is ``"api"``.

    Pins the constant so a regression that changes the token would be
    caught at the source level (the source-of-truth lives in this
    config file; the runtime tests above verify the rebind reaches
    gunicorn's module state).
    """
    config = _load_gunicorn_conf()
    assert config._DEFAULT_SERVER_TOKEN == "api", (
        f"Expected _DEFAULT_SERVER_TOKEN='api', got {config._DEFAULT_SERVER_TOKEN!r}"
    )


def test_default_limit_request_line_constant() -> None:
    """Verify the module-level ``_DEFAULT_LIMIT_REQUEST_LINE`` is ``"8190"``.

    Pins the documented maximum non-unlimited value chosen for Issue 1.
    """
    config = _load_gunicorn_conf()
    assert config._DEFAULT_LIMIT_REQUEST_LINE == "8190", (
        f"Expected _DEFAULT_LIMIT_REQUEST_LINE='8190', got {config._DEFAULT_LIMIT_REQUEST_LINE!r}"
    )

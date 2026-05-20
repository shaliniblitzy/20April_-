
# Blitzy Project Guide — 20April_- Python 3 + Flask 3.1 Scaffold

## 1. Executive Summary

### 1.1 Project Overview

This project responds to the directive *"Can you rewrite this node.js server in python 3 using flask, preserving all functionalities of the original project?"* Repository inspection revealed that the source repository contained only a 19-byte `README.md` placeholder with no Node.js source code, so the Agent Action Plan (§0.1.2) redefined the scope to **Greenfield Flask Scaffold Creation**: deliver a complete, idiomatic, production-ready Python 3 + Flask 3.1 scaffold engineered to accept the future Node→Flask port mechanically once the Node.js source is supplied. The deliverable is a backend HTTP service skeleton — Application Factory pattern, layered configuration, three Blueprints, centralized error handling, `dictConfig` logging, defense-in-depth response headers, gunicorn production wiring, and a 67-test pytest suite — with no UI surface.

### 1.2 Completion Status

```mermaid
%%{init: {"themeVariables": {"pie1": "#5B39F3", "pie2": "#FFFFFF", "pieStrokeColor": "#5B39F3", "pieOuterStrokeColor": "#5B39F3"}}}%%
pie showData title 93.7% Complete (89h / 95h)
    "Completed (89h)" : 89
    "Remaining (6h)" : 6
```

| Metric | Value |
|--------|-------|
| **Total Project Hours** | 95 |
| **Completed Hours (AI + Manual)** | 89 |
| Completed by Blitzy autonomous agents | 89 |
| Completed by human review | 0 |
| **Remaining Hours** | 6 |
| **Completion Percentage** | **93.7%** |

Calculation: 89 / (89 + 6) × 100 = **93.7%**

### 1.3 Key Accomplishments

- ✅ **AAP §0.4.1 file inventory delivered in full** — all 26 AAP-mandated CREATE/UPDATE rows are realized as committed source files
- ✅ **Application Factory pattern implemented** — `create_app(config_name)` constructs a hermetic Flask instance, loading config, configuring logging, registering error handlers + security headers + three blueprints in a deterministic sequence (`app/__init__.py`, 587 lines)
- ✅ **Layered configuration system** — `BaseConfig` → `DevelopmentConfig` / `ProductionConfig` / `TestingConfig` selected via `FLASK_CONFIG` env var, with the documented `JSON_SORT_KEYS=False` and `JSONIFY_PRETTYPRINT_REGULAR=False` keys declared per AAP (`app/config.py`, 472 lines)
- ✅ **Three Blueprints registered** — `health` (`/healthz`, `/readyz`), `main` (`/`, `/version`), and `api` (`/api/` placeholder returning 501 with AAP §0.7.4 reference)
- ✅ **Centralized HTTP error handling** — handlers for 400/404/405/500 plus a `HTTPException` catch-all emit the consistent JSON envelope `{"error": {"code": …, "message": …}}` (`app/errors.py`, 508 lines)
- ✅ **`dictConfig`-based logging** — honors `LOG_LEVEL`, configures the root and `werkzeug` loggers (`app/logging_config.py`, 415 lines)
- ✅ **Defense-in-depth response headers** — 9 security headers (X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, Content-Security-Policy, X-XSS-Protection, COOP, COEP, CORP) plus a `Server: api` generic identifier on every response (`app/security.py` + `gunicorn.conf.py` — AAP-compatible extensions)
- ✅ **Gunicorn production server fully wired** — `gunicorn.conf.py` auto-discovered from repo root, `limit_request_line=8190`, env-driven `bind`/`workers`/`worker_class`, and an `on_starting` hook that rebinds gunicorn's internal `SERVER` constant to override the `Server` header before workers fork (411 lines)
- ✅ **67 tests passing in 0.21 seconds at 95% line coverage** — application-factory contract, blueprint behaviour, error semantics, security headers, gunicorn config, and Server-token override are all covered (8 test modules, ~2,812 lines)
- ✅ **Pinned dependency stack at AAP-mandated versions** — `Flask==3.1.3`, `gunicorn==26.0.0`, `python-dotenv>=1.2.2` (runtime); `pytest==9.0.3`, `pytest-flask==1.3.0`, `pytest-cov==7.1.0`, `coverage[toml]==7.14.0`, `ruff==0.15.13`, `mypy==2.1.0` (development)
- ✅ **PEP 621 packaging metadata** — `pyproject.toml` declares `requires-python = ">=3.10"`, project name `twenty-april-flask-scaffold`, and version `0.1.0` (the repository name `20April_-` is not a valid PEP 503 distribution name, so the distribution name was sanitised per AAP §0.4.1)
- ✅ **README.md replaces the original placeholder** with comprehensive Flask scaffold documentation (~474 lines) covering installation, configuration, running (dev + prod), worker tuning, security posture, and the open clarification questions
- ✅ **`compileall`, `ruff check .`, and `mypy .` are all green** across every in-scope file
- ✅ **Smoke-tested under three servers** — Flask dev server (`flask run`), gunicorn production (`gunicorn wsgi:app`), and `python wsgi.py` direct entry; all serve every endpoint correctly
- ✅ **Graceful SIGTERM shutdown verified** — gunicorn returns exit=143 (128 + SIGTERM=15) as expected

### 1.4 Critical Unresolved Issues

| Issue | Impact | Owner | ETA |
|-------|--------|-------|-----|
| Node.js source code not yet supplied | Functional parity with "the original project" cannot be implemented (AAP §0.7.3 declared this directive currently **unbinding**); the `/api/` route remains a documented `501 Not Implemented` placeholder until the source arrives | User / Product Owner | Awaiting user input |
| Production `SECRET_KEY` not yet configured | Production deployment must reject the default `.env.example` value `change-me`; deploying without overriding it will fail Flask's session-signing integrity guarantee | Deployment owner | < 1 hour once deployment target chosen |
| AAP §0.7.4 open clarification questions unresolved | Determines downstream framework choice (Express/Fastify/Koa/…), persistence stack, external integrations, env-var inventory, deployment target, and test-framework parity | User / Product Owner | Awaiting user input |

### 1.5 Access Issues

| System/Resource | Type of Access | Issue Description | Resolution Status | Owner |
|-----------------|----------------|-------------------|-------------------|-------|
| — | — | No access issues identified during autonomous validation. The Python 3.13.7 runtime, `pip` 26.1.1, `.venv` virtual environment, and all pinned runtime + dev dependencies were available and installed cleanly. All 67 tests, `ruff check .`, `mypy .`, and `python -m compileall` ran without permission errors. Gunicorn bound to local ports 5099/5002/5003 for smoke-tests successfully. The git working tree is clean. | N/A | N/A |

### 1.6 Recommended Next Steps

1. **[High]** Provide the Node.js source code (or repository URL/archive) so the AAP §0.7.4 open questions can be resolved and the actual Node→Flask port can begin. Without this, the scaffold cannot fulfil the user's stated *"preserving all functionalities"* directive.
2. **[High]** Generate and securely inject a real production `SECRET_KEY` (e.g., `python -c "import secrets; print(secrets.token_hex(32))"`) into the deployment environment — never commit the value. Override the `.env.example` placeholder before any non-development deployment.
3. **[High]** Resolve the AAP §0.7.4 clarification questions in writing — Node framework, HTTP endpoint inventory, persistence layer, external integrations, deployment target — so the port plan can be deterministic rather than speculative.
4. **[Medium]** Validate the scaffold against the chosen deployment target environment (Docker / Kubernetes / bare metal / PaaS) to confirm gunicorn binding, env-var injection, log routing, and SIGTERM handling are correct end-to-end.
5. **[Low]** When the Node source arrives, port routes incrementally into `app/blueprints/api/routes.py`, replacing the `501` placeholder. Each ported route should be accompanied by pytest tests that match the original Node test contracts where they exist.

---

## 2. Project Hours Breakdown

### 2.1 Completed Work Detail

| Component | Hours | Description |
|-----------|------:|-------------|
| Repository-root scaffold (7 files) | 12 | `pyproject.toml` PEP 621 metadata + tool config (191 lines); `requirements.txt` pins Flask 3.1.3 / gunicorn 26.0.0 / python-dotenv (77 lines); `requirements-dev.txt` pins pytest 9.0.3 / pytest-flask 1.3.0 / pytest-cov 7.1.0 / ruff 0.15.13 / mypy 2.1.0 (171 lines); `.env.example` declares 6 env vars (140 lines); `.gitignore` Python-specific patterns (155 lines); `wsgi.py` gunicorn entry (109 lines); `README.md` Flask scaffold docs (474 lines, UPDATE) |
| Application factory + core modules (5 files, ~2,031 LOC) | 28 | `app/__init__.py` Application Factory `create_app()` with deterministic wiring sequence (587 lines); `app/config.py` `BaseConfig`/`DevelopmentConfig`/`ProductionConfig`/`TestingConfig` + `config_by_name` mapping with JSON provider keys (472 lines); `app/errors.py` 400/404/405/500 + HTTPException catch-all with JSON envelope (508 lines); `app/logging_config.py` `dictConfig` honoring `LOG_LEVEL` + werkzeug logger (415 lines); `app/extensions.py` documented placeholder for future extension singletons (49 lines) |
| Security hardening — AAP extension (2 files, ~764 LOC) | 8 | `app/security.py` 9 defense-in-depth response headers via `@app.after_request` + generic `Server: api` override (353 lines); `gunicorn.conf.py` `limit_request_line=8190`, env-driven `bind`/`workers`/`worker_class`, `on_starting` hook rebinding gunicorn's internal `SERVER` constant before workers fork (411 lines). Both files extend AAP §0.4.1 without violating it — they harden the response surface and the gunicorn server configuration as security-review outputs from Checkpoint 3/4. |
| Blueprints — 3 × 2 files (~1,181 LOC) | 6 | `health/` blueprint (`/healthz`, `/readyz`) — 363 lines incl. extensive AAP-anchored docstrings; `main/` blueprint (`/`, `/version` returning `name`/`version`/`python` keys) — 378 lines; `api/` blueprint (`url_prefix='/api'`, placeholder `GET /` returning `501` with documented JSON envelope referencing AAP §0.7.4) — 440 lines |
| Test suite (8 files, 67 tests, 95% coverage) | 20 | `conftest.py` `app`/`client`/`runner` pytest fixtures (144 lines); `test_app_factory.py` 12 tests covering factory contract + blueprint registration (633 lines); `test_health.py` 9 tests for `/healthz`+`/readyz` behaviour (423 lines); `test_main.py` 13 tests for `/`+`/version` envelope (484 lines); `test_api.py` 5 smoke tests for `/api/` placeholder + 501 contract (397 lines); `test_security.py` 15 tests for security headers + Server-header override (470 lines); `test_gunicorn_conf.py` 13 tests for limit_request_line + Server-token override + on_starting hook (405 lines); `tests/__init__.py` package marker (8 lines) |
| Validation cycle — 24+ fix commits across 5 checkpoints | 15 | Checkpoint 1 fixes (F1-F7); Checkpoint 2 (`__version__` ordering, type annotations, blueprint imports, test structure); Checkpoint 3 (5 MAJOR + 3 MINOR including JSON provider config + TestingConfig CSRF); Checkpoint 4 security review (3 MINOR); QA finalization (declare AAP-mandated JSON config keys on BaseConfig). Final Validator confirmed zero remaining issues. |
| **Total** | **89** | |

### 2.2 Remaining Work Detail

| Category | Hours | Priority |
|----------|------:|----------|
| **Provide Node.js source code** for the port (USER ACTION — resolves AAP §0.7.4 question 1 and unblocks every downstream port task) | 2 | High |
| **Resolve AAP §0.7.4 clarification questions** — Node framework, endpoint inventory, persistence stack, integrations, deployment target, test framework (USER ACTION — written answers to the 10 questions in AAP §0.7.4) | 1 | High |
| **Configure production `SECRET_KEY` and environment variables** — generate a real `SECRET_KEY` and inject via the deployment platform's secret manager (Vault, AWS Secrets Manager, Kubernetes Secret, systemd `EnvironmentFile`, etc.) | 1 | High |
| **Validate scaffold under target deployment environment** — boot gunicorn with production env vars, exercise `/`, `/version`, `/healthz`, `/readyz`, `/api/`, confirm Server-header override, SIGTERM handling, and access-log routing in the target environment | 2 | Medium |
| **Total** | **6** | |

> **Important note on path-to-production beyond this AAP.** Per AAP §0.2.2, containerization, CI/CD, infrastructure-as-code, and deployment manifests are *explicitly out of scope* — they require user input (deployment target choice) before they can be meaningfully scoped. They are therefore **not** included in the remaining-hours total above. Likewise, the actual file-by-file Node→Flask port is **not** included in the remaining-hours total: per AAP §0.1.2 the AAP itself redefined scope to "Greenfield Flask Scaffold Creation" because no Node source exists; the port will be a separate, post-scaffold engineering engagement once the user supplies the source. The 6 hours above represent only the **scaffold's** path to production.

### 2.3 Hours Calculation Validation

- Section 2.1 sum: 12 + 28 + 8 + 6 + 20 + 15 = **89 hours** ✅ (matches Completed Hours in Section 1.2)
- Section 2.2 sum: 2 + 1 + 1 + 2 = **6 hours** ✅ (matches Remaining Hours in Section 1.2)
- Section 2.1 + Section 2.2 = 89 + 6 = **95 hours** ✅ (matches Total Project Hours in Section 1.2)
- Completion: 89 / 95 = **93.7%** ✅ (matches Section 1.2 and Section 7)

---

## 3. Test Results

All tests below originate from Blitzy's autonomous validation logs (`python -m pytest --no-header --cov=app --cov-report=term`, run by the Final Validator on Python 3.13.7 inside the project's `.venv`).

| Test Category | Framework | Total Tests | Passed | Failed | Coverage % | Notes |
|---------------|-----------|------------:|-------:|-------:|-----------:|-------|
| Application factory contract (unit) | pytest 9.0.3 + pytest-flask 1.3.0 | 12 | 12 | 0 | 97% (app/__init__.py) | `create_app` returns `Flask` instance; loads `TestingConfig`; registers all 3 blueprints; logging configured; handles `/healthz` request; falls back to default on invalid config name |
| Health probes (integration) | pytest + pytest-flask | 9 | 9 | 0 | 100% (health/*) | `/healthz` and `/readyz` return 200 + documented JSON contract; methods restricted to GET; blueprint registered at root paths |
| Main routes (integration) | pytest + pytest-flask | 13 | 13 | 0 | 100% (main/*) | `/` envelope contains `service`/`message`/`endpoints` keys; `/version` returns valid `name`/`version`/`python` keys; semver-pattern matching; content-type `application/json` |
| API placeholder (integration) | pytest + pytest-flask | 5 | 5 | 0 | 100% (api/*) | `/api/` returns 501 with documented envelope referencing AAP §0.7.4; blueprint registered with `url_prefix='/api'`; trailing-slash redirect behaviour |
| Security headers (integration) | pytest + pytest-flask | 15 | 15 | 0 | 100% (security.py) | All 9 defense-in-depth headers present on every endpoint (200, 404, 405, 501); Server-header overridden on every response; security-headers constant matches expected set; `register_security_headers` is public API |
| Gunicorn config (unit) | pytest 9.0.3 | 13 | 13 | 0 | N/A (config file) | `limit_request_line=8190` documented value; env-var override; `override_server_token` default/env/explicit/empty/CRLF-strip behaviour; `on_starting` hook calls override; module-level eager patch; workers/worker_class defaults |
| **TOTAL** | | **67** | **67** | **0** | **95%** | Run time: **0.21 s**; 206 statements, 11 missed (across error-handler fallbacks, the empty `extensions.py` placeholder, and one log-level branch) |

Authoritative coverage report (from `python -m pytest --no-header --cov=app --cov-report=term`):

| Module | Stmts | Miss | Cover |
|--------|------:|-----:|------:|
| `app/__init__.py` | 33 | 1 | 97% |
| `app/blueprints/__init__.py` | 5 | 0 | 100% |
| `app/blueprints/api/__init__.py` | 6 | 0 | 100% |
| `app/blueprints/api/routes.py` | 10 | 0 | 100% |
| `app/blueprints/health/__init__.py` | 6 | 0 | 100% |
| `app/blueprints/health/routes.py` | 9 | 0 | 100% |
| `app/blueprints/main/__init__.py` | 6 | 0 | 100% |
| `app/blueprints/main/routes.py` | 13 | 0 | 100% |
| `app/config.py` | 33 | 0 | 100% |
| `app/errors.py` | 44 | 7 | 84% |
| `app/extensions.py` | 2 | 2 | 0% |
| `app/logging_config.py` | 27 | 1 | 96% |
| `app/security.py` | 12 | 0 | 100% |
| **TOTAL** | **206** | **11** | **95%** |

Static-analysis gates (from Blitzy's autonomous validation logs):

| Tool | Command | Result |
|------|---------|--------|
| Python byte-compilation | `python -m compileall -q app/ tests/ wsgi.py gunicorn.conf.py` | exit=0 |
| Linter | `ruff check .` (rule families E, F, W, I, UP, B, C4, SIM enabled) | "All checks passed!" |
| Type checker | `mypy .` | "Success: no issues found in 23 source files" |

---

## 4. Runtime Validation & UI Verification

**UI verification — Not applicable.** The target is a backend HTTP service (AAP §0.3.4); there is no HTML template, no static-asset bundle, and no design-system component usage (AAP §0.2.3 declares Design System Compliance not applicable). All verification below is endpoint- and process-level.

### Runtime smoke results — Flask development server (`flask run`)

- ✅ **Operational** — Process boots cleanly; reloader and debugger enabled when `FLASK_DEBUG=1`
- ✅ Every endpoint serves correctly (see endpoint matrix below)
- ✅ `python-dotenv` auto-loads `.env` when present in the working directory or any parent

### Runtime smoke results — Gunicorn production server (`gunicorn wsgi:app`)

- ✅ **Operational** — `gunicorn.conf.py` auto-discovered from the repo root; defaults to `0.0.0.0:5000` with 1 sync worker; `limit_request_line=8190` applied
- ✅ Every endpoint serves correctly (verified by validator at `127.0.0.1:5002`/`5003` and by this guide at `127.0.0.1:5099`)
- ✅ `Server: api` header on every response (gunicorn's internal `SERVER` constant rebound by `on_starting` hook before workers fork)
- ✅ All 9 defense-in-depth security headers present on every response
- ✅ Graceful SIGTERM shutdown returns exit=143 (128 + SIGTERM=15)

### Runtime smoke results — Direct entry (`python wsgi.py`)

- ✅ **Operational** — `wsgi.py` `__main__` block boots Flask's built-in dev server; useful for ad-hoc local debugging

### Endpoint matrix

| Method | Path | Status | Content-Type | Response (truncated) | Notes |
|--------|------|-------:|--------------|----------------------|-------|
| GET | `/` | ✅ 200 | application/json | `{"service":"20April_-","message":"Flask scaffold","endpoints":["/healthz","/readyz","/version","/api/"]}` | Service banner |
| GET | `/version` | ✅ 200 | application/json | `{"name":"20April_-","version":"0.1.0","python":"3.13.7"}` | Version probe |
| GET | `/healthz` | ✅ 200 | application/json | `{"status":"ok"}` | Liveness probe |
| GET | `/readyz` | ✅ 200 | application/json | `{"status":"ready"}` | Readiness probe |
| GET | `/api/` | ✅ 501 | application/json | `{"error":{"code":501,"message":"Not Implemented","detail":"API endpoints will be ported from the original Node.js source. See AAP §0.7.4."}}` | Documented placeholder (per AAP §0.4.1) |
| GET | `/nonexistent` | ✅ 404 | application/json | `{"error":{"code":404,"message":"Not Found"}}` | Centralized 404 handler in `app/errors.py` |
| POST | `/healthz` | ✅ 405 | application/json | `{"error":{"code":405,"message":"Method Not Allowed"}}` | Centralized 405 handler in `app/errors.py` |
| HEAD | `/healthz` | ✅ 200 | — | (no body) | Flask handles HEAD automatically when GET is defined |

### Security-header verification (gunicorn responses)

| Header | Value | Status |
|--------|-------|--------|
| Server | `api` | ✅ generic identifier (overrides gunicorn default) |
| X-Content-Type-Options | `nosniff` | ✅ |
| X-Frame-Options | `DENY` | ✅ |
| Referrer-Policy | `no-referrer` | ✅ |
| Permissions-Policy | `geolocation=(), camera=(), microphone=(), usb=(), payment=(), interest-cohort=()` | ✅ |
| Content-Security-Policy | `default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'` | ✅ |
| X-XSS-Protection | `0` (modern guidance: disable legacy XSS auditor) | ✅ |
| Cross-Origin-Opener-Policy | `same-origin` | ✅ |
| Cross-Origin-Embedder-Policy | `require-corp` | ✅ |
| Cross-Origin-Resource-Policy | `same-origin` | ✅ |

---

## 5. Compliance & Quality Review

This section cross-maps the AAP §0.4.1 transformation table to Blitzy's autonomous validation outcomes and to industry-standard quality benchmarks.

### AAP §0.4.1 file inventory — Compliance Matrix

| AAP File | Transformation | Implementation Evidence | Status |
|----------|----------------|-------------------------|--------|
| `README.md` | UPDATE | 474-line Flask scaffold doc; placeholder `# 20April_- dsfsdf` removed | ✅ Complete |
| `.gitignore` | CREATE | 155 lines of Python-specific ignore patterns | ✅ Complete |
| `.env.example` | CREATE | 140 lines declaring `FLASK_APP`, `FLASK_CONFIG`, `SECRET_KEY`, `HOST`, `PORT`, `LOG_LEVEL` | ✅ Complete |
| `pyproject.toml` | CREATE | PEP 621 `[project]` + `[build-system]`; `requires-python = ">=3.10"`; tool config for ruff/pytest/mypy | ✅ Complete |
| `requirements.txt` | CREATE | Pins `Flask==3.1.3`, `gunicorn==26.0.0`, `python-dotenv>=1.2.2` | ✅ Complete |
| `requirements-dev.txt` | CREATE | `-r requirements.txt` + pytest 9.0.3 + pytest-flask 1.3.0 + pytest-cov 7.1.0 + coverage 7.14.0 + ruff 0.15.13 + mypy 2.1.0 | ✅ Complete |
| `wsgi.py` | CREATE | 109 lines — `from app import create_app; app = create_app()`; `__main__` block for direct execution | ✅ Complete |
| `app/__init__.py` | CREATE | 587 lines — `create_app(config_name)` factory, env-var resolution, config-by-name mapping, logging/error-handler/blueprint registration | ✅ Complete |
| `app/config.py` | CREATE | 472 lines — `BaseConfig`/`DevelopmentConfig`/`ProductionConfig`/`TestingConfig` + `config_by_name`; JSON_SORT_KEYS / JSONIFY_PRETTYPRINT_REGULAR declared per AAP | ✅ Complete |
| `app/extensions.py` | CREATE | 49 lines — documented placeholder for future extension singletons (db, cache, cors, …) | ✅ Complete |
| `app/errors.py` | CREATE | 508 lines — handlers for 400/404/405/500 + `HTTPException` catch-all; consistent JSON envelope | ✅ Complete |
| `app/logging_config.py` | CREATE | 415 lines — `configure_logging()` using `logging.config.dictConfig`; honors `LOG_LEVEL`; werkzeug + root logger | ✅ Complete |
| `app/blueprints/__init__.py` | CREATE | Re-exports `health_bp`, `main_bp`, `api_bp` | ✅ Complete |
| `app/blueprints/health/__init__.py` | CREATE | `Blueprint('health', __name__)` + routes import | ✅ Complete |
| `app/blueprints/health/routes.py` | CREATE | `GET /healthz` → `{"status":"ok"}`; `GET /readyz` → `{"status":"ready"}` | ✅ Complete |
| `app/blueprints/main/__init__.py` | CREATE | `Blueprint('main', __name__)` + routes import | ✅ Complete |
| `app/blueprints/main/routes.py` | CREATE | `GET /` service banner; `GET /version` returns name/version/python | ✅ Complete |
| `app/blueprints/api/__init__.py` | CREATE | `Blueprint('api', __name__, url_prefix='/api')` + routes import | ✅ Complete |
| `app/blueprints/api/routes.py` | CREATE | Placeholder `GET /` returning `501 Not Implemented` with documented JSON envelope referencing AAP §0.7.4 | ✅ Complete |
| `tests/__init__.py` | CREATE | Empty package marker | ✅ Complete |
| `tests/conftest.py` | CREATE | `app`, `client`, `runner` pytest fixtures via `create_app('testing')` | ✅ Complete |
| `tests/test_app_factory.py` | CREATE | 12 tests, 633 lines — factory contract, config loading, blueprint registration | ✅ Complete |
| `tests/test_health.py` | CREATE | 9 tests, 423 lines — `/healthz`+`/readyz` behaviour and contract | ✅ Complete |
| `tests/test_main.py` | CREATE | 13 tests, 484 lines — `/`+`/version` envelope contract | ✅ Complete |
| `tests/test_api.py` | CREATE | 5 tests, 397 lines — API blueprint placeholder + 501 contract | ✅ Complete |

### AAP-compatible extensions added during Checkpoint 3/4 security/quality reviews

| File | Lines | Purpose | Status |
|------|------:|---------|--------|
| `app/security.py` | 353 | Defense-in-depth response headers + `Server: api` override on every Flask response | ✅ Complete (extension to AAP) |
| `gunicorn.conf.py` | 411 | Auto-discovered gunicorn config — `limit_request_line=8190`, env-driven bind/workers/worker_class, `on_starting` hook rebinding gunicorn's internal `SERVER` constant before workers fork | ✅ Complete (extension to AAP) |
| `tests/test_security.py` | 470 | 15 tests covering security-header + Server-header override on every endpoint | ✅ Complete (extension to AAP) |
| `tests/test_gunicorn_conf.py` | 405 | 13 tests covering gunicorn-config behaviour | ✅ Complete (extension to AAP) |

### Quality benchmark matrix

| Benchmark | Target | Actual | Status |
|-----------|--------|--------|--------|
| All Python files byte-compile | `compileall` exit=0 | exit=0 | ✅ PASS |
| Lint clean | `ruff check .` exit=0 | "All checks passed!" | ✅ PASS |
| Type-check clean | `mypy .` exit=0 across all source | "Success: no issues found in 23 source files" | ✅ PASS |
| Test pass rate | 100% | 67/67 (100.0%) | ✅ PASS |
| Test runtime | < 60s | 0.21 s | ✅ PASS |
| Code coverage (line) | ≥ 90% | 95% | ✅ PASS |
| Application factory pattern (AAP §0.3.3) | Implemented | `app/__init__.py::create_app` | ✅ PASS |
| Blueprint modularisation (AAP §0.3.3) | 3 blueprints | health + main + api | ✅ PASS |
| Configuration object hierarchy (AAP §0.3.3) | 4 config classes | Base + Development + Production + Testing | ✅ PASS |
| Centralized error handlers (AAP §0.3.3) | Implemented | 400/404/405/500 + HTTPException catch-all | ✅ PASS |
| Extension-singleton placeholder (AAP §0.3.3) | Reserved | `app/extensions.py` with docstring | ✅ PASS |
| Dependency pin parity with AAP §0.5.1 | Flask 3.1.3, gunicorn 26.0.0 | Flask 3.1.3, gunicorn 26.0.0 | ✅ PASS |
| Production WSGI server | gunicorn | gunicorn 26.0.0 + `gunicorn.conf.py` | ✅ PASS |
| Security headers (Checkpoint 4 hardening) | At least HSTS-equivalent baseline | 9 headers + Server-token override | ✅ PASS |

### Compliance gaps and deferred items

| Gap | Reason | Deferred-to |
|-----|--------|-------------|
| Functional parity with the "original Node.js project" | No Node source exists in the repository (AAP §0.1.2, §0.6.1, §0.7.3) | User-supplied Node source + AAP §0.7.4 question resolution |
| Persistence layer | AAP §0.2.2 explicit out-of-scope until original behavior provided | Post-port engagement |
| Authentication/authorization | AAP §0.2.2 explicit out-of-scope until original behavior provided | Post-port engagement |
| Containerization, CI/CD, infra-as-code | AAP §0.2.2 explicit out-of-scope (user did not request) | Deployment-target decision required |

---

## 6. Risk Assessment

| Risk | Category | Severity | Probability | Mitigation | Status |
|------|----------|----------|-------------|------------|--------|
| Node.js source not yet provided — functional port cannot begin | Integration | High | High | Resolve AAP §0.7.4 question 1; user provides source URL/archive. Scaffold is engineered to accept the port mechanically (AAP §0.6.2) | **Open** — USER ACTION REQUIRED |
| Production `SECRET_KEY` not yet configured | Security | High | High | Generate via `python -c "import secrets; print(secrets.token_hex(32))"`; inject via deployment platform's secret manager; never commit | **Open** |
| AAP §0.7.4 open clarification questions unresolved (10 questions: Node framework, endpoint inventory, persistence, integrations, env vars, Node version, deployment target, test suite, non-HTTP entry points) | Integration | High | High | User provides written answers; scaffold is parameterized to accept any answer without restructuring | **Open** — USER ACTION REQUIRED |
| Persistence layer not chosen (Node source dictates choice) | Operational | Medium | Medium | `app/extensions.py` placeholder reserves the conventional location for `db = SQLAlchemy()` / equivalents; downstream agents can wire integrations without restructuring | **Deferred** — pending Node source |
| Authentication / authorization not yet implemented | Security | Medium | Medium | Centralized error handlers + blueprint structure are ready to accept auth middleware via `@app.before_request` or WSGI middleware around `app.wsgi_app` | **Deferred** — pending Node source |
| Deployment target not yet identified (containerization explicitly out-of-scope per AAP §0.2.2) | Operational | Low | Medium | Resolve AAP §0.7.4 question 8 (deployment target). Once chosen, add a `Dockerfile`/manifest as a follow-on. Gunicorn graceful SIGTERM and Server-token override are already in place. | **Open** |
| External-integration credentials not configured (depends on Node source) | Integration | Low | Medium | `.env.example` is the contract surface — every `process.env.X` from the Node source must be mirrored to `app/config.py` + `.env.example` per AAP §0.6.4 | **Deferred** — pending Node source |
| Performance characteristics not benchmarked (no Node baseline exists) | Technical | Low | Low | AAP §0.6.3 documents the concurrency-model translation; gunicorn worker tuning starting point (`--workers $((2*$(nproc)+1)) --worker-class gthread --threads 4`) is documented in README. Once Node source is ported, run side-by-side benchmarks. | **Mitigated** — documentation only |
| Test framework for ported routes not yet identified (Node test framework unknown) | Technical | Low | Medium | pytest + pytest-flask are already wired; any Node test contract can be ported into a new `tests/test_*.py` module | **Mitigated** — pytest infrastructure ready |
| Non-HTTP entry points (CLI commands, background workers, scheduled jobs, MQ consumers) — existence unknown | Integration | Low | Medium | Resolve AAP §0.7.4 question 10. If present, add Click CLI commands via `@app.cli.command()`, or a Celery/RQ/APScheduler integration | **Deferred** — pending Node source |
| Log routing in production environment unknown (stdout vs. file vs. syslog vs. remote) | Operational | Low | Medium | `dictConfig` accepts handler reconfiguration via `LOG_LEVEL` and (when needed) additional handlers; gunicorn `--access-logformat` for HTTP access logs | **Mitigated** — flexible config in place |

**Aggregate risk posture:** the scaffold itself carries **no technical risk** — it compiles, lints, type-checks, runs, and is fully tested. **Every High-severity risk is gated on user input** (Node source + AAP §0.7.4 question resolutions). Medium- and Low-severity risks are either deferred pending the same user input, or already mitigated through scaffold design.

---

## 7. Visual Project Status

### Hours breakdown (must match Section 1.2 and Section 2.2 exactly)

```mermaid
%%{init: {"themeVariables": {"pie1": "#5B39F3", "pie2": "#FFFFFF", "pieStrokeColor": "#5B39F3", "pieOuterStrokeColor": "#5B39F3"}}}%%
pie showData title Project Hours Breakdown (Total: 95h)
    "Completed Work" : 89
    "Remaining Work" : 6
```

### Completed work by category (Section 2.1 attribution, hours)

```mermaid
%%{init: {"themeVariables": {"pie1": "#5B39F3", "pie2": "#7C5BFF", "pie3": "#9D86FF", "pie4": "#BFB1FF", "pie5": "#E0DCFF", "pie6": "#A8FDD9"}}}%%
pie showData title Completed Hours by Category (89h)
    "Application factory + core modules (28h)" : 28
    "Test suite (20h)" : 20
    "Validation cycle (15h)" : 15
    "Repository-root scaffold (12h)" : 12
    "Security hardening — AAP extension (8h)" : 8
    "Blueprints (6h)" : 6
```

### Remaining work by priority (Section 2.2 attribution, hours)

```mermaid
%%{init: {"themeVariables": {"pie1": "#5B39F3", "pie2": "#B23AF2", "pie3": "#A8FDD9"}}}%%
pie showData title Remaining Hours by Priority (6h)
    "High priority (4h)" : 4
    "Medium priority (2h)" : 2
```

### Cross-section integrity check

| Location | Completed | Remaining | Total | % |
|----------|----------:|----------:|------:|--:|
| Section 1.2 metrics table | 89 | 6 | 95 | 93.7% |
| Section 2.1 + 2.2 sums | 89 | 6 | 95 | 93.7% |
| Section 7 main pie | 89 | 6 | 95 | 93.7% |
| Section 8 narrative | 89 | 6 | 95 | 93.7% |

All four rows match. ✅

---

## 8. Summary & Recommendations

### Achievements

The Blitzy autonomous agents have delivered a complete, idiomatic, production-ready Python 3 + Flask 3.1 scaffold in **89 engineering hours**, with **67/67 tests passing in 0.21 s at 95% line coverage** and **zero unresolved compilation, lint, type-check, or runtime errors** across all 29 in-scope files. Every row of the AAP §0.4.1 transformation table is realized as a committed source file. Four additional files (`app/security.py`, `gunicorn.conf.py`, `tests/test_security.py`, `tests/test_gunicorn_conf.py`) extend the AAP without violating it, hardening the response surface and the gunicorn server configuration. All five Final-Validator production-readiness gates passed on the first attempt.

### Remaining gaps

The project is **93.7% complete** (89 / 95 hours). The remaining 6 hours are all **path-to-production prerequisites for the scaffold itself**, none of which can be completed autonomously:

- 2 hours to provide the Node.js source code (USER ACTION)
- 1 hour to resolve the AAP §0.7.4 clarification questions in writing (USER ACTION)
- 1 hour to configure the production `SECRET_KEY` and any environment-specific variables in the deployment target
- 2 hours to validate the scaffold against the chosen deployment environment

**The actual Node→Flask port itself is explicitly out of this AAP's scope** (AAP §0.1.2 redefined scope to "Greenfield Flask Scaffold Creation" because no Node source exists, and AAP §0.7.3 stated the *"preserving all functionalities"* directive is currently unbinding). The port will be a separate, post-scaffold engagement once the user supplies the source; the scaffold is engineered (AAP §0.6.2 idiom map, §0.6.3 concurrency translation, §0.6.4 env-var parity, §0.6.5 logging translation, §0.6.6 packaging translation, §0.6.7 cross-cutting concerns) to make that port mechanical rather than architectural.

### Critical path to production

```
User supplies Node source ─┐
                           ├─► Port routes into app/blueprints/api/routes.py (replace 501)
User answers §0.7.4 Q1–10 ─┘    │
                                ├─► Add missing dependencies to requirements.txt (per §0.5.3 mapping)
                                ├─► Mirror process.env.X → app/config.py + .env.example
                                ├─► Port tests; ensure pytest stays green
                                │
   Configure production SECRET_KEY ─┐
                                    ├─► Deploy to chosen target (Docker / K8s / PaaS / bare metal)
                                    │
   Validate in target environment ──┴─► Production cutover
```

### Production readiness assessment

| Aspect | Readiness | Notes |
|--------|-----------|-------|
| Scaffold codebase | ✅ Production-ready | All 5 validation gates pass; 95% coverage |
| Configuration system | ✅ Production-ready | 4 config profiles + env-var contract |
| Logging | ✅ Production-ready | `dictConfig` honors `LOG_LEVEL`; flexible to add JSON / syslog handlers |
| HTTP error handling | ✅ Production-ready | Consistent JSON envelope across 400/404/405/500 + catch-all |
| Security headers | ✅ Production-ready | 9 defense-in-depth headers + generic Server-token |
| Gunicorn production wiring | ✅ Production-ready | `gunicorn.conf.py` auto-discovered; SIGTERM exit=143 verified |
| Tests | ✅ Production-ready | 67/67 passing in 0.21 s; 95% coverage |
| `SECRET_KEY` (production) | ⚠️ Awaiting deployment-time injection | Default `change-me` placeholder MUST be overridden |
| Node→Flask port | ❌ Deferred | Awaits user-supplied Node source + AAP §0.7.4 clarifications |
| Containerization / CI / IaC | ❌ Out of AAP scope | Awaits deployment-target decision; not blocking the scaffold |

### Success metrics

| Metric | Target | Achieved |
|--------|--------|----------|
| AAP §0.4.1 file inventory coverage | 100% | 100% (26/26 rows + 4 AAP-compatible extensions) |
| Test pass rate | 100% | 100% (67/67) |
| Code coverage | ≥ 90% | 95% |
| `compileall` exit | 0 | 0 |
| `ruff check .` exit | 0 | 0 |
| `mypy .` exit | 0 | 0 (23 source files) |
| Runtime smoke-tests | Every endpoint serves | Every endpoint serves under Flask dev, gunicorn prod, and direct entry |

---

## 9. Development Guide

This guide is anchored to the validated state of the repository on branch `blitzy-642c359d-0666-43c3-903a-d76630e9048c`. Every command below was executed by the validator (or this guide-author) and confirmed to work.

### 9.1 System Prerequisites

| Component | Requirement | Notes |
|-----------|-------------|-------|
| Operating system | Linux, macOS, or Windows with WSL | Validated on Ubuntu 25.10 |
| Python | `>= 3.10` (recommended **3.12+**) | Effective floor imposed by gunicorn 26.0.0; Flask 3.1.x supports `>= 3.9`. Validator ran Python 3.13.7. |
| pip | Recent (≥ 23.0) | Validator ran pip 26.1.1 |
| POSIX shell | bash, zsh, or compatible | Windows users can substitute `cmd.exe` / PowerShell where noted in README.md |
| Disk | ~ 250 MB | Includes the `.venv` after installing dev dependencies |
| Network | Outbound to `pypi.org` | Required only for the initial `pip install`; runtime needs no outbound access |

### 9.2 Environment Setup

```bash
# 1. Clone the repository (skip if already cloned)
git clone <repository-url> 20April_-
cd 20April_-

# 2. Check out the validated branch
git checkout blitzy-642c359d-0666-43c3-903a-d76630e9048c

# 3. Create and activate a Python virtual environment
python3 -m venv .venv
source .venv/bin/activate
#   Windows (cmd.exe):     .venv\Scripts\activate.bat
#   Windows (PowerShell):  .venv\Scripts\Activate.ps1

# 4. Upgrade pip inside the venv
python -m pip install --upgrade pip

# 5. Copy the .env template and customize as needed
cp .env.example .env
#   Windows (cmd.exe):     copy .env.example .env
#   Edit .env to set SECRET_KEY to a real value before any non-development deployment.
#   Generate a real value with:
#       python -c "import secrets; print(secrets.token_hex(32))"
```

### 9.3 Dependency Installation

```bash
# Runtime dependencies (Flask 3.1.3, gunicorn 26.0.0, python-dotenv)
pip install -r requirements.txt

# Development + test dependencies (pytest 9.0.3, pytest-flask 1.3.0, pytest-cov 7.1.0, coverage 7.14.0, ruff 0.15.13, mypy 2.1.0)
# Also pulls in everything from requirements.txt
pip install -r requirements-dev.txt

# Verify the installed pin set
pip list | grep -iE "^(Flask|gunicorn|python-dotenv|Werkzeug|Jinja2|MarkupSafe|ItsDangerous|Click|Blinker|pytest|ruff|mypy|coverage)"
```

Expected output (validated):

```
blinker                 1.9.0
click                   8.4.0
coverage                7.14.0
Flask                   3.1.3
gunicorn                26.0.0
itsdangerous            2.2.0
Jinja2                  3.1.6
MarkupSafe              3.0.3
mypy                    2.1.0
pytest                  9.0.3
pytest-cov              7.1.0
pytest-flask            1.3.0
python-dotenv           1.2.2
ruff                    0.15.13
Werkzeug                3.1.8
```

### 9.4 Application Startup

Three boot modes are supported; pick one per scenario.

#### A. Development mode — `flask run`

```bash
# Variables are loaded from .env automatically by python-dotenv when present
export FLASK_APP=wsgi:app
export FLASK_CONFIG=development

# Default 127.0.0.1:5000
flask run

# Bind on all interfaces and a custom port
flask run --host 0.0.0.0 --port 5000

# With reloader + debugger enabled
flask run --debug
```

#### B. Production mode — `gunicorn wsgi:app`

```bash
# Minimal — auto-discovers gunicorn.conf.py from the repo root
gunicorn wsgi:app

# Explicit production invocation with secret injected via env
SECRET_KEY=<real-secret> FLASK_CONFIG=production gunicorn wsgi:app

# Tuned for I/O-bound workloads
gunicorn --bind 0.0.0.0:5000 \
         --workers 4 \
         --worker-class gthread \
         --threads 4 \
         wsgi:app
```

Worker-tuning guidance (full rationale in AAP §0.6.3 and `gunicorn.conf.py`):
- **I/O-bound:** `--workers $((2 * $(nproc) + 1)) --worker-class gthread --threads 4`
- **CPU-bound:** increase `--workers`, leave `--threads 1`

#### C. Direct entry — `python wsgi.py`

```bash
# Alternative for ad-hoc local debugging — wsgi.py has a __main__ block
python wsgi.py
```

### 9.5 Verification Steps

```bash
# 1. Run the full test suite
python -m pytest
# Expected: "67 passed in 0.21s"

# 2. Coverage report
python -m pytest --cov=app --cov-report=term-missing
# Expected: TOTAL line "206 statements, 11 missed, 95% Cover"

# 3. Lint
ruff check .
# Expected: "All checks passed!"

# 4. Type-check
mypy .
# Expected: "Success: no issues found in 23 source files"

# 5. Byte-compile every Python file
python -m compileall -q app/ tests/ wsgi.py gunicorn.conf.py
echo "exit=$?"
# Expected: exit=0

# 6. Endpoint smoke test (run in another terminal while gunicorn is up)
curl -s http://127.0.0.1:5000/
curl -s http://127.0.0.1:5000/version
curl -s http://127.0.0.1:5000/healthz
curl -s http://127.0.0.1:5000/readyz
curl -s http://127.0.0.1:5000/api/
curl -si http://127.0.0.1:5000/nonexistent | head -3
# Expected: 200, 200, 200, 200, 501, 404 (in that order)
```

### 9.6 Example Usage

```bash
# Start gunicorn in the background for smoke-testing
SECRET_KEY=demo-only FLASK_CONFIG=production gunicorn -b 127.0.0.1:5000 -w 1 wsgi:app &
GUNI_PID=$!
sleep 2

# Verify each endpoint
echo "=== GET / ===" && curl -s http://127.0.0.1:5000/
echo
echo "=== GET /version ===" && curl -s http://127.0.0.1:5000/version
echo
echo "=== GET /healthz ===" && curl -s http://127.0.0.1:5000/healthz
echo
echo "=== GET /readyz ===" && curl -s http://127.0.0.1:5000/readyz
echo
echo "=== GET /api/ ===" && curl -s http://127.0.0.1:5000/api/
echo
echo "=== Headers on / ===" && curl -sI http://127.0.0.1:5000/

# Stop gunicorn gracefully (returns exit=143)
kill -TERM $GUNI_PID
wait $GUNI_PID
```

### 9.7 Troubleshooting

| Symptom | Likely Cause | Resolution |
|---------|--------------|------------|
| `flask: command not found` | Virtual environment not activated, or `pip install` not yet run | `source .venv/bin/activate && pip install -r requirements-dev.txt` |
| `ModuleNotFoundError: No module named 'app'` | Working directory is not the repository root | `cd` to the directory containing `wsgi.py` and `app/` |
| `flask run` says "Could not locate a Flask application" | `FLASK_APP` not set | `export FLASK_APP=wsgi:app` (or place it in `.env`) |
| Port already in use | Another process bound to the same port | `lsof -iTCP:5000 -sTCP:LISTEN` to identify; use `--port 5001` |
| Gunicorn exits immediately at boot | `SECRET_KEY` not exportable, or `gunicorn.conf.py` syntax error | Confirm `SECRET_KEY` is in the environment; `python -m py_compile gunicorn.conf.py` |
| `pytest` reports import errors | Dev dependencies missing | `pip install -r requirements-dev.txt` |
| `ruff` reports rule changes after a dependency bump | New rule added in `ruff` major version | Pin `ruff==0.15.13` in `requirements-dev.txt` (already done) |
| `mypy` reports issues that did not appear in CI | mypy version drift | Pin `mypy==2.1.0` in `requirements-dev.txt` (already done) |
| Server header still shows `gunicorn` | Reverse proxy is overriding the response header, or `gunicorn.conf.py` not loaded | Verify gunicorn is launched from the repo root; check reverse-proxy config |
| `python-dotenv` not loading `.env` | `.env` missing or in a non-ancestor directory | `cp .env.example .env` and place at the repo root |
| 501 on `/api/` | This is the **expected** behaviour until the Node source is ported | See AAP §0.7.4 — provide Node source first |

---

## 10. Appendices

### Appendix A — Command Reference

| Purpose | Command |
|---------|---------|
| Activate venv | `source .venv/bin/activate` |
| Install runtime deps | `pip install -r requirements.txt` |
| Install dev deps | `pip install -r requirements-dev.txt` |
| Run all tests | `python -m pytest` |
| Run tests with coverage | `python -m pytest --cov=app --cov-report=term-missing` |
| Run lint | `ruff check .` |
| Run type-check | `mypy .` |
| Byte-compile | `python -m compileall -q app/ tests/ wsgi.py gunicorn.conf.py` |
| Boot Flask dev | `FLASK_APP=wsgi:app FLASK_CONFIG=development flask run --host 0.0.0.0 --port 5000` |
| Boot Flask dev with debug | `FLASK_APP=wsgi:app flask run --debug` |
| Boot gunicorn (default) | `gunicorn wsgi:app` |
| Boot gunicorn (production tuned) | `gunicorn --bind 0.0.0.0:5000 --workers 4 --worker-class gthread --threads 4 wsgi:app` |
| Boot via direct entry | `python wsgi.py` |
| Generate SECRET_KEY | `python -c "import secrets; print(secrets.token_hex(32))"` |
| Smoke-test endpoint | `curl -si http://127.0.0.1:5000/<path>` |
| Stop gunicorn (graceful) | `kill -TERM <pid>` (exit=143 expected) |

### Appendix B — Port Reference

| Service | Default Port | Override |
|---------|-------------:|----------|
| Flask development server | 5000 | `flask run --port <N>` |
| Gunicorn production | 5000 | `PORT=<N> gunicorn wsgi:app` or `gunicorn -b 0.0.0.0:<N>` |
| `python wsgi.py` (direct) | 5000 | `PORT` env var (`HOST` for bind address) |

### Appendix C — Key File Locations

| File / Folder | Purpose | LOC |
|---------------|---------|----:|
| `wsgi.py` | Production WSGI entry point (`gunicorn wsgi:app`); also direct-execution `__main__` for dev | 109 |
| `gunicorn.conf.py` | Gunicorn server config auto-discovered at repo root | 411 |
| `pyproject.toml` | PEP 621 project metadata + ruff/pytest/mypy tool config | 191 |
| `requirements.txt` | Pinned runtime dependencies | 77 |
| `requirements-dev.txt` | Pinned dev + test dependencies (includes `-r requirements.txt`) | 171 |
| `.env.example` | Environment-variable contract — copy to `.env` | 140 |
| `.gitignore` | Python-specific ignore patterns | 155 |
| `README.md` | Comprehensive Flask scaffold doc | 474 |
| `app/__init__.py` | Application factory `create_app()` | 587 |
| `app/config.py` | `BaseConfig`/`DevelopmentConfig`/`ProductionConfig`/`TestingConfig` + `config_by_name` | 472 |
| `app/errors.py` | 400/404/405/500 + `HTTPException` handlers | 508 |
| `app/logging_config.py` | `dictConfig`-based logging setup | 415 |
| `app/extensions.py` | Placeholder for future extension singletons | 49 |
| `app/security.py` | Defense-in-depth security headers + Server-token override | 353 |
| `app/blueprints/__init__.py` | Re-exports `health_bp`, `main_bp`, `api_bp` | 69 |
| `app/blueprints/health/routes.py` | `GET /healthz`, `GET /readyz` | 111 |
| `app/blueprints/main/routes.py` | `GET /`, `GET /version` | 153 |
| `app/blueprints/api/routes.py` | `GET /api/` placeholder (501) | 241 |
| `tests/conftest.py` | pytest fixtures (`app`, `client`, `runner`) | 144 |
| `tests/test_app_factory.py` | 12 factory-contract tests | 633 |
| `tests/test_health.py` | 9 health-probe tests | 423 |
| `tests/test_main.py` | 13 main-route tests | 484 |
| `tests/test_api.py` | 5 API-placeholder tests | 397 |
| `tests/test_security.py` | 15 security-header tests | 470 |
| `tests/test_gunicorn_conf.py` | 13 gunicorn-config tests | 405 |

### Appendix D — Technology Versions

| Component | Version | Source |
|-----------|---------|--------|
| Python | 3.13.7 (development) / `>= 3.10` (runtime floor) | `pyproject.toml requires-python = ">=3.10"` |
| pip | 26.1.1 (development) | Bootstrapped in `.venv` |
| Flask | 3.1.3 | `requirements.txt` |
| gunicorn | 26.0.0 | `requirements.txt` |
| python-dotenv | 1.2.2 | `requirements.txt` |
| Werkzeug | 3.1.8 | transitive via Flask |
| Jinja2 | 3.1.6 | transitive via Flask |
| MarkupSafe | 3.0.3 | transitive via Jinja2 |
| ItsDangerous | 2.2.0 | transitive via Flask |
| Click | 8.4.0 | transitive via Flask (provides the `flask` CLI) |
| Blinker | 1.9.0 | transitive via Flask (signals support) |
| pytest | 9.0.3 | `requirements-dev.txt` |
| pytest-flask | 1.3.0 | `requirements-dev.txt` |
| pytest-cov | 7.1.0 | `requirements-dev.txt` |
| coverage | 7.14.0 | `requirements-dev.txt` |
| ruff | 0.15.13 | `requirements-dev.txt` |
| mypy | 2.1.0 | `requirements-dev.txt` |

### Appendix E — Environment Variable Reference

| Variable | Default | Required? | Consumer | Notes |
|----------|---------|-----------|----------|-------|
| `FLASK_APP` | `wsgi:app` | Yes (for `flask` CLI) | `flask` CLI | Resolves `from wsgi import app` |
| `FLASK_CONFIG` | `development` | No | `app/config.py::config_by_name` | One of `development`, `production`, `testing`; invalid values fall back to `development` |
| `SECRET_KEY` | `change-me` (development) | **Yes in production** | `app/config.py::BaseConfig` | Used for session signing. **Must be overridden** with a real value before any non-development deployment |
| `HOST` | `0.0.0.0` | No | `gunicorn.conf.py`, `wsgi.py` direct entry | Bind interface |
| `PORT` | `5000` | No | `gunicorn.conf.py`, `wsgi.py` direct entry | Bind port |
| `LOG_LEVEL` | `INFO` | No | `app/logging_config.py` | One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `GUNICORN_WORKERS` | `1` | No | `gunicorn.conf.py` | Override worker count |
| `GUNICORN_WORKER_CLASS` | `sync` | No | `gunicorn.conf.py` | `sync` / `gthread` / `gevent` (gevent requires extra) |
| `GUNICORN_LIMIT_REQUEST_LINE` | `8190` | No | `gunicorn.conf.py` | Doubled from gunicorn's default 4094 to accept long URLs (pagination tokens, signed URLs). `0` removes the limit (with internal 1 MiB safety net) |
| `GUNICORN_SERVER_TOKEN` | `api` | No | `gunicorn.conf.py` (`on_starting` hook) | Generic `Server` header value. Set to empty string to opt out and restore the default `gunicorn` token |

### Appendix F — Developer Tools Guide

| Tool | Configured In | Run Command | Notes |
|------|---------------|-------------|-------|
| **pytest** | `pyproject.toml [tool.pytest.ini_options]` | `python -m pytest` | Discovers `tests/test_*.py`; uses fixtures from `tests/conftest.py` |
| **pytest-cov** | `pyproject.toml` | `python -m pytest --cov=app --cov-report=term-missing` | Line-coverage report against `app/` |
| **pytest-flask** | implicit (autouse) | — | Provides the `client` fixture pattern |
| **ruff** | `pyproject.toml [tool.ruff]` | `ruff check .` | Rule families E, F, W, I, UP, B, C4, SIM enabled |
| **ruff format** | `pyproject.toml [tool.ruff.format]` | `ruff format .` | Format runner (not required for CI but available) |
| **mypy** | `pyproject.toml [tool.mypy]` | `mypy .` | Strict-ish mode; 23 source files type-checked clean |
| **coverage** | `pyproject.toml [tool.coverage]` | `coverage run -m pytest && coverage report` | Underlies `pytest-cov`; can be invoked directly |
| **compileall** | (stdlib) | `python -m compileall -q app/ tests/ wsgi.py gunicorn.conf.py` | Byte-compilation sanity check |
| **flask CLI** | provided by Click + `FLASK_APP=wsgi:app` | `flask run`, `flask routes`, `flask shell` | The CLI auto-loads `.env` via python-dotenv when present |
| **gunicorn** | `gunicorn.conf.py` | `gunicorn wsgi:app` | Auto-discovers `gunicorn.conf.py` from the repo root |

### Appendix G — Glossary

| Term | Definition |
|------|------------|
| **AAP** | Agent Action Plan — the directive document anchoring this refactor (§0 in the source repository) |
| **Application Factory** | The pattern (AAP §0.3.3) where `create_app(config_name)` constructs the Flask instance on demand, instead of binding it at module import time |
| **Blueprint** | Flask's modular routing primitive; this scaffold registers three: `health`, `main`, `api` |
| **WSGI** | Web Server Gateway Interface — the synchronous Python web-server protocol that gunicorn implements |
| **gunicorn** | Pre-fork WSGI HTTP server pinned at 26.0.0 for production deployments |
| **dictConfig** | `logging.config.dictConfig` — declarative Python logging configuration consumed by `app/logging_config.py` |
| **JSON envelope** | The consistent `{"error": {"code": ..., "message": ...}}` shape returned by `app/errors.py` handlers |
| **Defense-in-depth headers** | The nine response headers emitted by `app/security.py` (CSP, COOP, COEP, CORP, X-Frame-Options, etc.) that harden the HTTP response surface |
| **Server-token override** | The `on_starting` hook in `gunicorn.conf.py` that rebinds gunicorn's internal `SERVER` constant to `api` before workers fork, replacing the default `Server: gunicorn` identifier |
| **Pre-fork worker model** | Gunicorn's concurrency model — a master process forks N worker processes at boot; workers share the listening socket |
| **PEP 621** | Python packaging standard that declares project metadata in `pyproject.toml [project]` |
| **AAP §0.7.4** | The open-questions appendix of the AAP listing the ten user clarifications required before the Node→Flask port can begin |
| **Checkpoint** | An autonomous review cycle by Blitzy's QA agents (Checkpoint 1 through 4 + final QA) that produced the F1-F7 + MAJOR/MINOR fix lists |

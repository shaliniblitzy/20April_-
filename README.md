# 20April_- — Flask 3.1 Scaffold

A Python 3 + Flask scaffold engineered so that any Node.js HTTP server can be
ported into it without architectural rework.


## Status

This section is intentionally transparent about a precondition gap discovered
during repository inspection — see AAP §0.6.1 for the full record.

- The repository currently contains a **Flask scaffold**, not a port of an
  existing Node.js project.
- The original user directive was:
  *"Can you rewrite this node.js server in python 3 using flask, preserving all
  functionalities of the original project?"*
- **No Node.js source code was found in the repository.** The two commits on
  record prior to this scaffold (HEAD `c238fc2` and predecessor `8b3768b`)
  both touched only `README.md`; no `package.json`, no `node_modules/`, and no
  `*.js` / `*.ts` / `*.mjs` / `*.cjs` files were present on any branch.
- Functional parity with "the original project" therefore **cannot be claimed**
  until the Node.js source is supplied. See the [Open Questions](#open-questions)
  section below for the clarification items that must be resolved before
  porting can begin.
- The scaffold below is engineered to accommodate the future port without
  restructuring: an application-factory pattern (`app/__init__.py::create_app`),
  blueprint modularisation, layered configuration, centralised error handling,
  an extension-singleton placeholder (`app/extensions.py`) for future
  integrations such as a database client or cache, and `dictConfig`-based
  logging are all wired in advance.


## Requirements

- **Python:** `>= 3.10` (effective minimum imposed by gunicorn 26.0.0; Flask
  3.1.x itself supports Python `>= 3.9`). Recommended: **Python 3.12**.
- **pip:** any recent version capable of installing from `requirements.txt`.
- **POSIX shell** (bash, zsh, or compatible) for running the commands shown
  in this README. Windows users can substitute the documented PowerShell /
  `cmd.exe` equivalents where noted.


## Project Layout

The target repository layout after the scaffold is generated is shown below
(see AAP §0.3.1 for the authoritative tree). Annotations follow `#`.

```text
20April_-/
├── README.md                              # this file
├── .gitignore                             # Python-specific ignore patterns
├── .env.example                           # environment-variable contract template
├── pyproject.toml                         # PEP 621 project metadata + tool config
├── requirements.txt                       # pinned runtime dependencies
├── requirements-dev.txt                   # pinned dev/test dependencies
├── wsgi.py                                # gunicorn entry point: `gunicorn wsgi:app`
├── app/
│   ├── __init__.py                        # application factory: create_app()
│   ├── config.py                          # BaseConfig + Development/Production/Testing
│   ├── extensions.py                      # extension-singleton placeholder
│   ├── errors.py                          # centralised HTTP error handlers
│   ├── logging_config.py                  # dictConfig-based logging setup
│   └── blueprints/
│       ├── __init__.py                    # re-exports blueprint objects
│       ├── health/
│       │   ├── __init__.py                # Blueprint('health', __name__)
│       │   └── routes.py                  # GET /healthz, GET /readyz
│       ├── main/
│       │   ├── __init__.py                # Blueprint('main', __name__)
│       │   └── routes.py                  # GET /, GET /version
│       └── api/
│           ├── __init__.py                # Blueprint('api', __name__, url_prefix='/api')
│           └── routes.py                  # placeholder API surface (ported routes land here)
└── tests/
    ├── __init__.py
    ├── conftest.py                        # pytest fixtures: app, client, runner
    ├── test_app_factory.py
    ├── test_health.py
    ├── test_main.py
    └── test_api.py
```


## Installation

The commands below assume a POSIX shell. Windows equivalents are noted where
they differ.

```bash
# 1. Clone the repository (skip if you already have it).
git clone <repository-url> 20April_- && cd 20April_-

# 2. Create and activate a virtual environment.
python -m venv .venv
source .venv/bin/activate
#   Windows (cmd.exe):       .venv\Scripts\activate.bat
#   Windows (PowerShell):    .venv\Scripts\Activate.ps1

# 3. Upgrade pip inside the venv.
python -m pip install --upgrade pip

# 4. Install runtime dependencies.
pip install -r requirements.txt

# 5. (Optional) Install development & test dependencies.
pip install -r requirements-dev.txt

# 6. Copy the environment-variable template and customise values for your
#    machine. NEVER commit the resulting `.env` file (it is git-ignored).
cp .env.example .env
#   Windows (cmd.exe):       copy .env.example .env
```

Edit `.env` to set `SECRET_KEY` to a real value before running the app in any
non-development context. Generate one with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```


## Running

### Development mode (`flask run`)

The development server is intended for local development only — it does not
provide the stability, security, or performance characteristics of a
production WSGI server. The reloader and the interactive debugger are
enabled by default when `--debug` is passed (or `FLASK_DEBUG=1` is set), and
**multithreading is enabled by default**: `flask run` accepts a
`--with-threads / --without-threads` flag whose default in Flask 3.1.x is
`--with-threads`. Supply `--without-threads` only when single-threaded
behaviour is required.

`FLASK_APP=wsgi:app` makes the `flask` CLI import `wsgi.py`, which in turn
calls `create_app()` exported from `app/__init__.py`.
`python-dotenv` is loaded automatically by the `flask` CLI when `.env` is
present in the current directory or any parent directory, so the variables
documented in [Configuration](#configuration) take effect without an explicit
`export`.

```bash
# Variables typically come from .env, but can also be exported inline:
export FLASK_APP=wsgi:app
export FLASK_CONFIG=development

flask run --host=0.0.0.0 --port=5000
```

### Production mode (gunicorn)

Use gunicorn for production deployments — it is the WSGI server pinned in
`requirements.txt` and is the recommended production runner for Flask.

```bash
# Minimal invocation.
gunicorn wsgi:app --bind 0.0.0.0:5000
```

Worker tuning guidance (see AAP §0.6.3 for the full concurrency-model
translation):

- **I/O-bound workloads** (database queries, outbound HTTP calls, blocking
  network I/O): use multiple workers and multiple threads per worker.

  ```bash
  gunicorn --workers $((2 * $(nproc) + 1)) \
           --worker-class gthread \
           --threads 4 \
           --bind 0.0.0.0:5000 \
           wsgi:app
  ```

- **CPU-bound workloads** (heavy computation, serialisation, cryptography):
  increase `--workers`, keep `--threads` low (typically `1`), and prefer the
  default `sync` worker class.

  ```bash
  gunicorn --workers $((2 * $(nproc) + 1)) \
           --threads 1 \
           --bind 0.0.0.0:5000 \
           wsgi:app
  ```

- **Genuinely async code paths** (e.g., when porting Node `async`/`await`
  endpoints): install Flask with the `async` extra and use `async def` view
  functions. The underlying request-handling thread remains synchronous from
  WSGI's perspective, but coroutine bodies can `await` cleanly.


## Configuration

All runtime configuration is driven by environment variables. The single
authoritative declaration of every variable lives in `.env.example`; copy it
to `.env` for local development.

The table below lists every variable with **two** columns to keep template
and runtime semantics distinct:

- **`.env.example` value** — the literal string committed in `.env.example`
  and copied into a developer `.env` by `cp .env.example .env`. These are
  placeholder defaults intended for local development only.
- **Code default (when variable is unset)** — the value `app/config.py` /
  `app/logging_config.py` falls back to if the environment variable is
  absent from `os.environ` at process startup. This is what runs in
  production when the deployment platform does not export the variable.

| Variable       | `.env.example` value | Code default (when variable is unset) | Purpose                                                                                |
| -------------- | -------------------- | ------------------------------------- | -------------------------------------------------------------------------------------- |
| `FLASK_APP`    | `wsgi:app`           | n/a (consumed by `flask` CLI only)    | Application import string used by the `flask` CLI.                                     |
| `FLASK_CONFIG` | `development`        | `development` (via the `default` alias in `app/config.py::config_by_name`) | Selects `DevelopmentConfig` / `ProductionConfig` / `TestingConfig`.                    |
| `SECRET_KEY`   | `change-me`          | `None` — `BaseConfig.SECRET_KEY = os.environ.get("SECRET_KEY")` | Flask secret key — `change-me` is a **template placeholder**, never a runtime default. Production deployments MUST set this from a secret manager or the native process environment. |
| `HOST`         | `0.0.0.0`            | `0.0.0.0`                             | Bind host for `flask run` and the `--bind` argument to gunicorn.                       |
| `PORT`         | `5000`               | `5000`                                | Bind port (same scope as `HOST`).                                                      |
| `LOG_LEVEL`    | `INFO`               | `INFO`                                | Root log level honoured by `app/logging_config.py`.                                    |

**About `SECRET_KEY`:** the literal string `change-me` is only present in
`.env.example` as a placeholder that developers replace locally; it is not
a hardcoded application default. When the `SECRET_KEY` environment variable
is unset and no `.env` file exists, `BaseConfig.SECRET_KEY` evaluates to
`None`, which causes Flask to refuse to sign session cookies and surfaces a
loud failure rather than silently signing with a predictable key. The
`TestingConfig` subclass overrides this to a hard-coded value
(`"test-secret-key"`) so hermetic test runs do not require the variable to
be present. Generate a real production value with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Notes on loading behaviour:

- `python-dotenv` is loaded automatically by the `flask` CLI when a `.env`
  file is present. No explicit `dotenv.load_dotenv()` call is required for
  the development workflow.
- **Production deployments should use the native process environment**
  (systemd unit files, Docker `--env`, Kubernetes `env` / `envFrom`, secret
  managers such as Vault or AWS Secrets Manager). `.env` files MUST NOT be
  shipped to production hosts.
- Every `process.env.X` reference discovered in the eventual Node.js source
  must be mirrored into **both** `app/config.py` (as a typed attribute on the
  appropriate Config class) **and** `.env.example` (as a documented default).
  See AAP §0.6.4 for the parity contract.


## Endpoints

The scaffold ships with the following placeholder routes. These are the
endpoints that exist before the Node.js source is ported; ported endpoints
will be added under `app/blueprints/api/routes.py`.

| Method | Path        | Blueprint | Response                                                                                                  |
| ------ | ----------- | --------- | --------------------------------------------------------------------------------------------------------- |
| `GET`  | `/`         | `main`    | Service banner JSON: `{"service": ..., "message": ..., "endpoints": [...]}` (a list of helper paths).      |
| `GET`  | `/version`  | `main`    | `{"name": ..., "version": ..., "python": ...}`                                                            |
| `GET`  | `/healthz`  | `health`  | `{"status": "ok"}` — liveness probe.                                                                      |
| `GET`  | `/readyz`   | `health`  | `{"status": "ready"}` — readiness probe.                                                                  |
| `GET`  | `/api/`     | `api`     | `501 Not Implemented` placeholder — replaced by the ported surface.                                        |

Once the Node.js source is supplied, its endpoints must be reproduced exactly
(same method, path, request schema, response schema, and status codes) inside
`app/blueprints/api/routes.py`. See AAP §0.7.2 for the preservation contract.


## Testing

The test suite is built on `pytest` + `pytest-flask`. All tests run under the
`TestingConfig` profile (with `TESTING=True`), and the application factory is
invoked fresh per test function via the function-scoped `app` fixture in
`tests/conftest.py`. Each test therefore receives its own independent Flask
instance, which guarantees order-independent execution and trivial
parallelisation (e.g., under `pytest-xdist`).

```bash
# Run the full suite.
pytest

# Verbose mode (show each test name and outcome).
pytest -v

# Run a single test module.
pytest tests/test_health.py

# Run a single test function.
pytest tests/test_health.py::test_healthz_returns_200
```

Fixtures provided by `tests/conftest.py`:

- `app` — a Flask application instance built with `create_app('testing')`.
- `client` — `app.test_client()` for issuing requests without a live server.
- `runner` — `app.test_cli_runner()` for invoking Click-based CLI commands.


## Development

Linting, formatting, and type-checking tools are pinned in
`requirements-dev.txt`. Tool configuration lives in `pyproject.toml`.

```bash
# Lint (read-only check, no auto-fix).
ruff check .

# Format the codebase in place.
ruff format .

# Optional static type-checking against the application package.
mypy app
```

Run linting and formatting before committing; the project intentionally keeps
the configuration centralised in `pyproject.toml` so editor integrations
(VS Code, PyCharm, etc.) pick up the same rules as CLI invocations.


## Porting From Node.js

When the original Node.js source is provided, the mechanical translation map
below converts the most common idioms (see AAP §0.6.2 for the full table).
Ported endpoints belong under `app/blueprints/api/routes.py`; cross-cutting
concerns (error envelopes, logging, configuration) are already wired and
should not be duplicated inside route handlers.

| Node.js idiom                          | Python / Flask equivalent                                       |
| -------------------------------------- | --------------------------------------------------------------- |
| `app.get('/path', handler)`            | `@bp.get('/path')` decorated function                           |
| `req.body`                             | `request.get_json(silent=True)`                                 |
| `req.query.x`                          | `request.args.get('x')`                                         |
| `req.params.id`                        | `<int:id>` URL converter + function parameter                   |
| `res.json(obj)`                        | `return jsonify(obj)`                                           |
| `res.status(201).json(obj)`            | `return jsonify(obj), 201`                                      |
| `next(err)` / error middleware         | `@app.errorhandler(...)` in `app/errors.py`                     |
| `process.env.X`                        | `os.environ.get('X')` (or `current_app.config['X']`)            |
| `console.log` / `console.error`        | `logger.info` / `logger.error` (or `logger.exception`)          |
| `app.use(middleware)`                  | `@app.before_request` / `@app.after_request` / WSGI middleware  |

Additional porting rules:

- Every `process.env.X` reference in the Node source MUST be mirrored into
  **both** `app/config.py` and `.env.example` (see [Configuration](#configuration)).
- Future ported endpoints belong under `app/blueprints/api/routes.py`; do not
  add them to `main` or `health`, which are reserved for the scaffold's own
  placeholder surface and liveness/readiness probes respectively.
- Preserve **all** observed external behaviour: routes, methods, request and
  response schemas, status codes, headers, error envelopes, side effects,
  timing semantics, and environment-variable names. See AAP §0.7.2 for the
  full preservation contract.


## Open Questions

The following items (reproduced from AAP §0.7.4) must be answered before
functional parity with the original Node.js project can be implemented. The
scaffold is engineered to accommodate any reasonable answer to each of these
questions without restructuring.

1. Where does the original Node.js server source code reside (repository URL,
   branch, archive, paste, or other delivery channel)?
2. Which Node.js framework was used (Express, Fastify, Koa, NestJS, Hapi, the
   bare `http` module, or other)?
3. What is the inventory of HTTP endpoints (method, path, request shape,
   response shape, status codes)?
4. What persistence layer is used (none, PostgreSQL, MySQL, SQLite, MongoDB,
   Redis, etc.) and which ORM or driver (Sequelize, TypeORM, Prisma,
   Mongoose, native driver, etc.)?
5. What external integrations exist (databases, message queues, third-party
   HTTP APIs, file storage, OAuth providers, etc.)?
6. What environment variables does the server read at runtime?
7. What Node.js runtime version and which npm packages does it depend on
   (i.e., what does the `package.json` look like)?
8. What is the deployment target (bare metal, Docker container, Kubernetes,
   Heroku / Render / Fly, AWS Lambda / EC2 / ECS, etc.)?
9. What test suite exists, what test framework is used, and what coverage
   threshold must be preserved after the port?
10. Are there any non-HTTP entry points (CLI commands, background workers,
    scheduled jobs, message-queue consumers)?


## License

No license has been specified by the user. Until a license is supplied, the
default copyright posture applies (all rights reserved by the author). Add a
license file (e.g., `LICENSE`) and update both `pyproject.toml` and this
section once a license has been chosen.

"""WSGI entry point for the Flask scaffold.

Purpose
-------
This module is the thin entry shim that production WSGI servers (gunicorn,
uWSGI, Waitress) and the development-time ``flask`` CLI import to access
the configured Flask application. It deliberately contains no logic
beyond calling the Application Factory (:func:`app.create_app`) once at
module scope.

Production usage
----------------
The canonical launch command is::

    gunicorn wsgi:app

A reasonable starting point for I/O-bound workloads is::

    gunicorn wsgi:app \\
        --workers $((2*$(nproc)+1)) \\
        --worker-class gthread \\
        --threads 4 \\
        --bind 0.0.0.0:5000

For CPU-bound workloads, increase ``--workers`` rather than ``--threads``.
For genuinely async code paths, install ``Flask[async]`` and switch to
``--worker-class gevent`` or ``--worker-class uvicorn.workers.UvicornWorker``.
See AAP §0.6.3 for the concurrency-model translation rationale from the
original Node.js event-loop model.

Development usage
-----------------
The Flask CLI uses this module as the ``FLASK_APP`` target::

    FLASK_APP=wsgi:app flask run --host 0.0.0.0 --port 5000

``python-dotenv`` is automatically loaded by the ``flask`` CLI when a
``.env`` file is present, so ``FLASK_APP=wsgi:app``, ``FLASK_CONFIG``,
``HOST``, ``PORT``, ``LOG_LEVEL``, and any other configuration values may
be supplied through that file (see ``.env.example`` for the documented
contract).

Direct ``python wsgi.py`` usage
-------------------------------
The ``if __name__ == "__main__":`` block at the bottom of this module is
a developer-ergonomics convenience that allows::

    python wsgi.py

to start Flask's built-in development server (Werkzeug) bound to the
``HOST`` and ``PORT`` values resolved by :class:`app.config.BaseConfig`.
This path is for local debugging only — production deployments MUST use
gunicorn (or another production-grade WSGI server) per the documentation
above. The ``__main__`` guard ensures that importing :mod:`wsgi` (as
gunicorn does) does NOT inadvertently start the development server.

References
----------
* AAP §0.3.3 — Application Factory pattern (rationale for the
  factory-call-at-module-scope shape of this file)
* AAP §0.4.1 — Transformation table row for ``wsgi.py``
* AAP §0.4.2 — Cross-file dependency: ``wsgi.py`` → ``app.create_app``
* AAP §0.6.3 — Concurrency model translation (Node event loop → gunicorn
  worker model)
* [web:gunicorn-pypi] gunicorn 26.0.0 — pre-fork worker model
"""

from __future__ import annotations

from app import create_app

# ---------------------------------------------------------------------------
# Application instantiation.
# ---------------------------------------------------------------------------
# The Application Factory is called exactly once at module scope. The
# resulting ``Flask`` instance is what gunicorn imports via ``wsgi:app``
# and what the ``flask`` CLI discovers via ``FLASK_APP=wsgi:app``.
#
# No arguments are passed to :func:`create_app` here — the factory
# resolves the active configuration profile from the ``FLASK_CONFIG``
# environment variable (with a deterministic fallback to
# :data:`app.DEFAULT_CONFIG`). Hard-coding a config name here would
# defeat the per-environment selection contract documented in AAP §0.6.4.
app = create_app()


# ---------------------------------------------------------------------------
# Local development convenience entry point.
# ---------------------------------------------------------------------------
# Importing this module (as gunicorn does) does NOT execute the block
# below; it runs only when this file is invoked directly via
# ``python wsgi.py``. The block reads ``HOST`` and ``PORT`` from the
# already-loaded ``app.config`` so the developer experience matches the
# documented ``.env.example`` contract — no parallel environment-variable
# parsing is required here.
if __name__ == "__main__":
    app.run(
        host=app.config.get("HOST", "0.0.0.0"),
        port=int(app.config.get("PORT", 5000)),
    )

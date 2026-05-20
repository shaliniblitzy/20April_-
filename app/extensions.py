"""Flask extension singleton placeholders.

This module is reserved for declaring Flask extension singletons at module
scope. The Extension Singleton pattern (AAP §0.3.3) keeps extension
instances decoupled from the application factory so that:

  1. Module-scope singletons are importable from any blueprint or service.
  2. ``create_app()`` only needs to call ``extension.init_app(app)``.
  3. Tests can build ephemeral Flask instances without re-declaring
     extensions.

Typical wiring pattern (illustrative — not active in this scaffold)::

    # In this module:
    db = SQLAlchemy()

    # In ``app/__init__.py`` inside ``create_app()``:
    db.init_app(app)

Once the original Node.js source is provided (see AAP §0.6.1, §0.7.4) the
appropriate extensions will be declared here. Common candidates include:

  * ``db = SQLAlchemy()``    — only if the Node source used a SQL ORM
                               (sequelize, typeorm, prisma).
  * ``migrate = Migrate()``  — Flask-Migrate for Alembic-based migrations.
  * ``cors = CORS()``        — flask-cors, only if the Node source used
                               the ``cors`` middleware.
  * ``cache = Cache()``      — flask-caching, only if the Node source used
                               a cache layer.
  * ``jwt = JWTManager()``   — flask-jwt-extended, only if the Node source
                               issued or verified JWTs.

This module is currently EMPTY by design. No extensions are wired until the
Node source is available. See AAP §0.5.3 for the Node→Python package
equivalency mapping that will drive this file's contents during the port.
"""

__all__: list[str] = []

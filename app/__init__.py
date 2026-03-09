import os
from pathlib import Path

from flask import Flask

from .models import AccessCredential, User, db
from .views import web


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    sqlite_path = Path(app.instance_path, "phonebooks.db")
    default_db = f"sqlite:///{sqlite_path.as_posix()}"
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "change-me"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", default_db),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        EXPORT_DIR=os.environ.get("EXPORT_DIR", "/data/phonebooks"),
        BASE_HTTP_URL=os.environ.get("BASE_HTTP_URL", "http://localhost:8080"),
        ACCESS_DEFAULT_USERNAME=os.environ.get("ACCESS_DEFAULT_USERNAME", "yeabook_client"),
        ACCESS_DEFAULT_PASSWORD=os.environ.get("ACCESS_DEFAULT_PASSWORD", "change-me-now"),
        ADMIN_USERNAME=os.environ.get("ADMIN_USERNAME", "admin"),
        ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", "admin123"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "false").lower()
        == "true",
    )

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["EXPORT_DIR"], exist_ok=True)

    db.init_app(app)

    with app.app_context():
        db.create_all()
        bootstrap_admin(app)
        bootstrap_access_credential(app)

    app.register_blueprint(web)

    return app


def bootstrap_admin(app: Flask) -> None:
    if User.query.count() > 0:
        return

    admin = User(
        username=app.config["ADMIN_USERNAME"],
        is_admin=True,
    )
    admin.set_password(app.config["ADMIN_PASSWORD"])
    db.session.add(admin)
    db.session.commit()


def bootstrap_access_credential(app: Flask) -> None:
    if AccessCredential.query.count() > 0:
        return

    cred = AccessCredential(username=app.config["ACCESS_DEFAULT_USERNAME"], is_active=True)
    cred.set_password(app.config["ACCESS_DEFAULT_PASSWORD"])
    db.session.add(cred)
    db.session.commit()

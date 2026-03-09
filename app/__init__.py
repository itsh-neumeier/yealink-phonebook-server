import os
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask

from .models import User, db
from .views import web


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    sqlite_path = Path(app.instance_path, "phonebooks.db")
    default_db = f"sqlite:///{sqlite_path.as_posix()}"
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "change-me"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", default_db),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        EXPORT_DIR=os.environ.get("EXPORT_DIR", "/data/ftp/phonebooks"),
        BASE_HTTP_URL=os.environ.get("BASE_HTTP_URL", "http://localhost:8080"),
        PROVISION_USERNAME=os.environ.get("PROVISION_USERNAME", ""),
        PROVISION_PASSWORD=os.environ.get("PROVISION_PASSWORD", ""),
        FTP_HOST=os.environ.get("FTP_HOST", "0.0.0.0"),
        FTP_PORT=int(os.environ.get("FTP_PORT", "2121")),
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
    app.config["SQLITE_DB_PATH"] = sqlite_file_path(app.config["SQLALCHEMY_DATABASE_URI"])

    db.init_app(app)

    with app.app_context():
        db.create_all()
        bootstrap_admin(app)

    app.register_blueprint(web)

    return app


def sqlite_file_path(database_uri: str) -> str:
    parsed = urlparse(database_uri)
    if parsed.scheme != "sqlite":
        raise RuntimeError("Only sqlite database URIs are supported in this project.")

    raw_path = parsed.path or ""
    if raw_path.startswith("/") and len(raw_path) > 2 and raw_path[2] == ":":
        raw_path = raw_path.lstrip("/")
    return raw_path


def bootstrap_admin(app: Flask) -> None:
    if User.query.count() > 0:
        return

    admin = User(
        username=app.config["ADMIN_USERNAME"],
        is_admin=True,
        ftp_enabled=True,
        ftp_username=app.config["ADMIN_USERNAME"],
    )
    admin.set_password(app.config["ADMIN_PASSWORD"])
    admin.set_ftp_password(app.config["ADMIN_PASSWORD"])
    db.session.add(admin)
    db.session.commit()

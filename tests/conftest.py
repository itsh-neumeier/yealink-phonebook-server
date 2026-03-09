import tempfile
from pathlib import Path

import pytest

from app import create_app
from app.models import db


@pytest.fixture
def app():
    tmp_db = tempfile.NamedTemporaryFile(prefix="test-db-", suffix=".sqlite", delete=False)
    tmp_db.close()

    export_dir = tempfile.mkdtemp(prefix="exports-")

    app = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_db.name}",
            "EXPORT_DIR": export_dir,
            "SECRET_KEY": "test-secret",
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "admin123",
        }
    )

    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.engine.dispose()

    Path(tmp_db.name).unlink(missing_ok=True)


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, username="admin", password="admin123"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )
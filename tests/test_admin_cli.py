from app.admin_cli import main
from app.models import User


def test_admin_cli_list_users(app, capsys, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", app.config["SQLALCHEMY_DATABASE_URI"])
    monkeypatch.setenv("EXPORT_DIR", app.config["EXPORT_DIR"])
    exit_code = main(["list-users"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Username" in output
    assert "admin" in output


def test_admin_cli_reset_password(app, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", app.config["SQLALCHEMY_DATABASE_URI"])
    monkeypatch.setenv("EXPORT_DIR", app.config["EXPORT_DIR"])
    with app.app_context():
        user = User.query.filter_by(username="admin").first()
        assert user is not None
        assert user.check_password("admin123")

    exit_code = main(["reset-password", "admin", "new-secret-123"])
    assert exit_code == 0

    with app.app_context():
        user = User.query.filter_by(username="admin").first()
        assert user is not None
        assert user.check_password("new-secret-123")


def test_admin_cli_reset_password_missing_user(app, capsys, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", app.config["SQLALCHEMY_DATABASE_URI"])
    monkeypatch.setenv("EXPORT_DIR", app.config["EXPORT_DIR"])
    exit_code = main(["reset-password", "missing-user", "new-secret-123"])

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "not found" in output

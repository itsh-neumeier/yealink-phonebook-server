from io import BytesIO
import base64
import sqlite3
import tempfile
from pathlib import Path

from app import create_app
from app.models import AccessCredentialPhonebook, PhonebookSettings, db
from app.models import User


def auth_headers(username="apiuser", password="apipass"):
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def grant_default_access_to_phonebook(client, phonebook_id: int):
    client.post(
        "/access/1/phonebooks",
        data={"phonebook_ids": str(phonebook_id)},
        follow_redirects=True,
    )


def test_webui_requires_login(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_not_found_page_contains_home_link(client):
    response = client.get("/this-page-does-not-exist", follow_redirects=False)
    assert response.status_code == 404
    assert b"Page not found" in response.data
    assert b'href="/"' in response.data


def test_admin_login_and_create_phonebook(client):
    login_response = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )
    assert login_response.status_code == 200
    assert b"Signed in." in login_response.data

    response = client.post(
        "/phonebooks",
        data={"name": "HQ", "description": "Main office"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"HQ" in response.data


def test_edit_phonebook_name(client):
    client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )
    client.post("/phonebooks", data={"name": "Ops"}, follow_redirects=True)

    response = client.post(
        "/phonebooks/1/edit",
        data={"name": "Operations", "description": "Updated"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Operations" in response.data


def test_csv_import_export_and_xml(client):
    client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )
    client.post("/phonebooks", data={"name": "Sales"}, follow_redirects=True)
    grant_default_access_to_phonebook(client, 1)

    csv_data = b"name,office,mobile,other,line,ring,group\nAlice,1001,1002,,1,Classic,Sales\n"
    import_resp = client.post(
        "/phonebooks/1/csv/import",
        data={"csv_file": (BytesIO(csv_data), "contacts.csv")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert import_resp.status_code == 200
    assert b"Imported 1 entries." in import_resp.data

    export_resp = client.get("/phonebooks/1/csv/export")
    assert export_resp.status_code == 200
    assert export_resp.mimetype == "text/csv"
    assert b"Alice" in export_resp.data

    xml_resp = client.get("/api/phonebooks/sales.xml", headers=auth_headers())
    assert xml_resp.status_code == 200
    assert b"YealinkIPPhoneDirectory" in xml_resp.data
    assert b"Alice" in xml_resp.data

    xml_short_resp = client.get("/sales.xml", headers=auth_headers())
    assert xml_short_resp.status_code == 200
    assert b"YealinkIPPhoneDirectory" in xml_short_resp.data


def test_edit_entry(client):
    client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )
    client.post("/phonebooks", data={"name": "Team"}, follow_redirects=True)
    client.post(
        "/phonebooks/1/entries",
        data={"name": "Alice", "office": "1001"},
        follow_redirects=True,
    )

    response = client.post(
        "/entries/1/edit",
        data={"name": "Alice Smith", "office": "2001", "mobile": "", "other": ""},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Alice Smith" in response.data
    assert b"2001" in response.data


def test_xml_import_export(client):
    client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )
    client.post("/phonebooks", data={"name": "Family"}, follow_redirects=True)

    xml_data = b"""<YealinkIPPhoneDirectory>
    <DirectoryEntry><Name>Timo Neumeier</Name><Telephone>+4915237566022</Telephone><Telephone>+499112193553</Telephone></DirectoryEntry>
    <DirectoryEntry><Name>Margareta Neumeier</Name><Telephone>+4996025701</Telephone></DirectoryEntry>
</YealinkIPPhoneDirectory>"""

    import_resp = client.post(
        "/phonebooks/1/xml/import",
        data={
            "xml_file": (BytesIO(xml_data), "yealink-phonebook-zweig.xml"),
            "replace_existing": "on",
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert import_resp.status_code == 200
    assert b"Imported 2 entries from XML." in import_resp.data

    export_resp = client.get("/phonebooks/1/xml/export")
    assert export_resp.status_code == 200
    assert export_resp.mimetype == "application/xml"
    assert b"Timo Neumeier" in export_resp.data


def test_admin_can_create_user(client, app):
    client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )

    response = client.post(
        "/users",
        data={
            "username": "operator",
            "password": "operator-pass",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"User created." in response.data

    with app.app_context():
        user = User.query.filter_by(username="operator").first()
        assert user is not None
        assert user.is_admin is False


def test_language_switch(client):
    response = client.post(
        "/language/de",
        data={"next": "/login"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Anmelden" in response.data


def test_phonebook_xml_requires_basic_auth(client):
    client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )
    client.post("/phonebooks", data={"name": "Secure"}, follow_redirects=True)
    grant_default_access_to_phonebook(client, 1)

    unauthorized = client.get("/secure.xml")
    assert unauthorized.status_code == 401

    authorized = client.get("/secure.xml", headers=auth_headers())
    assert authorized.status_code == 200


def test_admin_can_manage_access_credentials(client):
    client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )

    create_resp = client.post(
        "/access",
        data={"username": "phonebookreader", "password": "reader-secret", "is_active": "on"},
        follow_redirects=True,
    )
    assert create_resp.status_code == 200
    assert b"Access credential created." in create_resp.data


def test_business_menu_contains_signed_department_tokens(client):
    client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )
    client.post(
        "/phonebooks",
        data={"name": "Geschäftliche Kontakte", "category": "business"},
        follow_redirects=True,
    )
    client.post(
        "/phonebooks/1/entries",
        data={"name": "Alice", "office": "1001", "group": "ABC"},
        follow_redirects=True,
    )
    grant_default_access_to_phonebook(client, 1)

    menu_resp = client.get("/geschaeftliche-kontakte.xml", headers=auth_headers())
    assert menu_resp.status_code == 200
    assert b"YealinkIPPhoneMenu" in menu_resp.data
    assert b"token=" in menu_resp.data


def test_startup_migrates_legacy_volume_schema():
    tmp_db = tempfile.NamedTemporaryFile(prefix="legacy-db-", suffix=".sqlite", delete=False)
    tmp_db.close()
    export_dir = tempfile.mkdtemp(prefix="legacy-exports-")

    conn = sqlite3.connect(tmp_db.name)
    conn.executescript(
        """
        CREATE TABLE phonebooks (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            slug TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_admin INTEGER NOT NULL,
            created_at TEXT
        );
        CREATE TABLE access_credentials (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_active INTEGER NOT NULL,
            created_at TEXT
        );
        INSERT INTO phonebooks(id, name, slug) VALUES (1, 'Legacy', 'legacy');
        INSERT INTO users(id, username, password_hash, is_admin) VALUES (1, 'admin', 'x', 1);
        INSERT INTO access_credentials(id, username, password_hash, is_active) VALUES (1, 'reader', 'x', 1);
        """
    )
    conn.commit()
    conn.close()

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_db.name}",
            "EXPORT_DIR": export_dir,
            "SECRET_KEY": "test-secret",
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "admin123",
            "ACCESS_DEFAULT_USERNAME": "apiuser",
            "ACCESS_DEFAULT_PASSWORD": "apipass",
        }
    )

    with app.app_context():
        settings = PhonebookSettings.query.filter_by(phonebook_id=1).first()
        permission = AccessCredentialPhonebook.query.filter_by(credential_id=1, phonebook_id=1).first()
        assert settings is not None
        assert settings.category == "private"
        assert permission is not None
        db.session.remove()
        db.engine.dispose()
    Path(tmp_db.name).unlink(missing_ok=True)

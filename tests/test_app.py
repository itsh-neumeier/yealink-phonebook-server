from io import BytesIO
import base64

from app.models import User


def auth_headers(username="apiuser", password="apipass"):
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def test_webui_requires_login(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


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

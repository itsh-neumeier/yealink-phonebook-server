from io import BytesIO

from app.models import User


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

    xml_resp = client.get("/api/phonebooks/sales.xml")
    assert xml_resp.status_code == 200
    assert b"YealinkIPPhoneDirectory" in xml_resp.data
    assert b"Alice" in xml_resp.data


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


def test_admin_can_create_ftp_user(client, app):
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
            "ftp_enabled": "on",
            "ftp_username": "ftp_operator",
            "ftp_password": "ftp-secret",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"User created." in response.data

    with app.app_context():
        user = User.query.filter_by(username="operator").first()
        assert user is not None
        assert user.ftp_enabled is True
        assert user.ftp_username == "ftp_operator"
        assert user.ftp_password_hash is not None
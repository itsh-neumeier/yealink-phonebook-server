from app.yealink_ax86r import _https_fallback_url


def test_https_fallback_url_from_http():
    assert _https_fallback_url("http://192.168.90.22") == "https://192.168.90.22"
    assert _https_fallback_url("http://192.168.90.22:80") == "https://192.168.90.22:443"


def test_https_fallback_url_non_http():
    assert _https_fallback_url("https://192.168.90.22") is None


def test_login_data_can_be_bool_without_crash(monkeypatch):
    from app.yealink_ax86r import YealinkAX86RClient

    client = YealinkAX86RClient(
        base_url="https://192.168.90.22",
        username="admin",
        password="secret",
        verify_tls=False,
    )

    calls = {"i": 0}

    def fake_request_json(method, url, data=None):
        calls["i"] += 1
        if calls["i"] == 1:
            return {"ret": "ok", "data": True}
        if calls["i"] == 2:
            return {"ret": "ok", "data": True}
        return {"ret": "ok", "data": {"list": []}}

    monkeypatch.setattr(client, "_request_json", fake_request_json)
    client.fetch_local_contacts()

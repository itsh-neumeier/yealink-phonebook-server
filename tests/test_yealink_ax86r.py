from app.yealink_ax86r import _https_fallback_url


def test_https_fallback_url_from_http():
    assert _https_fallback_url("http://192.168.90.22") == "https://192.168.90.22"
    assert _https_fallback_url("http://192.168.90.22:80") == "https://192.168.90.22:443"


def test_https_fallback_url_non_http():
    assert _https_fallback_url("https://192.168.90.22") is None

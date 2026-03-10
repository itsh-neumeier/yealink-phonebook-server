from __future__ import annotations

import os
import random
import time
from urllib.parse import urljoin

import requests


class YealinkAX86RClient:
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        verify_tls: bool = False,
        timeout_seconds: int = 10,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.username = username
        self.password = password
        self.verify_tls = verify_tls
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()

    def fetch_local_contacts(self) -> list[dict[str, str | None]]:
        self._login()
        payload = self._request_json(
            "GET",
            self._endpoint("api/contacts/localcontacts?group=0&page=1&count=3000&p=ContactsLocal"),
        )
        raw_list = payload.get("data", {}).get("list", [])
        contacts: list[dict[str, str | None]] = []
        for raw in raw_list:
            if not isinstance(raw, dict):
                continue
            contacts.append(
                {
                    "name": (raw.get("name") or "").strip(),
                    "office": _clean(raw.get("office_number")),
                    "mobile": _clean(raw.get("mobile_number")),
                    "other": _clean(raw.get("other_number")),
                    "line": _clean(raw.get("line")),
                    "group": _clean(raw.get("group")),
                }
            )
        return [c for c in contacts if c["name"] and any([c["office"], c["mobile"], c["other"]])]

    def _login(self) -> None:
        login_info = self._request_json(
            "GET",
            self._endpoint("api/common/info?p=Login"),
        )
        data = login_info.get("data", {})
        n_hex = data.get("wui.common.rsaN")
        e_hex = data.get("wui.common.rsaE")
        encrypted = self.password
        if n_hex and e_hex:
            encrypted = "__WUI_ENC__:" + _rsa_encrypt_pkcs1_v15_hex(self.password, n_hex, e_hex)

        result = self._request_json(
            "POST",
            self._endpoint("api/auth/login?p=Login"),
            data={"username": self.username, "pwd": encrypted},
        )
        if result.get("ret") != "ok" or not result.get("data"):
            raise ValueError("Yealink login failed.")

    def _endpoint(self, path: str) -> str:
        stamp = str(int(time.time() * 1000)) + str(random.randint(100, 999))
        sep = "&" if "?" in path else "?"
        return urljoin(self.base_url, f"{path}{sep}t={stamp}")

    def _request_json(self, method: str, url: str, data: dict | None = None) -> dict:
        response = self.session.request(
            method=method,
            url=url,
            data=data,
            verify=self.verify_tls,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict):
            return payload
        raise ValueError("Unexpected Yealink API response.")


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _rsa_encrypt_pkcs1_v15_hex(plaintext: str, n_hex: str, e_hex: str) -> str:
    n = int(n_hex, 16)
    e = int(e_hex, 16)
    message = plaintext.encode("utf-8")
    k = (n.bit_length() + 7) // 8

    if len(message) > k - 11:
        raise ValueError("Password too long for Yealink RSA key.")

    padding_len = k - len(message) - 3
    padding = bytearray()
    while len(padding) < padding_len:
        b = os.urandom(1)
        if b != b"\x00":
            padding.extend(b)

    em = b"\x00\x02" + bytes(padding) + b"\x00" + message
    m = int.from_bytes(em, byteorder="big")
    c = pow(m, e, n)
    encrypted = c.to_bytes(k, byteorder="big")
    return encrypted.hex()

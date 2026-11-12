"""Thin async client for the V-Guard NOUS cloud used by the Smart 2.0 app."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
import base64

import aiohttp

from .const import APP_HEADERS, NOUS20, SMART20


class VGuardApiError(Exception):
    """Raised when the NOUS cloud returns an unexpected response."""


class VGuardPublishError(VGuardApiError):
    pass


def _format_error(resp) -> str:
    if isinstance(resp, dict):
        return str(resp.get("message") or resp.get("error") or "request failed")
    return "unexpected response"


@dataclass
class Frame:
    """Parsed VG029 telemetry frame."""

    fields: dict
    captured_at: float


class VGuardApi:
    """Session + telemetry client (read-only)."""

    def __init__(self, session: aiohttp.ClientSession, cfg: dict):
        self._session = session
        self._cfg = cfg  # mutable dict mirrored from the config entry

    async def _request(self, url, method="GET", json_body=None, auth=True, _retry=True):
        headers = dict(APP_HEADERS)
        if auth:
            tok = self._cfg.get("access_token")
            if tok:
                headers["authorization"] = tok
        try:
            async with self._session.request(
                method, url, headers=headers,
                json=json_body if json_body is not None else None,
                timeout=aiohttp.ClientTimeout(total=25),
            ) as resp:
                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    data = {"raw": await resp.text()}
                if resp.status == 401 and auth and _retry:
                    if await self.refresh_access_token():
                        return await self._request(url, method, json_body, auth, _retry=False)
                return resp.status, data
        except Exception as err:  # noqa: BLE001 - surfaced to HA as UpdateFailed
            return 0, {"error": str(err)}

    async def request_otp(self, country_code: str, mobile: str):
        return await self._request(
            SMART20 + "/v1/user/otp", "POST",
            {"type": 1, "authType": 1, "countryCode": country_code, "mobile": mobile, "email": None},
            auth=False,
        )

    async def login(self, country_code: str, mobile: str, otp: str, fcm_token: str | None):
        return await self._request(
            SMART20 + "/v1/user/login", "POST",
            {
                "email": None,
                "loginType": 1,
                "countryCode": country_code,
                "mobile": mobile,
                "otp": otp,
                "fcmToken": fcm_token,
                "password": None,
            },
            auth=False,
        )

    async def refresh_access_token(self):
        rt = self._cfg.get("refresh_token")
        if not rt:
            return False
        status, resp = await self._request(
            SMART20 + "/v1/user/access-token", "PUT", {"token": rt}, auth=False
        )
        data = (resp or {}).get("data") or {}
        tok = data.get("accessToken")
        if status == 200 and tok:
            self._cfg["access_token"] = tok
            try:
                import base64

                payload = tok.split(".")[1]
                payload += "=" * (-len(payload) % 4)
                self._cfg["access_token_exp"] = int(
                    json.loads(base64.urlsafe_b64decode(payload)).get("exp", 0)
                )
            except Exception:
                self._cfg["access_token_exp"] = int(time.time()) + 86000
            return True
        return False

    async def ensure_access_token(self):
        exp = float(self._cfg.get("access_token_exp") or 0)
        if not self._cfg.get("access_token") or exp < time.time() + 7200:
            await self.refresh_access_token()
        return self._cfg.get("access_token")

    async def my_products(self):
        await self.ensure_access_token()
        status, resp = await self._request(SMART20 + "/v1/product/my-products", "GET")
        if status != 200:
            return []
        data = (resp or {}).get("data") or {}
        if isinstance(data, dict):
            return data.get("myProductsList") or []
        return []

    async def telemetry(self):
        await self.ensure_access_token()
        cfg = self._cfg
        path = "/device/v2/subscribe/%s/%s/%s" % (
            cfg["serial"], cfg["product_type"], cfg["device_code"]
        )
        status, resp = await self._request(NOUS20 + path, "GET")
        if status == 200 and isinstance(resp, dict):
            payload = (resp.get("data") or {}).get("payload")
            if payload:
                if isinstance(payload, str):
                    try:
                        parsed = json.loads(payload)
                    except json.JSONDecodeError:
                        parsed = {"_unparsed": payload}
                else:
                    parsed = payload
                frame = parsed.get("VG029", parsed)
                if not isinstance(frame, dict):
                    frame = {"raw": frame}
                return Frame(fields=frame, captured_at=time.time())
            return None  # latest-packet cache miss; not an error
        if status in (0, 401, 403):
            raise VGuardApiError("NOUS subscribe failed: HTTP %s (%s)" % (status, _format_error(resp)))
        if status in (400, 404):
            return None
        raise VGuardApiError("NOUS subscribe unexpected: HTTP %s (%s)" % (status, _format_error(resp)))


    async def publish(self, command: str) -> bool:
        """Publish a plaintext command to the inverter (app's NOUS path)."""
        cfg = self._cfg
        key, iv = cfg.get("device_key"), cfg.get("device_iv")
        if not key or not iv:
            raise VGuardPublishError(
                "device key/iv not in config entry - remove and re-add the integration to capture them"
            )
        topic = "apps/%s/%s/%s" % (cfg["product_type"], cfg["device_code"], cfg["serial"])
        payload = encrypt_nous_payload(key, iv, command)
        await self.ensure_access_token()
        status, resp = await self._request(
            NOUS20 + "/nous/device/publish",
            "POST",
            {"topic": topic, "payload": payload},
        )
        if 200 <= status < 300:
            return True
        raise VGuardPublishError("publish failed: HTTP %s (%s)" % (status, _format_error(resp)))


def _pkcs7_pad(data: bytes, block: int = 16) -> bytes:
    pad = block - (len(data) % block)
    return data + bytes([pad]) * pad


def encrypt_nous_payload(key: str, iv: str, plaintext: str) -> str:
    """AES/CBC/PKCS7Padding + base64, as the app encrypts commands for NOUS."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    k = key.encode("utf-8")
    v = iv.encode("utf-8")
    cipher = Cipher(algorithms.AES(k), modes.CBC(v))
    enc = cipher.encryptor()
    ct = enc.update(_pkcs7_pad(plaintext.encode("utf-8"))) + enc.finalize()
    return base64.b64encode(ct).decode()



"""Config flow for the V-Guard Smart integration (OTP login)."""

from __future__ import annotations

import logging
import time
import base64
import json as _json

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCESS_TOKEN_EXP,
    CONF_COUNTRY_CODE,
    CONF_DEVICE_CODE,
    CONF_DEVICE_IV,
    CONF_DEVICE_KEY,
    CONF_MOBILE,
    CONF_PRODUCT_NAME,
    CONF_PRODUCT_TYPE,
    CONF_REFRESH_TOKEN,
    CONF_SERIAL,
    CONF_USER_ASSETS_ID,
    DOMAIN,
)
from .api import VGuardApi

_LOGGER = logging.getLogger(__name__)


def _resp_err(resp) -> str:
    if isinstance(resp, dict):
        return str(resp.get("message") or resp.get("error") or "request failed")
    return "unexpected response"


def _token_exp(tok: str) -> int:
    try:
        payload = tok.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return int(_json.loads(base64.urlsafe_b64decode(payload)).get("exp", 0))
    except Exception:  # noqa: BLE001
        return int(time.time()) + 86000


class VGuardConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Two-step OTP login."""

    VERSION = 1

    def __init__(self):
        self._mobile = None
        self._country_code = None

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            mobile = user_input[CONF_MOBILE].strip().replace(" ", "").lstrip("+")
            country_code = user_input[CONF_COUNTRY_CODE].strip()
            session = async_get_clientsession(self.hass)
            api = VGuardApi(session, {})
            try:
                status, resp = await api.request_otp(country_code, mobile)
            except Exception as err:  # noqa: BLE001
                status, resp = 0, {"error": str(err)}
            if status == 200:
                self._mobile = mobile
                self._country_code = country_code
                return await self.async_step_otp()
            errors["base"] = "otp_request_failed"
            _LOGGER.warning("OTP request failed: HTTP %s (%s)", status, _resp_err(resp))

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_COUNTRY_CODE, default="+91"): str,
                    vol.Required(CONF_MOBILE): str,
                }
            ),
            errors=errors,
        )

    async def async_step_otp(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            cfg = {"access_token": None, "access_token_exp": 0, "refresh_token": None}
            session = async_get_clientsession(self.hass)
            api = VGuardApi(session, cfg)
            status, resp = await api.login(
                self._country_code, self._mobile, user_input["otp"].strip(), None
            )
            data = (resp or {}).get("data") or {}
            access, refresh = data.get("accessToken"), data.get("refreshToken")
            if status == 200 and access and refresh:
                cfg.update(
                    access_token=access,
                    refresh_token=refresh,
                    access_token_exp=_token_exp(access),
                )
                api = VGuardApi(session, cfg)
                products = await api.my_products()
                inverter = next(
                    (p for p in products if p.get("isSolar") == 1 or p.get("categoryId") == 2),
                    products[0] if products else None,
                )
                if inverter is None:
                    return self.async_abort(reason="no_products")
                entry_data = {
                    CONF_MOBILE: self._mobile,
                    CONF_COUNTRY_CODE: self._country_code,
                    CONF_ACCESS_TOKEN: access,
                    CONF_REFRESH_TOKEN: refresh,
                    CONF_ACCESS_TOKEN_EXP: _token_exp(access),
                    CONF_SERIAL: str(inverter.get("serialNumber")),
                    CONF_USER_ASSETS_ID: str(inverter.get("userAssetsId")),
                    CONF_PRODUCT_TYPE: inverter.get("type") or "dups",
                    CONF_DEVICE_CODE: inverter.get("deviceCode") or "CE01",
                    CONF_DEVICE_KEY: inverter.get("key"),
                    CONF_DEVICE_IV: inverter.get("iv"),
                    CONF_PRODUCT_NAME: inverter.get("productName") or "V-Guard Inverter",
                }
                await self.async_set_unique_id(f"vguard-{entry_data[CONF_SERIAL]}")
                self._abort_if_unique_id_configured(updates=entry_data)
                return self.async_create_entry(
                    title=entry_data[CONF_PRODUCT_NAME], data=entry_data
                )
            errors["base"] = "invalid_otp"
            _LOGGER.warning("Login failed: HTTP %s (%s)", status, _resp_err(resp))

        return self.async_show_form(
            step_id="otp",
            data_schema=vol.Schema({vol.Required("otp"): str}),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Kick off OTP re-authentication."""
        entry = self._get_reauth_entry()
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            api = VGuardApi(session, {})
            await api.request_otp(entry.data[CONF_COUNTRY_CODE], entry.data[CONF_MOBILE])
            return await self.async_step_reauth_otp()
        return self.async_show_form(step_id="reauth_confirm", data_schema=vol.Schema({}))

    async def async_step_reauth_otp(self, user_input=None):
        errors = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            cfg = {"access_token": None, "access_token_exp": 0, "refresh_token": None}
            session = async_get_clientsession(self.hass)
            api = VGuardApi(session, cfg)
            status, resp = await api.login(
                entry.data[CONF_COUNTRY_CODE],
                entry.data[CONF_MOBILE],
                user_input["otp"].strip(),
                None,
            )
            data = (resp or {}).get("data") or {}
            access, refresh = data.get("accessToken"), data.get("refreshToken")
            if status == 200 and access and refresh:
                new_data = dict(entry.data)
                new_data.update(
                    access_token=access,
                    refresh_token=refresh,
                    access_token_exp=_token_exp(access),
                )
                return self.async_update_reload_and_abort(entry, data=new_data)
            errors["base"] = "invalid_otp"

        return self.async_show_form(
            step_id="reauth_otp",
            data_schema=vol.Schema({vol.Required("otp"): str}),
            errors=errors,
        )

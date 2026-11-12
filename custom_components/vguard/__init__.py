"""V-Guard Smart integration setup."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import VGuardApi, VGuardApiError
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCESS_TOKEN_EXP,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config) -> bool:
    await _async_register_card(hass)
    return True


async def _async_register_card(hass: HomeAssistant) -> None:
    import os

    card_path = os.path.join(os.path.dirname(__file__), "www", "vguard-inverter-card.js")
    if not os.path.exists(card_path):
        _LOGGER.warning("vguard-inverter-card.js not found next to integration; skipping card registration")
        return
    try:
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig("/vguard/vguard-inverter-card.js", card_path, cache_headers=False)]
        )
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("static_paths API unavailable, trying legacy: %s", err)
        try:
            hass.http.register_static_path("/vguard/vguard-inverter-card.js", card_path, cache_headers=False)
        except Exception as err2:  # noqa: BLE001
            _LOGGER.warning("card static path registration failed: %s", err2)
            return
    try:
        from homeassistant.components.frontend import add_extra_js_url

        add_extra_js_url(hass, "/vguard/vguard-inverter-card.js")
        return
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("add_extra_js_url unavailable, trying lovelace resources: %s", err)
    try:
        lovelace = hass.data.get("lovelace")
        resources = getattr(lovelace, "resources", None) if lovelace else None
        if resources is None:
            _LOGGER.warning("lovelace resources API not found; add /vguard/vguard-inverter-card.js as a module resource manually")
            return
        items = await resources.async_items()
        url = "/vguard/vguard-inverter-card.js?v=1.0.0"
        if any(str(i.get("url", "")).startswith("/vguard/vguard-inverter-card.js") for i in items):
            return
        await resources.async_create_item({"res_type": "module", "url": url})
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("card resource registration failed; add /vguard/vguard-inverter-card.js as a module resource manually: %s", err)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    # mutable cfg mirrored from the entry; api mutates it in place on refresh
    entry_data = dict(entry.data)
    cfg = dict(entry_data)

    class VGuardCoordinator(DataUpdateCoordinator):
        def __init__(self):
            super().__init__(
                hass,
                _LOGGER,
                name="vguard",
                update_interval=timedelta(seconds=30),
            )
            self.api = VGuardApi(session, cfg)

        async def _async_update_data(self):
            try:
                frame = await self.api.telemetry()
            except VGuardApiError as err:
                raise UpdateFailed(str(err)) from err
            except Exception as err:  # noqa: BLE001
                raise UpdateFailed(f"poll failed: {err}") from err

            # persist rotated tokens back to the config entry when they change
            if (
                cfg.get(CONF_ACCESS_TOKEN) != entry_data.get(CONF_ACCESS_TOKEN)
                or cfg.get(CONF_REFRESH_TOKEN) != entry_data.get(CONF_REFRESH_TOKEN)
                or cfg.get(CONF_ACCESS_TOKEN_EXP) != entry_data.get(CONF_ACCESS_TOKEN_EXP)
            ):
                entry_data.update(
                    {
                        CONF_ACCESS_TOKEN: cfg.get(CONF_ACCESS_TOKEN),
                        CONF_REFRESH_TOKEN: cfg.get(CONF_REFRESH_TOKEN),
                        CONF_ACCESS_TOKEN_EXP: cfg.get(CONF_ACCESS_TOKEN_EXP),
                    }
                )
                hass.config_entries.async_update_entry(entry, data=dict(entry_data))

            if frame is None:
                # keep last data; age will age out naturally
                return self.data or {"fields": {}, "captured_at": None, "missing": True}
            return {"fields": frame.fields, "captured_at": frame.captured_at, "missing": False}

    coordinator = VGuardCoordinator()
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "cfg": cfg,
        "entry_data": entry_data,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return ok

# V-Guard Smart Inverter — Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=adeveloper79&repository=VGuard-has&category=integration)
[![GitHub](https://img.shields.io/badge/github-adeveloper79/VGuard%2Dhas-blue.svg)](https://github.com/adeveloper79/VGuard-has)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Unofficial Home Assistant integration for **V-Guard Smart / SMART PRO 1200 S** solar
inverters (and compatible DUPS-family products) over the V-Guard NOUS cloud, using the
same protocol as the official *V-Guard Smart 2.0* Android app.

> Not affiliated with or endorsed by V-Guard. Reverse-engineered for interoperability
> with hardware you own. Use at your own risk — sending commands changes the state of
> your inverter (charging behaviour, alarms, force-cut scheduling).

## Features

- OTP login from the Home Assistant UI (same SMS OTP flow as the phone app)
- Automatic access-token refresh; automatic re-auth if the phone app logs the account out
- Auto-discovers your inverter product via `my-products` (no serials to type)
- **Sensors**: grid voltage, output voltage, battery voltage, battery % (computed exactly like the app),
  frequency, load current, apparent power, aux discharge, WiFi RSSI, energy counters
- **Binary sensors**: online/offline (stale after > 15 min without data), mains indicator (app formula: VG095 bit 0x08)
- **Switches**: Turbo Charging, Appliance Mode, Holiday Mode, Extra Backup Mode, Grid Force Cut
- **Selects**: Night Forced Cut time, Force Cut duration, Load-exceeds alarm threshold
- **Numbers**: Battery Backup / Performance sliders — inversely linked on the same `VG035` register (1–7)
- **Button**: Battery-Type Unlock (30 min)
- Full raw `VG029` telemetry frame exposed as attributes
- Bundled **Lovelace card** (`vguard-inverter-card.js`) auto-registered on install —
  no YAML or resource steps; add it from the card picker ("V-Guard Inverter Card")

## Installation (HACS) — one click

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=adeveloper79&repository=VGuard-has&category=integration)

Clicking the badge opens your Home Assistant, adds this repository to HACS as a custom
integration, and lets you install it from there. Requires HACS to be set up.

## Installation (HACS)

1. HACS → Integrations → ⋮ → **Custom repositories** → add this repo, category **Integration**
2. Install **V-Guard Smart Inverter**
3. Restart Home Assistant
4. **Settings → Devices & Services → + Add Integration → V-Guard Smart**
5. Enter the mobile number of your V-Guard Smart account (country code `+91`) → OTP SMS → enter OTP

The integration discovers your inverter (`SMART PRO 1200 S`) and starts polling every 30 s.

## Installation (manual)

```bash
mkdir -p /config/custom_components
cp -r custom_components/vguard /config/custom_components/vguard
# restart Home Assistant, then add the integration as above
```

## Card

The card is auto-registered as a Lovelace resource when the integration loads.
**Overview → Edit → + Add Card → search "V-Guard Inverter Card"**. It shows battery /
grid / output voltage, apparent power, frequency, current, online status and the
Turbo/Appliance/Holiday/Extra Backup/Force Cut chips (tap to toggle). Optional config:
`{ title: "..." }` to rename it.

Prefer YAML? See [`examples/dashboard.yaml`](examples/dashboard.yaml).

## How it works (protocol notes)

The OEM design is:

```text
Phone app (V-Guard Smart 2.0)
        │  HTTPS REST, long-poll subscribe (not MQTT)
        ▼
   nous20.vguard.in  (NOUS cloud, JSON envelopes, AES-CBC per-device payload)
        ▼
  ESP32 comm board inside the inverter (WiFi, UART 9600 8N1 to the inverter MCU)
        ▼
   Inverter MCU (register read/write only, 8-byte frames)
```

App-side specifics replicated by this integration:

- Auth: `POST v1/user/otp` → `POST v1/user/login` (mobile + OTP) → `{accessToken, refreshToken}`
  at `https://smart20.vguard.in`; refresh via `PUT v1/user/access-token` (auth header
  `authorization: <raw JWT>`, **no** `Bearer ` prefix; platform headers required)
- Telemetry: `GET device/v2/subscribe/{serial}/{product_type}/{device_code}` — returns the
  latest published frame; `GET device/info-status/{serial}` similar
- Commands: `POST nous/device/publish` with `{topic: "apps/{product_type}/{device_code}/{serial}", payload}`
  where `payload = base64(AES/CBC/PKCS7Padding(key, iv, command))` using the per-device key/IV
  provisioned at product registration (stored in the app's Room DB)
- Frame shape: `{"VG029": {"VG014": "242.00", "VG016": "13.14", ...}}` — the VG-prefixed keys
  map to the inverter MCU's registers via the ESP firmware (not the app)
- `product_type` / `device_code` are literals like `dups` / `CE01` for the SMART PRO 1200 S;
  other families use their own (`VG_STB_BT_WF` for stabilizers, `VG_PUMP_BT_WF`, `VG_FAN_BT_WF` …)

Community reference for the OEM ESP firmware side (UART register map, ESPHome replacement):
<https://github.com/KratosMr/VGuard-Inverter-Esphome>

## Settings commands (VGxxx) used by this integration

| Entity | Command | Notes |
|---|---|---|
| Turbo Charging | `VG099:1` / `VG099:0` | force full battery charge |
| Appliance Mode | `VG036:1` / `VG036:0` | prioritise appliances over backup |
| Holiday Mode | `VG100:1` / `VG100:0` | inverter economy mode while away |
| Extra Backup Mode | `VG072:1` / `VG072:0` | reserve a charge slice for outages |
| Grid Force Cut | `VG038:1` / `VG038:0` (+ `VG037:<minutes>` for duration) | grid-disconnect timer |
| Battery Backup level | `VG035:<n>` | backup-priority level (inverse axis) |
| Performance level | `VG035:<n>` (8−n shown) | performance-priority level; inverse of Backup |
| Night Forced Cut time | `VG219:<seconds>` | nightly grid cut-off schedule (8 slots) |
| Day-time Load Usage | `VG185:1` / `VG185:0` | daytime economy on solar power |
| Force Cut Duration | `VG037:<30/60/120/180/240>` | minutes |
| Load-exceeds alarm | `VG050:<50..100>` | load alarm threshold (%) |
| Battery Type Unlock | `VG105:1` | one-shot 30 min unlock window |

Read state comes from the same subscribe frame (`VG0xx`), so entities stay in sync with
the inverter's own view of the world.

## Safety

Writing registers can change charging/protection behaviour. Commands here are exactly the
ones the official app sends for the corresponding buttons — but you are responsible for
what you toggle. Start with harmless ones (holiday mode, buzzer-class changes) and watch
the inverter display when enabling force-cut or touching battery settings.

## License

MIT — see [LICENSE](LICENSE).

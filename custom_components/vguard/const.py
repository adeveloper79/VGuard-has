"""Constants for the V-Guard Smart integration."""

DOMAIN = "vguard"
MANUFACTURER = "V-Guard"

SMART20 = "https://smart20.vguard.in"
NOUS20 = "https://nous20.vguard.in"

APP_HEADERS = {
    "content-type": "application/json",
    "app-version": "2.0.18",
    "platform": "1",
    "platform-version": "35",
    "platform-model": "android-SMART PRO",
}

PLATFORMS = ["sensor", "binary_sensor", "switch", "select", "button"]

CONF_SERIAL = "serial"
CONF_PRODUCT_TYPE = "product_type"
CONF_DEVICE_CODE = "device_code"
CONF_PRODUCT_NAME = "product_name"
CONF_DEVICE_KEY = "device_key"
CONF_DEVICE_IV = "device_iv"
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_ACCESS_TOKEN_EXP = "access_token_exp"
CONF_MOBILE = "mobile"
CONF_COUNTRY_CODE = "country_code"
CONF_USER_ASSETS_ID = "user_assets_id"

# aliases: friendly label -> VG key in the VG029 frame
SENSOR_SCALARS = {
    "grid_voltage": "VG014",
    "output_voltage": "VG015",
    "battery_voltage": "VG016",
    "load_current": "VG018",
    "frequency_hz": "VG019",
    "apparent_power": "VG020",
    "wifi_rssi": "VG011",
    "aux_discharge": "VG017",
    "load_percent_raw": "VG024",
    "energy_counter_a": "VG110",
    "energy_counter_b": "VG042",
}

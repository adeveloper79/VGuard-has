/* V-Guard Smart Pro 1200 S — Lovelace card (auto-registered by the vguard integration) */
class VGuardInverterCard extends HTMLElement {
  setConfig(config) {
    this._config = Object.assign({ title: "V-Guard Smart Pro 1200 S", prefix: "" }, config || {});
    if (!this._hass) return;
    this._render();
  }

  getCardSize() { return 5; }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _eid(domain, key) {
    const p = this._config.prefix || "";
    const direct = p + domain + ".smart_pro_1200_s_" + key;
    if (this._hass.states[direct]) return direct;
    // fallback: scan for the entity with the same suffix
    const suffix = ".smart_pro_1200_s_" + key;
    const found = Object.keys(this._hass.states).find((e) => e.endsWith(suffix));
    return found || null;
  }

  _state(domain, key) {
    const id = this._eid(domain, key);
    if (!id) return null;
    return this._hass.states[id];
  }

  _fmt(v, unit) {
    if (v === undefined || v === null) return "–";
    if (typeof v === "number") return (Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(1)) + (unit ? "" + unit : "");
    const n = Number(v);
    if (!Number.isNaN(n)) return (Math.abs(n) >= 100 ? n.toFixed(0) : n.toFixed(1)) + (unit || "");
    return String(v);
  }

  _tile(label, value, unit, accent) {
    return `<div class="tile${accent ? " accent" : ""}"><div class="tval">${this._fmt(value, unit)}</div><div class="tlabel">${label}</div></div>`;
  }

  _chip(label, stateId, iconOn, iconOff) {
    const st = stateId ? this._hass.states[stateId] : null;
    const on = st && st.state === "on";
    const icon = on ? iconOn : iconOff;
    const cls = "chip" + (on ? " on" : "");
    return `<button class="${cls}" data-entity="${stateId || ""}"><ha-icon icon="${icon}"></ha-icon><span>${label}</span></button>`;
  }

  _render() {
    if (!this._hass) return;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const onlineId = this._eid("binary_sensor", "online");
    const online = onlineId && this._hass.states[onlineId] && this._hass.states[onlineId].state === "on";
    const s = (d, k) => {
      const st = this._state(d, k);
      return st ? st.state : null;
    };

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        ha-card { padding: 14px 16px; background: var(--card-background-color, #fff); border-radius: var(--ha-card-border-radius, 12px); box-shadow: var(--ha-card-box-shadow, none); }
        .head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
        .title { font-size: 15px; font-weight: 600; color: var(--primary-text-color, #21313c); }
        .dot { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--secondary-text-color, #727272); }
        .dot span { width: 10px; height: 10px; border-radius: 50%; background: ${online ? "#4caf50" : "#e53935"}; display: inline-block; }
        .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
        .tile { background: var(--secondary-background-color, #f3f6f9); border-radius: 10px; padding: 10px 8px; text-align: center; }
        .tile.accent { background: var(--primary-color, #ff9800); color: #fff; }
        .tile.accent .tlabel { color: rgba(255,255,255,.85); }
        .tval { font-size: 19px; font-weight: 700; line-height: 1.1; font-variant-numeric: tabular-nums; }
        .tlabel { font-size: 11px; color: var(--secondary-text-color, #727272); margin-top: 3px; }
        .divider { height: 1px; background: var(--divider-color, #e0e0e0); margin: 12px 2px; }
        .chips { display: flex; flex-wrap: wrap; gap: 8px; }
        .chip { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 18px; border: 1px solid var(--divider-color, #ddd); background: transparent; color: var(--primary-text-color, #21313c); cursor: pointer; font-size: 12px; }
        .chip.on { background: var(--primary-color, #ff9800); border-color: var(--primary-color, #ff9800); color: #fff; }
        .chip ha-icon { --mdi-icon-size: 18px; }
        .foot { margin-top: 10px; font-size: 11px; color: var(--secondary-text-color, #727272); display: flex; justify-content: space-between; }
      </style>
      <ha-card>
        <div class="head">
          <div class="title">${this._config.title}</div>
          <div class="dot"><span></span>${online ? "Online" : "Offline"}</div>
        </div>

        <div class="grid">
          ${this._tile("Battery", s("sensor", "battery_voltage"), " V", true)}
          ${this._tile("Grid", s("sensor", "grid_voltage"), " V", false)}
          ${this._tile("Output", s("sensor", "output_voltage"), " V", false)}
          ${this._tile("Load", s("sensor", "apparent_power"), " VA", false)}
          ${this._tile("Frequency", s("sensor", "frequency"), " Hz", false)}
          ${this._tile("Current", s("sensor", "load_current"), " A", false)}
        </div>

        <div class="divider"></div>

        <div class="chips">
          ${this._chip("Turbo", this._eid("switch", "turbo_charging"), "mdi:battery-charging-high", "mdi:battery-charging-high")}
          ${this._chip("Appliance", this._eid("switch", "appliance_mode"), "mdi:power-plug", "mdi:power-plug-outline")}
          ${this._chip("Holiday", this._eid("switch", "holiday_mode"), "mdi:palm-tree", "mdi:palm-tree")}
          ${this._chip("Extra Backup", this._eid("switch", "extra_backup_mode"), "mdi:battery-clock", "mdi:battery-clock")}
          ${this._chip("Force Cut", this._eid("switch", "grid_force_cut"), "mdi:transmission-tower-off", "mdi:transmission-tower")}
        </div>

        <div class="foot">
          <span>Mains ${this._state("binary_sensor", "mains") === "on" ? "ON" : "FAIL"} · ${this._fmt(s("sensor", "battery"))}% · WiFi ${this._fmt(s("sensor", "wifi_rssi"), " dBm")}</span>
          <span>Backup Lv. ${this._fmt(s("number", "battery_backup_level"))} / Perf Lv. ${this._fmt(s("number", "performance_level"))}</span>
        </div>
      </ha-card>
    `;

    this.shadowRoot.querySelectorAll(".chip").forEach((btn) => {
      btn.addEventListener("click", () => {
        const entityId = btn.getAttribute("data-entity");
        if (entityId && this._hass) {
          this._hass.callService("switch", "toggle", { entity_id: entityId });
        }
      });
    });
  }
}

customElements.define("vguard-inverter-card", VGuardInverterCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "vguard-inverter-card",
  name: "V-Guard Inverter Card",
  preview: true,
  description: "Battery/grid/output at a glance plus turbo & appliance toggles for the V-Guard Smart Pro 1200 S"
});

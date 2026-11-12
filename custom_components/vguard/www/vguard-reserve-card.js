/* V-Guard Smart Pro 1200 S — Reserve Power card (auto-registered by the vguard integration) */
class VGuardReserveCard extends HTMLElement {
  setConfig(config) {
    this._config = Object.assign({ title: "Reserve Power", prefix: "" }, config || {});
    if (!this._hass) return;
    this._render();
  }

  getCardSize() { return 4; }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _eid(domain, key) {
    const p = this._config.prefix || "";
    const direct = p + domain + ".smart_pro_1200_s_" + key;
    if (this._hass.states[direct]) return direct;
    const suffix = ".smart_pro_1200_s_" + key;
    return Object.keys(this._hass.states).find((e) => e.endsWith(suffix)) || null;
  }

  _state(domain, key) {
    const id = this._eid(domain, key);
    return id ? this._hass.states[id] : null;
  }

  _num(domain, key) {
    const st = this._state(domain, key);
    const v = st ? Number(st.state) : NaN;
    return Number.isFinite(v) ? v : null;
  }

  _esc(str) {
    if (str === undefined || str === null) return "";
    return String(str).replace(/[&<>"']/g, (m) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    })[m]);
  }

  static _NIGHT_SLOTS = [
    ["No Force Cut", "No Force Cut"],
    ["06:00 PM", "06:00 PM"],
    ["07:00 PM", "07:00 PM"],
    ["08:00 PM", "08:00 PM"],
    ["09:00 PM", "09:00 PM"],
    ["10:00 PM", "10:00 PM"],
    ["11:00 PM", "11:00 PM"],
    ["00:00 AM", "00:00 AM"],
  ];

  _render() {
    if (!this._hass) return;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const perf = this._num("number", "performance_level");
    const backup = this._num("number", "battery_backup_level");
    const nightState = this._state("select", "night_forced_cut_time");
    const nightSel = nightState ? nightState.state : null;
    const perfId = this._eid("number", "performance_level");
    const backupId = this._eid("number", "battery_backup_level");
    const nightId = this._eid("select", "night_forced_cut_time");

    const slider = (label, value, entityId, min, max, minCap, maxCap) => `
      <div class="slider-block">
        <div class="slider-head"><span>${this._esc(label)}</span><span class="val">${value === null ? "–" : this._esc(value + " / " + max)}</span></div>
        <div class="slider-row">
          <span class="cap lo">${this._esc(minCap)}</span>
          <input type="range" min="${min}" max="${max}" step="1" value="${value === null ? 1 : value}"
                 data-entity="${this._esc(entityId || "")}" ${entityId ? "" : "disabled"}/>
          <span class="cap hi">${this._esc(maxCap)}</span>
        </div>
      </div>`;

    const chips = VGuardReserveCard._NIGHT_SLOTS.map(([label]) => {
      const active = nightSel === label;
      return `<button class="slot${active ? " on" : ""}" data-option="${this._esc(label)}" data-entity="${this._esc(nightId || "")}">${this._esc(label)}</button>`;
    }).join("");

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        ha-card { padding: 14px 16px; background: var(--card-background-color, #fff); border-radius: var(--ha-card-border-radius, 12px); box-shadow: var(--ha-card-box-shadow, none); color: var(--primary-text-color, #21313c); }
        .head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
        .title { font-size: 15px; font-weight: 600; }
        .note { font-size: 11px; color: var(--secondary-text-color, #727272); margin: 2px 0 12px; }
        .section-label { font-size: 12px; font-weight: 700; color: var(--secondary-text-color, #727272); text-transform: uppercase; letter-spacing: .04em; margin: 10px 0 2px; }
        .slider-block { margin: 10px 0; }
        .slider-head { display: flex; justify-content: space-between; font-size: 12px; font-weight: 600; margin-bottom: 4px; }
        .slider-head .val { color: var(--primary-color, #ff9800); font-variant-numeric: tabular-nums; }
        .slider-row { display: flex; align-items: center; gap: 8px; }
        .cap { font-size: 10px; color: var(--secondary-text-color, #727272); width: 34px; }
        .cap.hi { text-align: right; }
        input[type="range"] { flex: 1; accent-color: var(--primary-color, #ff9800); height: 24px; cursor: pointer; }
        input[type="range"]:disabled { opacity: .4; cursor: default; }
        .divider { height: 1px; background: var(--divider-color, #e0e0e0); margin: 12px 2px; }
        .slots { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-top: 6px; }
        .slot { padding: 8px 4px; border-radius: 10px; border: 1px solid var(--divider-color, #ddd); background: var(--secondary-background-color, #f3f6f9); color: var(--primary-text-color, #21313c); font-size: 11px; cursor: pointer; text-align: center; }
        .slot.on { background: var(--primary-color, #ff9800); border-color: var(--primary-color, #ff9800); color: #fff; font-weight: 700; }
        .foot { margin-top: 10px; font-size: 10px; color: var(--secondary-text-color, #727272); }
      </style>
      <ha-card>
        <div class="head"><div class="title">${this._esc(this._config.title)}</div></div>
        <div class="note">Battery save and Inverter performance are inversely proportional to each other.</div>

        ${slider("Performance", perf, perfId, 1, 7, "Low", "High")}
        ${slider("Battery Backup", backup, backupId, 1, 7, "Low", "High")}

        <div class="divider"></div>

        <div class="section-label">Night Forced Cut time</div>
        <div class="slots">${chips}</div>

        <div class="foot">Setting one moves the other — both write the same inverter register.</div>
      </ha-card>
    `;

    this.shadowRoot.querySelectorAll('input[type="range"]').forEach((el) => {
      el.addEventListener("change", () => {
        const entityId = el.getAttribute("data-entity");
        if (!entityId || !this._hass) return;
        this._hass.callService("number", "set_value", { entity_id: entityId, value: Number(el.value) });
      });
    });
    this.shadowRoot.querySelectorAll(".slot").forEach((btn) => {
      btn.addEventListener("click", () => {
        const entityId = btn.getAttribute("data-entity");
        const option = btn.getAttribute("data-option");
        if (!entityId || !option || !this._hass) return;
        this._hass.callService("select", "select_option", { entity_id: entityId, option });
      });
    });
  }
}

if (!customElements.get("vguard-reserve-card")) { customElements.define("vguard-reserve-card", VGuardReserveCard); }

window.customCards = window.customCards || [];
window.customCards.push({
  type: "vguard-reserve-card",
  name: "V-Guard Reserve Power Card",
  preview: true,
  description: "Maximum Backup / Performance inverse sliders and the night forced cut time picker, matching the app's Reserve Power screen"
});

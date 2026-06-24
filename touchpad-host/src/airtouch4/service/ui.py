"""Ingress UI for the AirTouch runtime service."""

from __future__ import annotations


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AirTouch 4</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f3f6f8;
      --panel: #ffffff;
      --panel-soft: #f8fafb;
      --ink: #16212c;
      --muted: #657381;
      --line: #d9e2e8;
      --ok: #14795a;
      --bad: #b42318;
      --warn: #996700;
      --accent: #0f6e8e;
      --accent-soft: #e6f4f7;
      --cool: #2d6cdf;
      --warm: #b45f06;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.42 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    header {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 14px;
      align-items: center;
      padding: 14px 18px 10px;
      background: #16212c;
      color: #fff;
      border-bottom: 3px solid var(--accent);
    }
    h1 { margin: 0; font-size: 21px; font-weight: 720; }
    h2 { margin: 0 0 10px; font-size: 15px; font-weight: 720; }
    h3 { margin: 0 0 8px; font-size: 14px; font-weight: 720; }
    main {
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 14px;
      padding: 14px;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px;
      min-width: 0;
    }
    .status {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
      font-weight: 680;
      white-space: nowrap;
    }
    .dot {
      width: 10px;
      height: 10px;
      border-radius: 999px;
      background: var(--warn);
      flex: 0 0 auto;
    }
    .ok .dot { background: var(--ok); }
    .bad .dot { background: var(--bad); }
    .nav {
      grid-column: 1 / -1;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .nav button {
      min-height: 34px;
      border-color: rgba(255,255,255,.24);
      background: rgba(255,255,255,.08);
      color: #fff;
    }
    .nav button.active {
      background: #fff;
      color: var(--ink);
      border-color: #fff;
    }
    .view { display: none; }
    .view.active { display: grid; gap: 14px; }
    .control-grid { display: grid; gap: 14px; }
    .control-head {
      display: grid;
      grid-template-columns: minmax(0, .88fr) minmax(320px, 1.12fr);
      gap: 14px;
      align-items: stretch;
    }
    .ac-selector {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 8px;
      margin-bottom: 10px;
    }
    .ac-select-card {
      min-height: 74px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px;
      background: #fff;
      color: var(--ink);
      text-align: left;
      display: grid;
      gap: 4px;
      align-content: start;
    }
    .ac-select-card.active {
      border-color: var(--accent);
      background: var(--accent-soft);
      color: var(--ink);
    }
    .ac-board {
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 12px;
    }
    .ac-panel {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 14px;
      background: linear-gradient(180deg, #f8fbfc 0%, #fff 82%);
      display: grid;
      gap: 14px;
      min-height: 260px;
    }
    .ac-panel.on {
      border-color: #87c7b0;
      background: linear-gradient(180deg, #f1fbf7 0%, #fff 82%);
    }
    .ac-top {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 10px;
      align-items: start;
    }
    .ac-name { font-size: 24px; font-weight: 780; overflow-wrap: anywhere; }
    .ac-temp {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    .reading {
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      background: #fff;
    }
    .label {
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: .02em;
    }
    .big {
      margin-top: 3px;
      font-size: 34px;
      line-height: 1.05;
      font-weight: 780;
    }
    .small-value {
      margin-top: 3px;
      font-size: 20px;
      font-weight: 740;
    }
    .ac-controls {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }
    .control-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    .groups-board {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
      gap: 10px;
    }
    .zone-toolbar {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 10px;
    }
    .zone-pages {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .group-tile {
      min-height: 190px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px;
      background: #fff;
      display: grid;
      grid-template-rows: auto 1fr auto auto;
      gap: 10px;
    }
    .group-tile.on {
      border-color: #86c6b0;
      background: linear-gradient(180deg, #f4fbf8 0%, #fff 76%);
    }
    .group-tile.spill {
      border-color: #dec879;
      background: linear-gradient(180deg, #fffbea 0%, #fff 76%);
    }
    .group-head {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 8px;
      align-items: start;
    }
    .group-name {
      font-size: 17px;
      font-weight: 780;
      overflow-wrap: anywhere;
    }
    .group-num {
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
      margin-top: 2px;
    }
    .group-body {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      align-content: center;
    }
    .damper { grid-column: 1 / -1; }
    .bar {
      height: 8px;
      border-radius: 999px;
      background: #e6ebef;
      overflow: hidden;
      margin-top: 5px;
    }
    .bar-fill {
      height: 100%;
      width: 0%;
      background: var(--accent);
    }
    .tile-foot {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      min-height: 24px;
      align-items: center;
    }
    .tile-actions {
      display: flex;
      gap: 8px;
      align-items: center;
      justify-content: flex-end;
      min-height: 34px;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 24px;
      padding: 2px 9px;
      border-radius: 999px;
      border: 1px solid var(--line);
      color: var(--muted);
      background: #fff;
      font-size: 12px;
      font-weight: 680;
      white-space: nowrap;
    }
    .pill.on { color: #fff; background: var(--ok); border-color: var(--ok); }
    .pill.warn { color: #fff; background: var(--warn); border-color: var(--warn); }
    .pill.cool { color: #fff; background: var(--cool); border-color: var(--cool); }
    button {
      min-height: 34px;
      border: 1px solid var(--accent);
      border-radius: 5px;
      padding: 5px 12px;
      background: var(--accent);
      color: #fff;
      font: inherit;
      font-weight: 720;
      cursor: pointer;
    }
    button:hover { filter: brightness(.95); }
    button:disabled { cursor: progress; opacity: .62; }
    button.secondary {
      border-color: var(--line);
      background: #fff;
      color: var(--ink);
    }
    button.option {
      border-color: var(--line);
      background: #fff;
      color: var(--ink);
    }
    button.option.active {
      border-color: var(--accent);
      background: var(--accent-soft);
      color: var(--accent);
    }
    .split {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 14px;
    }
    .cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      gap: 10px;
    }
    .card {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      background: var(--panel-soft);
      min-height: 96px;
      display: grid;
      gap: 8px;
      align-content: start;
    }
    .card-title { font-size: 16px; font-weight: 740; overflow-wrap: anywhere; }
    table {
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
    }
    th, td {
      border-bottom: 1px solid var(--line);
      padding: 7px 6px;
      text-align: left;
      vertical-align: top;
      overflow-wrap: anywhere;
    }
    th {
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
      text-transform: uppercase;
      letter-spacing: .02em;
      background: var(--panel-soft);
    }
    tbody tr:last-child td { border-bottom: 0; }
    .service-grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 14px;
    }
    .diagnostics {
      grid-column: 1 / -1;
    }
    .muted { color: var(--muted); }
    .json {
      white-space: pre-wrap;
      font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
      font-size: 12px;
      max-height: 260px;
      overflow: auto;
      background: var(--panel-soft);
      border: 1px solid var(--line);
      border-radius: 5px;
      padding: 8px;
    }
    @media (max-width: 1040px) {
      .control-head,
      .split,
      .service-grid {
        grid-template-columns: 1fr;
      }
    }
    @media (max-width: 620px) {
      header { grid-template-columns: 1fr; }
      main { padding: 10px; gap: 10px; }
      section { padding: 10px; }
      .ac-temp,
      .ac-controls,
      .group-body {
        grid-template-columns: 1fr 1fr;
      }
      .groups-board { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>AirTouch 4</h1>
    <div id="status" class="status"><span class="dot"></span><span>Connecting</span></div>
    <nav class="nav" aria-label="Primary">
      <button type="button" class="active" data-view-button="control">Control</button>
      <button type="button" data-view-button="programs">Favourites & Programs</button>
      <button type="button" data-view-button="service">Service</button>
    </nav>
  </header>
  <main>
    <div id="view-control" class="view active">
      <div class="control-grid">
        <section>
          <h2>Air Conditioner</h2>
          <div class="ac-selector" id="ac-selector"></div>
          <div class="ac-board" id="acs"></div>
        </section>
        <section>
          <h2>Zones</h2>
          <div class="zone-toolbar">
            <div class="muted" id="zone-context"></div>
            <div class="zone-pages" id="zone-pages"></div>
          </div>
          <div class="groups-board" id="groups"></div>
        </section>
      </div>
    </div>

    <div id="view-programs" class="view">
      <div class="split">
        <section>
          <h2>Favourites</h2>
          <div class="cards" id="favourites"></div>
        </section>
        <section>
          <h2>Programs</h2>
          <div class="cards" id="programs"></div>
        </section>
      </div>
    </div>

    <div id="view-service" class="view">
      <div class="service-grid">
        <section>
          <h2>Sensors</h2>
          <table>
            <thead><tr><th>Sensor</th><th>Name</th><th>Temp</th><th>Status</th></tr></thead>
            <tbody id="sensors"></tbody>
          </table>
        </section>
        <section>
          <h2>Setup</h2>
          <div class="json" id="system">{}</div>
        </section>
        <section class="diagnostics">
          <h2>Diagnostics</h2>
          <div class="cards" id="metrics"></div>
          <table>
            <thead><tr><th>Type</th><th>Command</th><th>Message</th></tr></thead>
            <tbody id="events"></tbody>
          </table>
        </section>
      </div>
    </div>
  </main>
  <script>
    const $ = (id) => document.getElementById(id);
    const API_ROOT = window.location.pathname.replace(/\\/+$/, "");
    const pendingGroups = new Set();
    const pendingAcs = new Set();
    const pendingFavourites = new Set();
    let selectedAc = 0;
    let zonePage = 0;

    function apiPath(path) {
      return `${API_ROOT}/api/${path}`;
    }

    function text(value, fallback = "-") {
      return value === undefined || value === null || value === "" ? fallback : String(value);
    }

    function escapeHtml(value) {
      return text(value).replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }[char]));
    }

    function row(cells) {
      return "<tr>" + cells.map((cell) => "<td>" + escapeHtml(cell) + "</td>").join("") + "</tr>";
    }

    function metric(label, value) {
      return `<div class="card"><div class="label">${escapeHtml(label)}</div><div class="small-value">${escapeHtml(value)}</div></div>`;
    }

    function pct(value) {
      const num = Number(value);
      if (!Number.isFinite(num)) return null;
      return Math.max(0, Math.min(100, Math.round(num)));
    }

    function temp(value) {
      return value === undefined || value === null ? "-" : `${value} C`;
    }

    function modeName(value) {
      const modes = {0: "auto", 1: "heat", 2: "dry", 3: "fan", 4: "cool", 7: "-"};
      return modes[value] || text(value);
    }

    function fanName(value) {
      const fans = {0: "auto", 1: "low", 2: "med", 3: "high", 7: "-"};
      return fans[value] || text(value);
    }

    function groupNamesFromBitmap(groups, low, high) {
      const names = [];
      for (let i = 0; i < 8; i += 1) {
        if (low & (1 << i)) names.push((groups[i] && groups[i].name) || `Zone ${i + 1}`);
      }
      for (let i = 0; i < 8; i += 1) {
        if (high & (1 << i)) names.push((groups[i + 8] && groups[i + 8].name) || `Zone ${i + 9}`);
      }
      return names;
    }

    function visibleAcs(state) {
      const acs = state.acs || {};
      const count = Number(state.system && state.system.ac_count);
      let entries = Object.entries(acs)
        .filter(([_id, ac]) => ac.base || ac.status || ac.runtime)
        .sort(([a], [b]) => Number(a) - Number(b));
      if (Number.isInteger(count) && count > 0) {
        entries = entries.filter(([id, ac]) => Number(id) < count || ac.base);
        for (let i = 0; i < count; i += 1) {
          if (!entries.some(([id]) => Number(id) === i)) entries.push([String(i), {}]);
        }
        entries.sort(([a], [b]) => Number(a) - Number(b));
      }
      return entries;
    }

    function zoneEntriesForAc(state, acId) {
      const allGroups = state.active_groups || state.groups || {};
      const entries = Object.entries(allGroups).sort(([a], [b]) => Number(a) - Number(b));
      const oneDuct = !!(state.system && state.system.one_duct_system);
      const ac = (state.acs || {})[acId] || {};
      const base = ac.base || {};
      const settings = ac.settings || {};
      if (oneDuct || !Number.isInteger(base.group_start) || !Number.isInteger(base.group_count)) {
        return settings.hide_spill_group
          ? entries.filter(([_id, group]) => !(group.spill_configured || (group.status || {}).spill_on))
          : entries;
      }
      const start = base.group_start;
      const end = start + base.group_count;
      return entries.filter(([id, group]) => {
        const number = Number(id);
        if (number < start || number >= end) return false;
        return !(settings.hide_spill_group && (group.spill_configured || (group.status || {}).spill_on));
      });
    }

    function setStatus(health) {
      const el = $("status");
      el.className = "status " + (health.ok ? "ok" : "bad");
      el.lastElementChild.textContent = health.ok ? "Running" : text(health.error, text(health.status, "Error"));
    }

    function acCard(id, ac) {
      const status = ac.status || {};
      const base = ac.base || {};
      const settings = ac.settings || {};
      const power = status.power_on === true ? "on" : status.power_on === false ? "off" : "-";
      const isOn = power === "on";
      const pending = pendingAcs.has(String(id));
      const mode = Number.isInteger(status.mode) ? status.mode : null;
      const fan = Number.isInteger(status.fan) ? status.fan : null;
      const setpoint = Number.isInteger(status.setpoint) ? status.setpoint : null;
      const modes = [[0, "Auto"], [1, "Heat"], [2, "Dry"], [3, "Fan"], [4, "Cool"]];
      const fans = [[0, "Auto"], [1, "Low"], [2, "Med"], [3, "High"]];
      return `
        <article class="ac-panel ${isOn ? "on" : ""}">
          <div class="ac-top">
            <div>
              <div class="ac-name">${escapeHtml(base.name || `AC ${Number(id) + 1}`)}</div>
              <div class="muted">${escapeHtml(modeName(mode))} mode, ${escapeHtml(fanName(fan))} fan</div>
            </div>
            <span class="${isOn ? "pill on" : "pill"}">${escapeHtml(power)}</span>
          </div>
          <div class="ac-temp">
            <div class="reading">
              <div class="label">Setpoint</div>
              <div class="big">${escapeHtml(temp(setpoint))}</div>
            </div>
            <div class="reading">
              <div class="label">Range</div>
              <div class="small-value">${escapeHtml(text(settings.min_setpoint))}-${escapeHtml(text(settings.max_setpoint))} C</div>
            </div>
          </div>
          <div>
            <div class="label">Mode</div>
            <div class="control-row">${modes.map(([value, label]) => `<button type="button" class="option ${mode === value ? "active" : ""}" data-action="ac-status" data-ac="${escapeHtml(id)}" data-mode="${value}" ${pending ? "disabled" : ""}>${label}</button>`).join("")}</div>
          </div>
          <div>
            <div class="label">Fan</div>
            <div class="control-row">${fans.map(([value, label]) => `<button type="button" class="option ${fan === value ? "active" : ""}" data-action="ac-status" data-ac="${escapeHtml(id)}" data-fan="${value}" ${pending ? "disabled" : ""}>${label}</button>`).join("")}</div>
          </div>
          <div class="ac-controls">
            <button type="button" data-action="ac-status" data-ac="${escapeHtml(id)}" data-power-on="${isOn ? "false" : "true"}" ${pending ? "disabled" : ""}>${escapeHtml(pending ? "Sending" : (isOn ? "Turn off" : "Turn on"))}</button>
            <button type="button" class="secondary" data-action="ac-status" data-ac="${escapeHtml(id)}" data-setpoint="${setpoint === null ? "" : setpoint + 1}" ${pending || setpoint === null ? "disabled" : ""}>Set +</button>
            <button type="button" class="secondary" data-action="ac-status" data-ac="${escapeHtml(id)}" data-setpoint="${setpoint === null ? "" : setpoint - 1}" ${pending || setpoint === null ? "disabled" : ""}>Set -</button>
          </div>
        </article>`;
    }

    function acSelectorCard(id, ac) {
      const status = ac.status || {};
      const base = ac.base || {};
      const power = status.power_on === true ? "on" : status.power_on === false ? "off" : "-";
      return `
        <button type="button" class="ac-select-card ${Number(id) === selectedAc ? "active" : ""}" data-action="select-ac" data-ac="${escapeHtml(id)}">
          <span class="card-title">${escapeHtml(base.name || `AC ${Number(id) + 1}`)}</span>
          <span class="muted">${escapeHtml(power)} &middot; ${escapeHtml(modeName(status.mode))} &middot; ${escapeHtml(temp(status.setpoint))}</span>
        </button>`;
    }

    function groupTile(id, group) {
      const number = Number(id) + 1;
      const status = group.status || {};
      const grouping = group.grouping || {};
      const damper = pct(status.percentage);
      const power = status.power_name || (status.power_code === 1 ? "on" : "off");
      const isOn = power === "on";
      const isSpill = group.spill_configured || status.spill_on;
      const pending = pendingGroups.has(String(id));
      const classes = ["group-tile"];
      if (isOn) classes.push("on");
      if (isSpill) classes.push("spill");
      const badges = [];
      badges.push(`<span class="${isOn ? "pill on" : "pill"}">${escapeHtml(power)}</span>`);
      if (isSpill) badges.push('<span class="pill warn">spill</span>');
      if (status.sensor_control) badges.push('<span class="pill cool">sensor</span>');
      if (grouping.thermostat_name) badges.push(`<span class="pill">${escapeHtml(grouping.thermostat_name)}</span>`);
      return `
        <article class="${classes.join(" ")}">
          <div class="group-head">
            <div>
              <div class="group-name">${escapeHtml(group.name || `Zone ${number}`)}</div>
              <div class="group-num">Zone ${number}</div>
            </div>
            <span class="pill">${escapeHtml(damper === null ? "-" : `${damper}%`)}</span>
          </div>
          <div class="group-body">
            <div class="reading">
              <div class="label">Room</div>
              <div class="big">${escapeHtml(temp(status.temperature))}</div>
            </div>
            <div class="reading">
              <div class="label">Set</div>
              <div class="small-value">${escapeHtml(temp(status.setpoint))}</div>
              <div class="muted">${escapeHtml(status.has_sensor ? "mapped" : "no sensor")}</div>
            </div>
            <div class="damper">
              <div class="label">Damper</div>
              <div class="bar"><div class="bar-fill" style="width:${damper === null ? 0 : damper}%"></div></div>
            </div>
          </div>
          <div class="tile-foot">${badges.join("")}</div>
          <div class="tile-actions">
            <button
              type="button"
              class="${isOn ? "secondary" : ""}"
              data-action="group-power"
              data-group="${escapeHtml(id)}"
              data-on="${isOn ? "false" : "true"}"
              data-sensor-control="${status.sensor_control ? "true" : "false"}"
              data-setpoint="${escapeHtml(status.setpoint ?? "")}"
              data-percentage="${escapeHtml(status.percentage ?? "")}"
              ${pending ? "disabled" : ""}
            >${escapeHtml(pending ? "Sending" : (isOn ? "Off" : "On"))}</button>
          </div>
        </article>`;
    }

    function renderFavourites(favourites, groups) {
      const entries = Object.entries(favourites || {}).sort(([a], [b]) => Number(a) - Number(b));
      $("favourites").innerHTML = entries.map(([id, favourite]) => {
        const groupNames = groupNamesFromBitmap(groups, favourite.groups_1_8_bitmap || 0, favourite.groups_9_16_bitmap || 0);
        const pending = pendingFavourites.has(String(id));
        return `
          <article class="card">
            <div class="card-title">${escapeHtml(favourite.name || `Favourite ${Number(id) + 1}`)}</div>
            <div class="muted">${escapeHtml(groupNames.length ? groupNames.join(", ") : "No zones selected")}</div>
            <button type="button" data-action="active-favourite" data-favourite="${escapeHtml(id)}" ${pending ? "disabled" : ""}>${escapeHtml(pending ? "Sending" : "Apply")}</button>
          </article>`;
      }).join("") || '<div class="muted">No favourite data</div>';
    }

    function renderPrograms(programs, groups) {
      const entries = Object.entries(programs || {}).sort(([a], [b]) => Number(a) - Number(b));
      $("programs").innerHTML = entries.map(([_id, program]) => {
        const groupNames = groupNamesFromBitmap(groups, program.groups_1_8_bitmap || 0, program.groups_9_16_bitmap || 0);
        const onTimer = program.on_timer || {};
        const offTimer = program.off_timer || {};
        return `
          <article class="card">
            <div class="card-title">${escapeHtml(program.name || `Program ${(program.program ?? 0) + 1}`)}</div>
            <div class="muted">${escapeHtml(groupNames.length ? groupNames.join(", ") : "No zones selected")}</div>
            <div><span class="${program.enabled ? "pill on" : "pill"}">${escapeHtml(program.enabled ? "enabled" : "off")}</span></div>
            <div class="muted">On ${escapeHtml(onTimer.enabled ? `${onTimer.hour}:${String(onTimer.minute).padStart(2, "0")}` : "-")} / Off ${escapeHtml(offTimer.enabled ? `${offTimer.hour}:${String(offTimer.minute).padStart(2, "0")}` : "-")}</div>
          </article>`;
      }).join("") || '<div class="muted">No program data</div>';
    }

    function renderState(payload) {
      const controller = payload.controller || {};
      const runtime = (payload.runtime && payload.runtime.runtime) || {};
      const transactions = (payload.runtime && payload.runtime.transactions) || {};
      const state = (payload.runtime && payload.runtime.state) || {};
      const config = controller.config || {};
      const acEntries = visibleAcs(state);
      if (!acEntries.some(([id]) => Number(id) === selectedAc)) selectedAc = Number(acEntries[0] && acEntries[0][0]) || 0;

      $("metrics").innerHTML = [
        metric("Transport", config.transport),
        metric("Endpoint", config.transport === "tcp_serial" ? `${config.tcp_host}:${config.tcp_port}` : config.port),
        metric("Address", runtime.src),
        metric("Boot", runtime.boot_complete ? "complete" : "pending"),
        metric("RX / TX", `${runtime.rx_count || 0} / ${runtime.tx_count || 0}`),
        metric("Transactions", `${(transactions.completed || []).length} ok, ${(transactions.failed || []).length} fail`)
      ].join("");

      $("ac-selector").innerHTML = acEntries.length > 1
        ? acEntries.map(([id, ac]) => acSelectorCard(id, ac)).join("")
        : "";

      const selectedAcRecord = (state.acs || {})[selectedAc] || {};
      $("acs").innerHTML = acEntries.length
        ? acCard(String(selectedAc), selectedAcRecord)
        : '<div class="muted">No AC data</div>';

      const groups = state.active_groups || state.groups || {};
      const zoneEntries = zoneEntriesForAc(state, selectedAc);
      const pageCount = Math.max(1, Math.ceil(zoneEntries.length / 8));
      if (zonePage >= pageCount) zonePage = pageCount - 1;
      const pageStart = zonePage * 8;
      const pageEntries = zoneEntries.slice(pageStart, pageStart + 8);
      const selectedBase = selectedAcRecord.base || {};
      $("zone-context").textContent = acEntries.length > 1
        ? `${selectedBase.name || `AC ${selectedAc + 1}`} zones`
        : `${zoneEntries.length} configured zones`;
      $("zone-pages").innerHTML = pageCount > 1
        ? Array.from({length: pageCount}, (_value, index) => `<button type="button" class="option ${index === zonePage ? "active" : ""}" data-action="zone-page" data-page="${index}">${(index * 8) + 1}-${Math.min((index + 1) * 8, zoneEntries.length)}</button>`).join("")
        : "";
      $("groups").innerHTML = pageEntries
        .map(([id, group]) => groupTile(id, group))
        .join("") || '<div class="muted">No zone data</div>';

      renderFavourites(state.favourites || {}, groups);
      renderPrograms(state.programs || {}, groups);

      const sensors = state.sensors || {};
      $("sensors").innerHTML = Object.entries(sensors)
        .sort(([a], [b]) => Number(a) - Number(b))
        .map(([id, sensor]) => row([
          id,
          sensor.sensor_name,
          temp(sensor.temperature),
          sensor.status || (sensor.present === false ? "missing" : sensor.listed ? "listed" : "-")
        ])).join("") || row(["-", "No sensor data", "-", "-"]);

      $("system").textContent = JSON.stringify({
        name: state.system && state.system.system_name,
        group_count: state.system && state.system.group_count,
        sensors: state.system && state.system.sensor_addresses,
        supply_air: state.system && state.system.supply_air,
        spill: state.system && state.system.spill,
        service: state.service,
        password: state.password,
        last_led: state.last_led
      }, null, 2);
    }

    function renderEvents(payload) {
      const events = (payload.events || []).slice(-10).reverse();
      $("events").innerHTML = events.map((event) => row([
        event.event,
        event.cmd_name || event.cmd,
        event.message || (event.transaction && event.transaction.name) || ""
      ])).join("") || row(["-", "-", "No events yet"]);
    }

    async function sendCommand(action, data) {
      const response = await fetch(apiPath("command"), {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({action, data})
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || `Command failed: ${response.status}`);
      }
      return response.json();
    }

    document.querySelector(".nav").addEventListener("click", (event) => {
      const button = event.target.closest("button[data-view-button]");
      if (!button) return;
      const view = button.dataset.viewButton;
      document.querySelectorAll("[data-view-button]").forEach((item) => item.classList.toggle("active", item === button));
      document.querySelectorAll(".view").forEach((item) => item.classList.toggle("active", item.id === `view-${view}`));
    });

    $("groups").addEventListener("click", async (event) => {
      const button = event.target.closest("button[data-action='group-power']");
      if (!button) return;
      const group = button.dataset.group;
      pendingGroups.add(group);
      button.disabled = true;
      button.textContent = "Sending";
      try {
        await sendCommand("group_power", {
          group: Number(group),
          on: button.dataset.on === "true",
          sensor_control: button.dataset.sensorControl === "true",
          setpoint: Number(button.dataset.setpoint),
          percentage: Number(button.dataset.percentage)
        });
        setTimeout(refresh, 300);
      } catch (err) {
        setStatus({ok: false, error: err.message});
      } finally {
        setTimeout(() => {
          pendingGroups.delete(group);
          refresh();
        }, 900);
      }
    });

    $("acs").addEventListener("click", async (event) => {
      const button = event.target.closest("button[data-action='ac-status']");
      if (!button) return;
      const ac = button.dataset.ac;
      const data = {ac: Number(ac)};
      if (button.dataset.powerOn !== undefined) data.power_on = button.dataset.powerOn === "true";
      if (button.dataset.mode !== undefined) data.mode = Number(button.dataset.mode);
      if (button.dataset.fan !== undefined) data.fan = Number(button.dataset.fan);
      if (button.dataset.setpoint !== undefined && button.dataset.setpoint !== "") data.setpoint = Number(button.dataset.setpoint);
      pendingAcs.add(ac);
      try {
        await sendCommand("ac_status", data);
        setTimeout(refresh, 300);
      } catch (err) {
        setStatus({ok: false, error: err.message});
      } finally {
        setTimeout(() => {
          pendingAcs.delete(ac);
          refresh();
        }, 900);
      }
    });

    $("ac-selector").addEventListener("click", (event) => {
      const button = event.target.closest("button[data-action='select-ac']");
      if (!button) return;
      selectedAc = Number(button.dataset.ac);
      zonePage = 0;
      refresh();
    });

    $("zone-pages").addEventListener("click", (event) => {
      const button = event.target.closest("button[data-action='zone-page']");
      if (!button) return;
      zonePage = Number(button.dataset.page);
      refresh();
    });

    $("favourites").addEventListener("click", async (event) => {
      const button = event.target.closest("button[data-action='active-favourite']");
      if (!button) return;
      const favourite = button.dataset.favourite;
      pendingFavourites.add(favourite);
      try {
        await sendCommand("active_favourite", {favourite: Number(favourite)});
        setTimeout(refresh, 300);
      } catch (err) {
        setStatus({ok: false, error: err.message});
      } finally {
        setTimeout(() => {
          pendingFavourites.delete(favourite);
          refresh();
        }, 900);
      }
    });

    async function refresh() {
      try {
        const [health, state, events] = await Promise.all([
          fetch(apiPath("health")).then((r) => r.json()),
          fetch(apiPath("state")).then((r) => r.json()),
          fetch(apiPath("events")).then((r) => r.json())
        ]);
        setStatus(health);
        renderState(state);
        renderEvents(events);
      } catch (err) {
        setStatus({ok: false, error: err.message});
      }
    }

    refresh();
    setInterval(refresh, 1500);
  </script>
</body>
</html>
"""

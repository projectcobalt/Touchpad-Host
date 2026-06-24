"""Minimal ingress UI for the AirTouch runtime service."""

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
      --bg: #f4f6f8;
      --panel: #ffffff;
      --panel-soft: #f9fbfc;
      --ink: #15202b;
      --muted: #667380;
      --line: #d9e1e8;
      --ok: #13795b;
      --bad: #b42318;
      --warn: #9a6700;
      --accent: #106f8f;
      --accent-soft: #e7f4f7;
      --cool: #2d6cdf;
      --off: #8a96a3;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.42 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    header {
      display: flex;
      gap: 16px;
      align-items: center;
      justify-content: space-between;
      padding: 14px 18px;
      background: #15202b;
      color: #fff;
      border-bottom: 3px solid var(--accent);
    }
    h1 { margin: 0; font-size: 20px; font-weight: 650; }
    h2 { margin: 0 0 10px; font-size: 15px; font-weight: 650; }
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
      font-weight: 650;
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
    .topline {
      display: grid;
      grid-template-columns: repeat(6, minmax(110px, 1fr));
      gap: 10px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 5px;
      padding: 9px;
      min-height: 58px;
      background: var(--panel-soft);
    }
    .label {
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: .02em;
    }
    .value {
      margin-top: 5px;
      font-size: 17px;
      font-weight: 650;
      overflow-wrap: anywhere;
    }
    .ac-strip {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 10px;
    }
    .ac-panel {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      background: var(--panel-soft);
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px;
      align-items: start;
    }
    .ac-name { font-size: 17px; font-weight: 700; }
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
      font-weight: 650;
      white-space: nowrap;
    }
    .pill.on {
      color: #fff;
      background: var(--ok);
      border-color: var(--ok);
    }
    .pill.warn {
      color: #fff;
      background: var(--warn);
      border-color: var(--warn);
    }
    .pill.cool {
      color: #fff;
      background: var(--cool);
      border-color: var(--cool);
    }
    .groups-board {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 10px;
    }
    .group-tile {
      min-height: 168px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 11px;
      background: #fff;
      display: grid;
      grid-template-rows: auto 1fr auto;
      gap: 10px;
    }
    .group-tile.on {
      border-color: #86c6b0;
      background: linear-gradient(180deg, #f4fbf8 0%, #fff 74%);
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
      font-size: 16px;
      font-weight: 750;
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
    .reading {
      min-width: 0;
    }
    .reading .big {
      font-size: 28px;
      line-height: 1.05;
      font-weight: 760;
      margin-top: 2px;
    }
    .reading .small-value {
      font-size: 18px;
      font-weight: 700;
      margin-top: 4px;
    }
    .damper {
      grid-column: 1 / -1;
    }
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
    .lower {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(360px, .8fr);
      gap: 14px;
    }
    .muted { color: var(--muted); }
    .json {
      white-space: pre-wrap;
      font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
      font-size: 12px;
      max-height: 230px;
      overflow: auto;
      background: var(--panel-soft);
      border: 1px solid var(--line);
      border-radius: 5px;
      padding: 8px;
    }
    @media (max-width: 940px) {
      header { align-items: flex-start; flex-direction: column; }
      .topline { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .lower { grid-template-columns: 1fr; }
    }
    @media (max-width: 520px) {
      main { padding: 10px; gap: 10px; }
      section { padding: 10px; }
      .topline { grid-template-columns: 1fr; }
      .groups-board { grid-template-columns: 1fr; }
      .group-body { grid-template-columns: 1fr 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>AirTouch 4</h1>
    <div id="status" class="status"><span class="dot"></span><span>Connecting</span></div>
  </header>
  <main>
    <section>
      <div class="topline" id="metrics"></div>
    </section>
    <section>
      <h2>Air Conditioner</h2>
      <div class="ac-strip" id="acs"></div>
    </section>
    <section>
      <h2>Groups</h2>
      <div class="groups-board" id="groups"></div>
    </section>
    <div class="lower">
      <section>
        <h2>Sensors</h2>
        <table>
          <thead><tr><th>Sensor</th><th>Name</th><th>Temp</th><th>Status</th></tr></thead>
          <tbody id="sensors"></tbody>
        </table>
      </section>
      <section>
        <h2>Activity</h2>
        <table>
          <thead><tr><th>Type</th><th>Command</th><th>Message</th></tr></thead>
          <tbody id="events"></tbody>
        </table>
      </section>
    </div>
    <section>
      <h2>System</h2>
      <div class="json" id="system">{}</div>
    </section>
  </main>
  <script>
    const $ = (id) => document.getElementById(id);

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
      return `<div class="metric"><div class="label">${escapeHtml(label)}</div><div class="value">${escapeHtml(value)}</div></div>`;
    }

    function pct(value) {
      const num = Number(value);
      if (!Number.isFinite(num)) return null;
      return Math.max(0, Math.min(100, Math.round(num)));
    }

    function temp(value) {
      return value === undefined || value === null ? "-" : `${value} deg`;
    }

    function modeName(value) {
      const modes = {0: "auto", 1: "heat", 2: "dry", 3: "fan", 4: "cool"};
      return modes[value] || text(value);
    }

    function fanName(value) {
      const fans = {0: "auto", 1: "low", 2: "med", 3: "high"};
      return fans[value] || text(value);
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
      const pillClass = power === "on" ? "pill on" : "pill";
      return `
        <div class="ac-panel">
          <div>
            <div class="ac-name">${escapeHtml(base.name || `AC ${Number(id) + 1}`)}</div>
            <div class="muted">Set ${escapeHtml(status.setpoint)} deg · ${escapeHtml(modeName(status.mode))} · ${escapeHtml(fanName(status.fan))}</div>
            <div class="muted">Range ${escapeHtml(settings.min_setpoint)}-${escapeHtml(settings.max_setpoint)} deg</div>
          </div>
          <span class="${pillClass}">${escapeHtml(power)}</span>
        </div>`;
    }

    function groupTile(id, group) {
      const number = Number(id) + 1;
      const status = group.status || {};
      const grouping = group.grouping || {};
      const damper = pct(status.percentage);
      const power = status.power_name || (status.power_code === 1 ? "on" : "off");
      const isOn = power === "on";
      const isSpill = group.spill_configured || status.spill_on;
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
              <div class="group-name">${escapeHtml(group.name || `Group ${number}`)}</div>
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
        </article>`;
    }

    function renderState(payload) {
      const controller = payload.controller || {};
      const runtime = (payload.runtime && payload.runtime.runtime) || {};
      const transactions = (payload.runtime && payload.runtime.transactions) || {};
      const state = (payload.runtime && payload.runtime.state) || {};
      const config = controller.config || {};
      $("metrics").innerHTML = [
        metric("Transport", config.transport),
        metric("Endpoint", config.transport === "tcp_serial" ? `${config.tcp_host}:${config.tcp_port}` : config.port),
        metric("Address", runtime.src),
        metric("Boot", runtime.boot_complete ? "complete" : "pending"),
        metric("RX / TX", `${runtime.rx_count || 0} / ${runtime.tx_count || 0}`),
        metric("Transactions", `${(transactions.completed || []).length} ok, ${(transactions.failed || []).length} fail`)
      ].join("");

      const acs = state.acs || {};
      $("acs").innerHTML = Object.entries(acs)
        .sort(([a], [b]) => Number(a) - Number(b))
        .map(([id, ac]) => acCard(id, ac))
        .join("") || '<div class="muted">No AC data</div>';

      const groups = state.active_groups || state.groups || {};
      $("groups").innerHTML = Object.entries(groups)
        .sort(([a], [b]) => Number(a) - Number(b))
        .map(([id, group]) => groupTile(id, group))
        .join("") || '<div class="muted">No group data</div>';

      const sensors = state.sensors || {};
      $("sensors").innerHTML = Object.entries(sensors)
        .sort(([a], [b]) => Number(a) - Number(b))
        .map(([id, sensor]) => row([
          id,
          sensor.sensor_name,
          temp(sensor.temperature),
          sensor.status || (sensor.present === false ? "missing" : "-")
        ])).join("") || row(["-", "No sensor data", "-", "-"]);

      $("system").textContent = JSON.stringify({
        name: state.system && state.system.system_name,
        groups: state.system && state.system.group_count,
        sensors: state.system && state.system.sensor_addresses,
        spill: state.system && state.system.spill,
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

    async function refresh() {
      try {
        const [health, state, events] = await Promise.all([
          fetch("api/health").then((r) => r.json()),
          fetch("api/state").then((r) => r.json()),
          fetch("api/events").then((r) => r.json())
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

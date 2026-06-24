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
      --bg: #f6f7f9;
      --panel: #ffffff;
      --ink: #17202a;
      --muted: #5d6b7a;
      --line: #d9e0e7;
      --ok: #16835b;
      --bad: #b42318;
      --warn: #9a6700;
      --accent: #146c94;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    header {
      display: flex;
      gap: 16px;
      align-items: center;
      justify-content: space-between;
      padding: 14px 18px;
      background: #17202a;
      color: #fff;
      border-bottom: 3px solid var(--accent);
    }
    h1 { margin: 0; font-size: 20px; font-weight: 650; }
    h2 { margin: 0 0 10px; font-size: 15px; font-weight: 650; }
    main {
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) minmax(360px, .85fr);
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
    .span { grid-column: 1 / -1; }
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
    .grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(120px, 1fr));
      gap: 10px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 5px;
      padding: 9px;
      min-height: 62px;
      background: #fbfcfd;
    }
    .label {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .02em;
    }
    .value {
      margin-top: 5px;
      font-size: 18px;
      font-weight: 650;
      overflow-wrap: anywhere;
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
      background: #fbfcfd;
    }
    tbody tr:last-child td { border-bottom: 0; }
    .small { color: var(--muted); font-size: 12px; }
    .stack { display: grid; gap: 14px; }
    .json {
      white-space: pre-wrap;
      font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
      font-size: 12px;
      max-height: 320px;
      overflow: auto;
      background: #fbfcfd;
      border: 1px solid var(--line);
      border-radius: 5px;
      padding: 8px;
    }
    @media (max-width: 900px) {
      main { grid-template-columns: 1fr; }
      .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      header { align-items: flex-start; flex-direction: column; }
    }
    @media (max-width: 520px) {
      .grid { grid-template-columns: 1fr; }
      th:nth-child(4), td:nth-child(4) { display: none; }
    }
  </style>
</head>
<body>
  <header>
    <h1>AirTouch 4</h1>
    <div id="status" class="status"><span class="dot"></span><span>Connecting</span></div>
  </header>
  <main>
    <section class="span">
      <h2>Runtime</h2>
      <div class="grid" id="metrics"></div>
    </section>
    <section>
      <h2>Air Conditioners</h2>
      <table>
        <thead><tr><th>AC</th><th>Name</th><th>Power</th><th>Setpoint</th><th>Mode</th></tr></thead>
        <tbody id="acs"></tbody>
      </table>
    </section>
    <section>
      <h2>Groups</h2>
      <table>
        <thead><tr><th>Group</th><th>Name</th><th>State</th><th>Damper</th></tr></thead>
        <tbody id="groups"></tbody>
      </table>
    </section>
    <section>
      <h2>Sensors</h2>
      <table>
        <thead><tr><th>Sensor</th><th>Name</th><th>Temp</th><th>Status</th></tr></thead>
        <tbody id="sensors"></tbody>
      </table>
    </section>
    <section class="stack">
      <div>
        <h2>Events</h2>
        <table>
          <thead><tr><th>Type</th><th>Command</th><th>Message</th></tr></thead>
          <tbody id="events"></tbody>
        </table>
      </div>
      <div>
        <h2>System</h2>
        <div class="json" id="system">{}</div>
      </div>
    </section>
  </main>
  <script>
    const $ = (id) => document.getElementById(id);

    function text(value, fallback = "-") {
      return value === undefined || value === null || value === "" ? fallback : String(value);
    }

    function row(cells) {
      return "<tr>" + cells.map((cell) => "<td>" + text(cell) + "</td>").join("") + "</tr>";
    }

    function metric(label, value) {
      return `<div class="metric"><div class="label">${label}</div><div class="value">${text(value)}</div></div>`;
    }

    function setStatus(health) {
      const el = $("status");
      el.className = "status " + (health.ok ? "ok" : "bad");
      el.lastElementChild.textContent = health.ok ? "Running" : text(health.error, text(health.status, "Error"));
    }

    function renderState(payload) {
      const controller = payload.controller || {};
      const runtime = (payload.runtime && payload.runtime.runtime) || {};
      const state = (payload.runtime && payload.runtime.state) || {};
      const config = controller.config || {};
      $("metrics").innerHTML = [
        metric("Transport", config.transport),
        metric("Endpoint", config.transport === "tcp_serial" ? `${config.tcp_host}:${config.tcp_port}` : config.port),
        metric("Address", runtime.src),
        metric("Boot", runtime.boot_complete ? "complete" : "pending"),
        metric("RX", runtime.rx_count),
        metric("TX", runtime.tx_count),
        metric("Uptime", `${runtime.uptime_seconds || 0}s`),
        metric("Controller", controller.status)
      ].join("");

      const acs = state.acs || {};
      $("acs").innerHTML = Object.entries(acs).map(([id, ac]) => {
        const status = ac.status || {};
        const base = ac.base || {};
        return row([id, base.name, status.power_on === true ? "on" : status.power_on === false ? "off" : "-", status.setpoint, status.mode]);
      }).join("") || row(["-", "No AC data", "-", "-", "-"]);

      const groups = state.active_groups || state.groups || {};
      $("groups").innerHTML = Object.entries(groups).map(([id, group]) => {
        const status = group.status || {};
        const damper = status.open_percentage ?? status.damper_percentage ?? status.percentage;
        return row([Number(id) + 1, group.name, status.power_on === true ? "on" : status.power_on === false ? "off" : "-", damper]);
      }).join("") || row(["-", "No group data", "-", "-"]);

      const sensors = state.sensors || {};
      $("sensors").innerHTML = Object.entries(sensors).map(([id, sensor]) => {
        return row([id, sensor.sensor_name, sensor.temperature, sensor.status || (sensor.present === false ? "missing" : "-")]);
      }).join("") || row(["-", "No sensor data", "-", "-"]);

      $("system").textContent = JSON.stringify(state.system || {}, null, 2);
    }

    function renderEvents(payload) {
      const events = (payload.events || []).slice(-20).reverse();
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

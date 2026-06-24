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
      --header: #16212c;
      --header-ink: #ffffff;
      --active-bg: #0f6e8e;
      --active-ink: #ffffff;
    }
    body[data-theme="dark"] {
      color-scheme: dark;
      --bg: #10161c;
      --panel: #17212a;
      --panel-soft: #1d2933;
      --ink: #e7eef4;
      --muted: #9babba;
      --line: #33414d;
      --ok: #42b883;
      --bad: #ff6b5f;
      --warn: #d8a63c;
      --accent: #57b6d4;
      --accent-soft: #173a46;
      --cool: #73a7ff;
      --warm: #f0a650;
      --header: #0b1117;
      --header-ink: #f3f8fb;
      --active-bg: #57b6d4;
      --active-ink: #071217;
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
      background: var(--header);
      color: var(--header-ink);
      border-bottom: 3px solid var(--accent);
    }
    h1 { margin: 0; font-size: 21px; font-weight: 720; }
    h2 { margin: 0 0 10px; font-size: 15px; font-weight: 720; }
    h3 { margin: 0 0 8px; font-size: 14px; font-weight: 720; }
    .section-title {
      display: flex;
      gap: 7px;
      align-items: baseline;
      margin: 0 0 10px;
      font-size: 15px;
      font-weight: 720;
    }
    .section-title strong {
      font-size: 24px;
      line-height: 1;
    }
    main {
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 10px;
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
    .error-strip {
      display: none;
      min-height: 30px;
      overflow: hidden;
      border: 1px solid color-mix(in srgb, var(--warn) 36%, var(--line));
      border-radius: 5px;
      background: color-mix(in srgb, var(--warn) 11%, var(--panel));
      color: var(--ink);
    }
    .error-strip.active { display: block; }
    .error-track {
      display: inline-flex;
      gap: 28px;
      min-width: 100%;
      padding: 6px 10px;
      white-space: nowrap;
      animation: ticker 26s linear infinite;
    }
    @keyframes ticker {
      from { transform: translateX(100%); }
      to { transform: translateX(-100%); }
    }
    .header-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: flex-start;
      justify-content: flex-end;
    }
    .theme-stack {
      display: grid;
      gap: 5px;
      justify-items: end;
    }
    .weather-chip {
      display: none;
      min-height: 26px;
      padding: 4px 9px;
      border: 1px solid rgba(255,255,255,.24);
      border-radius: 5px;
      background: rgba(255,255,255,.08);
      color: #fff;
      font-weight: 680;
      text-align: center;
      white-space: nowrap;
    }
    .weather-chip.active { display: block; }
    .chip-label {
      margin-right: 6px;
      color: rgba(255,255,255,.72);
      font-size: 11px;
      font-weight: 760;
      text-transform: uppercase;
    }
    .nav button {
      min-height: 34px;
      border-color: rgba(255,255,255,.24);
      background: rgba(255,255,255,.08);
      color: #fff;
    }
    .nav button.active {
      background: var(--active-bg);
      color: var(--active-ink);
      border-color: var(--active-bg);
      box-shadow: inset 0 -3px 0 rgba(255,255,255,.35);
    }
    .theme-toggle {
      width: 38px;
      min-width: 38px;
      height: 38px;
      padding: 0;
      border-color: rgba(255,255,255,.24);
      background: rgba(255,255,255,.08);
      color: #fff;
      font-size: 18px;
      line-height: 1;
    }
    .view { display: none; }
    .view.active { display: grid; gap: 14px; }
    .subnav {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .subnav button {
      border-color: var(--line);
      background: var(--panel);
      color: var(--ink);
    }
    .subnav button.active {
      border-color: var(--accent);
      background: var(--active-bg);
      color: var(--active-ink);
      box-shadow: inset 0 -3px 0 rgba(255,255,255,.35);
    }
    .subview { display: none; }
    .subview.active { display: grid; gap: 14px; }
    .control-grid {
      display: grid;
      grid-template-columns: minmax(500px, 7fr) minmax(310px, 3fr);
      gap: 14px;
      align-items: start;
    }
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
      background: var(--panel);
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
      box-shadow: inset 4px 0 0 var(--accent);
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
      background: linear-gradient(180deg, var(--panel-soft) 0%, var(--panel) 82%);
      display: grid;
      gap: 14px;
      min-height: 260px;
    }
    .ac-panel.on {
      border-color: #87c7b0;
      background: linear-gradient(180deg, color-mix(in srgb, var(--ok) 11%, var(--panel)) 0%, var(--panel) 82%);
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
      background: var(--panel);
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
      grid-template-columns: minmax(0, 1fr);
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
      min-height: 108px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      background: var(--panel);
      display: grid;
      grid-template-columns: minmax(136px, .58fr) 44px minmax(240px, 1fr) minmax(112px, auto);
      gap: 10px;
      align-items: center;
    }
    .group-tile.on {
      border-color: #86c6b0;
      background: linear-gradient(180deg, color-mix(in srgb, var(--ok) 10%, var(--panel)) 0%, var(--panel) 76%);
    }
    .group-tile.off {
      background: color-mix(in srgb, var(--panel) 72%, var(--bg));
    }
    .group-tile.off .group-name,
    .group-tile.off .group-num {
      color: var(--muted);
    }
    .group-tile.off .group-body,
    .group-tile.off .tile-foot {
      opacity: .48;
    }
    .group-tile.spill {
      border-color: #dec879;
      background: linear-gradient(180deg, color-mix(in srgb, var(--warn) 14%, var(--panel)) 0%, var(--panel) 76%);
    }
    .group-head {
      display: grid;
      gap: 3px;
      align-items: center;
    }
    .group-name {
      font-size: 16px;
      font-weight: 780;
      overflow-wrap: anywhere;
    }
    .group-num {
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
      text-transform: uppercase;
    }
    .group-body {
      display: grid;
      grid-template-columns: minmax(82px, .75fr) minmax(82px, .75fr) minmax(128px, 1.35fr);
      gap: 8px;
      align-content: center;
      align-items: center;
    }
    .group-body .reading {
      padding: 8px;
      min-height: 66px;
      height: 100%;
    }
    .power-button {
      width: 42px;
      height: 42px;
      min-height: 42px;
      max-width: 42px;
      flex: 0 0 42px;
      padding: 0;
      border-radius: 999px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      line-height: 1;
      white-space: nowrap;
      font-size: 22px;
      overflow: hidden;
    }
    .power-button.on {
      background: var(--ok);
      border-color: var(--ok);
      color: #fff;
    }
    .power-button.off {
      background: var(--panel);
      border-color: var(--line);
      color: var(--muted);
    }
    .group-body .big {
      font-size: 24px;
    }
    .group-body .small-value {
      font-size: 18px;
    }
    .damper { min-width: 0; }
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
    .zone-slider {
      width: 100%;
      accent-color: var(--accent);
      margin: 8px 0 0;
    }
    .tile-foot {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      min-height: 22px;
      align-items: center;
    }
    .tile-actions {
      display: grid;
      grid-template-columns: repeat(2, minmax(48px, 1fr));
      gap: 8px;
      align-items: center;
      min-width: 112px;
    }
    .tile-actions button { padding-inline: 8px; }
    .tile-actions .wide-action { grid-column: 1 / -1; }
    .pill {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 22px;
      padding: 2px 8px;
      border-radius: 999px;
      border: 1px solid var(--line);
      color: var(--muted);
      background: var(--panel);
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
      background: var(--panel);
      color: var(--ink);
    }
    button.option {
      border-color: var(--line);
      background: var(--panel);
      color: var(--ink);
    }
    button.option.active {
      border-color: var(--accent);
      background: var(--active-bg);
      color: var(--active-ink);
      box-shadow: inset 0 -3px 0 rgba(255,255,255,.35);
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
    .field-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 10px;
      align-items: end;
    }
    .field {
      display: grid;
      gap: 5px;
    }
    .field label {
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
      text-transform: uppercase;
    }
    input,
    select {
      width: 100%;
      min-height: 36px;
      border: 1px solid var(--line);
      border-radius: 5px;
      background: var(--panel-soft);
      color: var(--text);
      padding: 7px 8px;
      font: inherit;
    }
    input[type="checkbox"] {
      width: 18px;
      min-height: 18px;
      padding: 0;
    }
    .check-row {
      display: flex;
      align-items: center;
      gap: 8px;
      min-height: 34px;
    }
    .service-actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 10px;
    }
    .service-card-body {
      display: grid;
      gap: 10px;
      margin-top: 10px;
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
      .control-grid,
      .control-head,
      .split,
      .service-grid {
        grid-template-columns: 1fr;
      }
      .group-tile {
        grid-template-columns: minmax(128px, .58fr) 44px minmax(210px, 1fr);
      }
      .group-body {
        grid-template-columns: minmax(82px, .75fr) minmax(82px, .75fr) minmax(128px, 1.35fr);
      }
      .tile-actions { grid-column: 3; }
    }
    @media (max-width: 620px) {
      header { grid-template-columns: 1fr; }
      main { padding: 10px; gap: 10px; }
      section { padding: 10px; }
      .group-tile {
        grid-template-columns: minmax(0, 1fr) 42px;
        align-items: start;
      }
      .ac-temp,
      .ac-controls,
      .group-body {
        grid-template-columns: 1fr 1fr;
      }
      .group-body,
      .tile-actions {
        grid-column: 1 / -1;
      }
      .tile-actions {
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }
      .damper { grid-column: 1 / -1; }
      .groups-board { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1 id="app-title">AirTouch 4</h1>
    <div class="header-actions">
      <div id="status" class="status"><span class="dot"></span><span>Connecting</span></div>
      <div class="theme-stack">
        <button type="button" id="theme-toggle" class="theme-toggle">Theme</button>
        <div id="weather-chip" class="weather-chip"></div>
        <div id="indoor-chip" class="weather-chip"></div>
      </div>
    </div>
    <nav class="nav" aria-label="Primary">
      <button type="button" class="active" data-view-button="control">Control</button>
      <button type="button" data-view-button="programs">Favourites & Programs</button>
      <button type="button" data-view-button="service">Service</button>
    </nav>
  </header>
  <main>
    <div id="view-control" class="view active">
      <div id="error-strip" class="error-strip" aria-live="polite"><div id="error-track" class="error-track"></div></div>
      <div class="control-grid">
        <section>
          <div class="section-title"><strong id="zone-count">0</strong><span>Zones</span></div>
          <div class="zone-toolbar">
            <div class="zone-pages" id="zone-pages"></div>
          </div>
          <div class="groups-board" id="groups"></div>
        </section>
        <section>
          <h2>Air Conditioner</h2>
          <div class="ac-selector" id="ac-selector"></div>
          <div class="ac-board" id="acs"></div>
        </section>
      </div>
    </div>

    <div id="view-programs" class="view">
      <div class="subnav" aria-label="Favourites and programs">
        <button type="button" class="active" data-subview-button="programs" data-subview="favourites">Favourites</button>
        <button type="button" data-subview-button="programs" data-subview="program-list">Programs</button>
        <button type="button" data-subview-button="programs" data-subview="ac-timer">AC Timer</button>
        <button type="button" data-subview-button="programs" data-subview="program-options">Options</button>
        <button type="button" data-subview-button="programs" data-subview="program-summary">Summary</button>
      </div>
      <div id="programs-favourites" class="subview active">
        <section>
          <h2>Favourites</h2>
          <div class="cards" id="favourites"></div>
        </section>
      </div>
      <div id="programs-program-list" class="subview">
        <section>
          <h2>Programs</h2>
          <div class="cards" id="programs"></div>
        </section>
      </div>
      <div id="programs-ac-timer" class="subview">
        <section>
          <h2>AC Timer</h2>
          <div class="cards" id="ac-timers"></div>
        </section>
      </div>
      <div id="programs-program-options" class="subview">
        <section>
          <h2>Options</h2>
          <div class="json" id="program-options">{}</div>
        </section>
      </div>
      <div id="programs-program-summary" class="subview">
        <section>
          <h2>Summary</h2>
          <div class="json" id="program-summary">{}</div>
        </section>
      </div>
    </div>

    <div id="view-service" class="view">
      <div class="subnav" aria-label="Service pages">
        <button type="button" class="active" data-subview-button="service" data-subview="sensors">Sensors</button>
        <button type="button" data-subview-button="service" data-subview="grouping">Grouping</button>
        <button type="button" data-subview-button="service" data-subview="spill">Spill</button>
        <button type="button" data-subview-button="service" data-subview="balance">Balance</button>
        <button type="button" data-subview-button="service" data-subview="ac-setup">AC Setup</button>
        <button type="button" data-subview-button="service" data-subview="parameters">Parameters</button>
        <button type="button" data-subview-button="service" data-subview="system">System Info</button>
        <button type="button" data-subview-button="service" data-subview="diagnostics">Diagnostics</button>
      </div>
      <div id="service-sensors" class="subview active">
        <section>
          <h2>Sensors</h2>
          <div class="service-actions">
            <button type="button" data-service-action="pair-sensor" data-pairing="true">Start Pair</button>
            <button type="button" class="secondary" data-service-action="pair-sensor" data-pairing="false">Stop Pair</button>
          </div>
          <table>
            <thead><tr><th>Sensor</th><th>Name</th><th>Temp</th><th>Signal</th><th>Status</th></tr></thead>
            <tbody id="sensors"></tbody>
          </table>
        </section>
      </div>
      <div id="service-grouping" class="subview">
        <section>
          <h2>Grouping</h2>
          <div class="cards" id="grouping"></div>
        </section>
      </div>
      <div id="service-spill" class="subview">
        <section>
          <h2>Spill</h2>
          <div class="cards" id="spill"></div>
        </section>
      </div>
      <div id="service-balance" class="subview">
        <section>
          <h2>Balance</h2>
          <table>
            <thead><tr><th>Zone</th><th>Set</th><th>Motor</th><th>State</th></tr></thead>
            <tbody id="balance"></tbody>
          </table>
        </section>
      </div>
      <div id="service-ac-setup" class="subview">
        <section>
          <h2>AC Setup</h2>
          <div class="cards" id="ac-setup"></div>
        </section>
      </div>
      <div id="service-parameters" class="subview">
        <section>
          <h2>Parameters</h2>
          <div class="field-grid">
            <div class="field">
              <label for="system-name-input">System name</label>
              <input id="system-name-input" maxlength="16" autocomplete="off">
            </div>
            <button type="button" data-service-action="preference">Save Name</button>
          </div>
          <div class="cards" id="parameters"></div>
        </section>
      </div>
      <div id="service-system" class="subview">
        <section>
          <h2>System Info</h2>
          <div class="field-grid">
            <div class="field">
              <label for="service-company-input">Service company</label>
              <input id="service-company-input" maxlength="10" autocomplete="off">
            </div>
            <div class="field">
              <label for="service-phone-input">Service phone</label>
              <input id="service-phone-input" maxlength="12" autocomplete="off">
            </div>
            <button type="button" data-service-action="service-contact">Save Service</button>
          </div>
          <div class="cards" id="system"></div>
        </section>
      </div>
      <div id="service-diagnostics" class="subview">
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
    const API_ROOT = window.location.pathname.replace(new RegExp("/+$"), "");
    const pendingGroups = new Set();
    const pendingAcs = new Set();
    const pendingFavourites = new Set();
    const THEME_KEY = "airtouch4.uiTheme";
    const themeLabels = {system: "System", light: "Light", dark: "Dark"};
    const themeIcons = {system: "&#128187;", light: "&#9728;", dark: "&#9790;"};
    let selectedAc = 0;
    let zonePage = 0;
    let configuredTheme = "system";
    let selectedTheme = localStorage.getItem(THEME_KEY) || "system";

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

    function infoCard(title, details, footer = "") {
      return `<article class="card"><div class="card-title">${escapeHtml(title)}</div><div class="muted">${escapeHtml(details)}</div>${footer}</article>`;
    }

    function pct(value) {
      const num = Number(value);
      if (!Number.isFinite(num)) return null;
      return Math.max(0, Math.min(100, Math.round(num)));
    }

    function temp(value) {
      return value === undefined || value === null ? "-" : `${value} C`;
    }

    function themeToApply() {
      const theme = selectedTheme === "system" ? configuredTheme : selectedTheme;
      if (theme === "dark" || theme === "light") return theme;
      return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }

    function applyTheme() {
      document.body.dataset.theme = themeToApply();
      const toggle = $("theme-toggle");
      toggle.innerHTML = themeIcons[selectedTheme] || "&#128187;";
      toggle.title = `${themeLabels[selectedTheme] || "System"} theme`;
      toggle.setAttribute("aria-label", toggle.title);
    }

    function modeName(value) {
      const modes = {0: "auto", 1: "heat", 2: "dry", 3: "fan", 4: "cool", 7: "-"};
      return modes[value] || text(value);
    }

    function fanName(value) {
      const fans = {0: "auto", 1: "low", 2: "med", 3: "high", 7: "-"};
      return fans[value] || text(value);
    }

    function detectAirTouchModel(state) {
      const system = state.system || {};
      const fields = [
        system.system_name,
        system.device_id,
        system.hardware_version_raw,
        system.firmware_version_raw,
        system.boot_version_raw,
        system.version_or_flags,
        system.gateway_info && system.gateway_info.text,
        system.debug_info && system.debug_info.text,
        system.expanded && system.expanded.software_version
      ].filter(Boolean).join(" ");
      if (/\\b(?:airtouch\\s*5|at5)\\b/i.test(fields)) return "AirTouch 5";
      if (/\\b(?:airtouch\\s*4|at4)\\b/i.test(fields)) return "AirTouch 4";
      return "AirTouch 4";
    }

    function collectAlerts(controller, state, integrations, transactions) {
      const alerts = [];
      if (controller.error) alerts.push(describeControllerError(controller.error));
      const controllerStatus = text(controller.status, "");
      if (controllerStatus && !["running", "starting", "stopped"].includes(controllerStatus) && !controller.error) {
        alerts.push(`Runtime status: ${controllerStatus}`);
      }
      const weatherError = integrations && integrations.weather && integrations.weather.error;
      if (weatherError) alerts.push(`Outside weather: ${describeControllerError(weatherError)}`);
      const indoorError = integrations && integrations.indoor && integrations.indoor.error;
      if (indoorError) alerts.push(`Indoor climate: ${describeControllerError(indoorError)}`);
      const mqtt = integrations && integrations.mqtt;
      if (mqtt && mqtt.enabled && mqtt.error) alerts.push(`MQTT: ${describeControllerError(mqtt.error)}`);
      if (mqtt && mqtt.enabled && Number(mqtt.failed_publish_count) > 0) {
        alerts.push(`MQTT publish failures: ${mqtt.failed_publish_count}`);
      }
      const errorResolver = integrations && integrations.error_resolver;
      if (errorResolver && errorResolver.enabled && errorResolver.last_error) {
        alerts.push(`Error lookup: ${describeControllerError(errorResolver.last_error)}`);
      }
      const failedTransactions = transactions && Array.isArray(transactions.failed) ? transactions.failed.length : 0;
      if (failedTransactions > 0) alerts.push(`Bus transactions failed: ${failedTransactions}`);
      Object.entries(state.acs || {}).forEach(([id, ac]) => {
        const status = ac.status || {};
        if (status.error_code && status.error_code !== 0) {
          const name = (ac.base || {}).name || `AC ${Number(id) + 1}`;
          alerts.push(`${name}: ${describeAcFault(status.error_code, status.error_display)}`);
        }
      });
      const dialog = state.system && state.system.dialog_message;
      if (dialog) {
        if (dialog.ascii) alerts.push(dialog.ascii);
        else if (dialog.message_id !== undefined) alerts.push(`Dialog ${dialog.message_id}`);
      }
      return [...new Set(alerts.filter(Boolean))];
    }

    function describeControllerError(error) {
      const message = text(error);
      if (/ConnectionRefusedError|ECONNREFUSED/i.test(message)) return `Runtime connection refused: ${message}`;
      if (/TimeoutError|timed out/i.test(message)) return `Runtime timeout: ${message}`;
      if (/SerialException|could not open port/i.test(message)) return `Serial transport error: ${message}`;
      if (/mqtt/i.test(message)) return `MQTT error: ${message}`;
      return message;
    }

    function describeAcFault(code, display) {
      if (display && display.label) {
        return display.description ? `${display.label}: ${display.description}` : display.label;
      }
      const number = Number(code);
      if (number === 65534) return "Code: FFFE: Error in the communication of the gateway with the main module.";
      if (number === 65535) return "Code: FFFF: Error in the communication of the gateway with the AC unit.";
      return `Code: ${Number.isFinite(number) ? number : text(code)}`;
    }

    function renderAlerts(alerts) {
      const strip = $("error-strip");
      const track = $("error-track");
      strip.classList.toggle("active", alerts.length > 0);
      track.innerHTML = alerts.map((alert) => `<span>${escapeHtml(alert)}</span>`).join("");
    }

    function renderWeather(integrations) {
      const chip = $("weather-chip");
      const weather = integrations && integrations.weather && integrations.weather.state;
      if (!weather) {
        chip.classList.remove("active");
        chip.textContent = "";
        return;
      }
      const unit = weather.temperature_unit || "C";
      const tempText = weather.temperature === undefined || weather.temperature === null ? "" : `${weather.temperature} ${unit}`;
      const humidityText = weather.humidity === undefined || weather.humidity === null ? "" : `${weather.humidity}%`;
      const icon = weatherIcon(weather.state);
      chip.innerHTML = [
        '<span class="chip-label">Outside</span>',
        `<span>${icon}</span>`,
        tempText ? `<span>${escapeHtml(tempText)}</span>` : "",
        humidityText ? `<span>${escapeHtml(humidityText)}</span>` : ""
      ].filter(Boolean).join(" ");
      chip.classList.add("active");
    }

    function renderIndoor(integrations) {
      const chip = $("indoor-chip");
      const indoor = integrations && integrations.indoor && integrations.indoor.state;
      if (!indoor || (indoor.temperature === null && indoor.temperature === undefined && indoor.humidity === null && indoor.humidity === undefined)) {
        chip.classList.remove("active");
        chip.textContent = "";
        return;
      }
      const tempUnit = indoor.temperature_unit || "C";
      const humidityUnit = indoor.humidity_unit || "%";
      const tempText = indoor.temperature === undefined || indoor.temperature === null ? "" : `${indoor.temperature} ${tempUnit}`;
      const humidityText = indoor.humidity === undefined || indoor.humidity === null ? "" : `${indoor.humidity} ${humidityUnit}`;
      chip.innerHTML = [
        '<span class="chip-label">Indoor</span>',
        tempText ? `<span>${escapeHtml(tempText)}</span>` : "",
        humidityText ? `<span>${escapeHtml(humidityText)}</span>` : ""
      ].filter(Boolean).join(" ");
      chip.classList.add("active");
    }

    function weatherIcon(condition) {
      const safeIcons = {
        "clear-night": "&#9790;",
        "cloudy": "&#9729;",
        "fog": "&#8779;",
        "hail": "&#9671;",
        "lightning": "&#9889;",
        "lightning-rainy": "&#9889;",
        "partlycloudy": "&#9680;",
        "pouring": "&#9730;",
        "rainy": "&#9730;",
        "snowy": "&#10052;",
        "snowy-rainy": "&#10052;",
        "sunny": "&#9728;",
        "windy": "&#8776;",
        "windy-variant": "&#8776;"
      };
      return safeIcons[String(condition || "").toLowerCase()] || "&#9675;";
      const icons = {
        "clear-night": "☾",
        "cloudy": "☁",
        "fog": "≋",
        "hail": "◇",
        "lightning": "⚡",
        "lightning-rainy": "⚡",
        "partlycloudy": "◐",
        "pouring": "☂",
        "rainy": "☂",
        "snowy": "❄",
        "snowy-rainy": "❄",
        "sunny": "☀",
        "windy": "≈",
        "windy-variant": "≈"
      };
      return icons[String(condition || "").toLowerCase()] || "○";
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

    function sensorName(value) {
      const sensor = Number(value);
      if (!Number.isFinite(sensor) || sensor === 255) return "None";
      if (sensor === 144) return "Touchpad 1";
      if (sensor === 145) return "Touchpad 2";
      return `Sensor ${sensor}`;
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
      const isOn = power === "on" || power === "turbo";
      const isSpill = group.spill_configured || status.spill_on;
      const sensorControl = status.sensor_control === true;
      const setpoint = Number.isInteger(status.setpoint) ? status.setpoint : null;
      const percentage = damper === null ? null : damper;
      const pending = pendingGroups.has(String(id));
      const roomTemp = status.has_sensor ? temp(status.temperature) : "-";
      const valueLabel = !isOn
        ? "OFF"
        : sensorControl
          ? temp(setpoint)
          : percentage === 0
            ? "Closed"
            : (percentage === null ? "-" : `${percentage}%`);
      const classes = ["group-tile"];
      if (isOn) classes.push("on");
      if (!isOn) classes.push("off");
      if (isSpill) classes.push("spill");
      const badges = [];
      badges.push(`<span class="${isOn ? "pill on" : "pill"}">${escapeHtml(power)}</span>`);
      if (isSpill) badges.push('<span class="pill warn">spill</span>');
      if (sensorControl) badges.push('<span class="pill cool">sensor</span>');
      if (status.low_battery) badges.push('<span class="pill warn">battery</span>');
      if (status.timer_on) badges.push('<span class="pill">program</span>');
      if (power === "turbo" || status.turbo_supported) badges.push('<span class="pill">turbo</span>');
      if (grouping.thermostat_name) badges.push(`<span class="pill">${escapeHtml(grouping.thermostat_name)}</span>`);
      const slider = sensorControl
        ? `<input class="zone-slider" type="range" min="16" max="30" step="1" value="${setpoint === null ? 23 : setpoint}" data-action="group-setpoint" data-group="${escapeHtml(id)}" ${pending || setpoint === null || !isOn ? "disabled" : ""}>`
        : `<input class="zone-slider" type="range" min="0" max="100" step="5" value="${percentage === null ? 0 : percentage}" data-action="group-percentage" data-group="${escapeHtml(id)}" ${pending || percentage === null || !isOn ? "disabled" : ""}>`;
      const valueButtons = sensorControl
        ? `
          <button type="button" class="secondary" data-action="group-setpoint" data-group="${escapeHtml(id)}" data-setpoint="${setpoint === null ? "" : setpoint - 1}" ${pending || setpoint === null || !isOn ? "disabled" : ""}>Set -</button>
          <button type="button" class="secondary" data-action="group-setpoint" data-group="${escapeHtml(id)}" data-setpoint="${setpoint === null ? "" : setpoint + 1}" ${pending || setpoint === null || !isOn ? "disabled" : ""}>Set +</button>`
        : `
          <button type="button" class="secondary" data-action="group-percentage" data-group="${escapeHtml(id)}" data-percentage="${percentage === null ? "" : Math.max(0, percentage - 10)}" ${pending || percentage === null || !isOn ? "disabled" : ""}>-10%</button>
          <button type="button" class="secondary" data-action="group-percentage" data-group="${escapeHtml(id)}" data-percentage="${percentage === null ? "" : Math.min(100, percentage + 10)}" ${pending || percentage === null || !isOn ? "disabled" : ""}>+10%</button>`;
      return `
        <article class="${classes.join(" ")}">
          <div class="group-head">
            <div>
              <div class="group-num">Zone ${number}</div>
              <div class="group-name">${escapeHtml(group.name || `Zone ${number}`)}</div>
            </div>
            <div class="tile-foot">${badges.join("")}</div>
          </div>
          <button
            type="button"
            class="power-button ${isOn ? "on" : "off"}"
            data-action="group-power"
            data-group="${escapeHtml(id)}"
            data-on="${isOn ? "false" : "true"}"
            data-sensor-control="${sensorControl ? "true" : "false"}"
            data-setpoint="${escapeHtml(status.setpoint ?? "")}"
            data-percentage="${escapeHtml(status.percentage ?? "")}"
            aria-label="${escapeHtml(isOn ? "Turn zone off" : "Turn zone on")}"
            title="${escapeHtml(isOn ? "Turn zone off" : "Turn zone on")}"
            ${pending ? "disabled" : ""}
          >${pending ? "..." : "⏻"}</button>
          <div class="group-body">
            <div class="reading">
              <div class="label">Room</div>
              <div class="big">${escapeHtml(roomTemp)}</div>
            </div>
            <div class="reading">
              <div class="label">${escapeHtml(sensorControl ? "Set" : "Vent")}</div>
              <div class="small-value">${escapeHtml(valueLabel)}</div>
              <div class="muted">${escapeHtml(status.has_sensor ? "mapped" : "no sensor")}</div>
            </div>
            <div class="damper">
              <div class="label">Damper</div>
              <div class="bar"><div class="bar-fill" style="width:${damper === null ? 0 : damper}%"></div></div>
              ${slider}
            </div>
          </div>
          <div class="tile-actions">
            ${valueButtons}
            ${status.turbo_supported ? `<button type="button" class="secondary wide-action" data-action="group-turbo" data-group="${escapeHtml(id)}" data-sensor-control="${sensorControl ? "true" : "false"}" data-setpoint="${escapeHtml(status.setpoint ?? "")}" data-percentage="${escapeHtml(status.percentage ?? "")}" ${pending || !isOn ? "disabled" : ""}>Turbo</button>` : ""}
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

    function renderProgramSupport(state) {
      const programs = state.programs || {};
      const acs = visibleAcs(state);
      $("ac-timers").innerHTML = acs.map(([id, ac]) => {
        const base = ac.base || {};
        const status = ac.status || {};
        return infoCard(
          base.name || `AC ${Number(id) + 1}`,
          `${status.power_on ? "On" : "Off"} / ${modeName(status.mode)} / ${fanName(status.fan)} / ${temp(status.setpoint)}`
        );
      }).join("") || '<div class="muted">No AC timer data</div>';
      $("program-options").textContent = JSON.stringify({
        known_programs: Object.keys(programs).length,
        active_favourite: state.active_favourite,
        timers_available: Object.keys(programs).some((id) => {
          const program = programs[id] || {};
          return !!((program.on_timer || {}).enabled || (program.off_timer || {}).enabled);
        })
      }, null, 2);
      $("program-summary").textContent = JSON.stringify(programs, null, 2);
    }

    function renderServicePages(state) {
      const groups = state.groups || state.active_groups || {};
      const acs = visibleAcs(state);
      const system = state.system || {};
      const balanceZones = ((state.system || {}).balance || {}).zones || [];
      $("grouping").innerHTML = Object.entries(groups)
        .sort(([a], [b]) => Number(a) - Number(b))
        .map(([id, group]) => {
          const grouping = group.grouping || {};
          const status = group.status || {};
          const groupName = group.name || `Zone ${Number(id) + 1}`;
          const zoneStart = grouping.zone_start ?? grouping.zone_1 ?? Number(id);
          const zoneCount = grouping.zone_count ?? 1;
          const minPercent = grouping.min_percent ?? status.min_percentage ?? 0;
          const thermostat = grouping.thermostat ?? status.sensor ?? 255;
          return `
            <article class="card" data-service-group="${escapeHtml(id)}">
              <div class="card-title">${escapeHtml(groupName)}</div>
              <div class="muted">Mapped dampers ${escapeHtml(zoneStart)}-${escapeHtml(Number(zoneStart) + Number(zoneCount) - 1)} / sensor ${escapeHtml(sensorName(thermostat))}</div>
              <div class="service-card-body">
                <div class="field-grid">
                  <div class="field"><label>Name</label><input data-field="group-name" maxlength="8" value="${escapeHtml(groupName)}"></div>
                  <div class="field"><label>Start</label><input data-field="zone-start" type="number" min="0" max="63" value="${escapeHtml(zoneStart)}"></div>
                  <div class="field"><label>Count</label><input data-field="zone-count" type="number" min="1" max="4" value="${escapeHtml(zoneCount)}"></div>
                  <div class="field"><label>Min %</label><input data-field="min-percent" type="number" min="0" max="100" value="${escapeHtml(minPercent)}"></div>
                  <div class="field"><label>Sensor</label><input data-field="thermostat" type="number" min="0" max="255" value="${escapeHtml(thermostat)}"></div>
                </div>
                <div class="service-actions">
                  <button type="button" data-service-action="group-name" data-group="${escapeHtml(id)}">Save Name</button>
                  <button type="button" class="secondary" data-service-action="grouping" data-group="${escapeHtml(id)}">Save Grouping</button>
                </div>
              </div>
            </article>`;
        }).join("") || '<div class="muted">No grouping data</div>';
      $("spill").innerHTML = Object.entries(groups)
        .sort(([a], [b]) => Number(a) - Number(b))
        .map(([id, group]) => {
          const status = group.status || {};
          const configured = group.spill_configured || status.spill_on;
          return `
            <article class="card">
              <div class="card-title">${escapeHtml(group.name || `Zone ${Number(id) + 1}`)}</div>
              <div class="muted">${escapeHtml(configured ? "Configured as spill/storage path" : "Normal controlled zone")}</div>
              <label class="check-row">
                <input type="checkbox" data-spill-group="${escapeHtml(id)}" ${configured ? "checked" : ""}>
                <span class="${configured ? "pill warn" : "pill"}">${configured ? "spill" : "normal"}</span>
              </label>
            </article>`;
        }).join("") || '<div class="muted">No spill data</div>';
      $("spill").innerHTML += `
        <article class="card">
          <div class="card-title">AC Spill Mode</div>
          <div class="field-grid">
            ${[0, 1, 2, 3].map((ac) => {
              const configured = (((system.spill || {}).ac_spill_types || [])[ac] || {}).value ?? 0;
              return `<div class="field"><label>AC ${ac + 1}</label><select data-spill-ac="${ac}">
                ${[[0, "None"], [1, "Spill"], [2, "Storage"], [3, "Reserve"]].map(([value, label]) => `<option value="${value}" ${configured === value ? "selected" : ""}>${label}</option>`).join("")}
              </select></div>`;
            }).join("")}
          </div>
          <div class="service-actions"><button type="button" data-service-action="spill">Save Spill</button></div>
        </article>`;
      $("balance").innerHTML = balanceZones.length
        ? balanceZones.map((zone) => {
          const group = groups[zone.zone] || {};
          return row([
            group.name || `Zone ${Number(zone.zone) + 1}`,
            zone.set_value ?? "-",
            zone.current_value ?? "-",
            (group.status || {}).power_name || "-"
          ]);
        }).join("")
        : row(["-", "No balance data", "-", "-"]);
      $("balance").innerHTML += `<tr><td colspan="4"><div class="service-actions"><button type="button" data-service-action="balance-start">Start Balance</button><button type="button" class="secondary" data-service-action="balance-stop">Stop Balance</button></div></td></tr>`;
      $("ac-setup").innerHTML = acs.map(([id, ac]) => {
        const base = ac.base || {};
        const settings = ac.settings || {};
        return infoCard(
          base.name || `AC ${Number(id) + 1}`,
          `Groups ${text(base.group_start)}-${Number.isInteger(base.group_start) && Number.isInteger(base.group_count) ? base.group_start + base.group_count - 1 : "-"} / brand ${text(base.brand)} / hide spill ${settings.hide_spill_group ? "yes" : "no"}`
        );
      }).join("") || '<div class="muted">No AC setup data</div>';
      if (document.activeElement !== $("system-name-input")) $("system-name-input").value = system.system_name || "";
      const service = state.service || {};
      if (document.activeElement !== $("service-company-input")) $("service-company-input").value = service.company || service.company_name || "";
      if (document.activeElement !== $("service-phone-input")) $("service-phone-input").value = service.phone || service.phone_number || "";
      $("parameters").innerHTML = [
        metric("System", system.system_name || "-"),
        metric("Groups", system.group_count ?? "-"),
        metric("ACs", system.ac_count ?? "-"),
        metric("Device ID", system.device_id || "-"),
        metric("Firmware", system.firmware_version_raw || "-"),
        metric("Sensors", (system.sensor_addresses || []).join(", ") || "-"),
      ].join("");
      $("system").innerHTML = [
        metric("Service", [service.company, service.phone].filter(Boolean).join(" / ") || "-"),
        metric("Password Pages", Object.keys(state.password || {}).length),
        metric("Last LED", (state.last_led || {}).led ?? "-"),
        metric("Supply Air", (system.supply_air || []).map((item) => item.status || item.temperature || "-").join(", ") || "-"),
        metric("Touchpads", (((system.sensor_list || {}).touchpad_addresses) || []).map((item) => `0x${Number(item).toString(16).toUpperCase()}`).join(", ") || "-"),
        metric("Runtime", (system.expanded || {}).software_version || "-"),
      ].join("");
    }

    function renderState(payload, eventsPayload = {}) {
      const controller = payload.controller || {};
      const runtime = (payload.runtime && payload.runtime.runtime) || {};
      const transactions = (payload.runtime && payload.runtime.transactions) || {};
      const state = (payload.runtime && payload.runtime.state) || {};
      const integrations = payload.integrations || {};
      const config = controller.config || {};
      configuredTheme = config.ui_theme || "system";
      applyTheme();
      $("app-title").textContent = detectAirTouchModel(state);
      renderAlerts(collectAlerts(controller, state, integrations, transactions));
      renderWeather(integrations);
      renderIndoor(integrations);
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
      $("zone-count").textContent = String(zoneEntries.length);
      $("zone-pages").innerHTML = pageCount > 1
        ? Array.from({length: pageCount}, (_value, index) => `<button type="button" class="option ${index === zonePage ? "active" : ""}" data-action="zone-page" data-page="${index}">${(index * 8) + 1}-${Math.min((index + 1) * 8, zoneEntries.length)}</button>`).join("")
        : "";
      $("groups").innerHTML = pageEntries
        .map(([id, group]) => groupTile(id, group))
        .join("") || '<div class="muted">No zone data</div>';

      renderFavourites(state.favourites || {}, groups);
      renderPrograms(state.programs || {}, groups);
      renderProgramSupport(state);
      renderServicePages(state);

      const sensors = state.sensors || {};
      $("sensors").innerHTML = Object.entries(sensors)
        .sort(([a], [b]) => Number(a) - Number(b))
        .map(([id, sensor]) => row([
          id,
          sensor.sensor_name,
          temp(sensor.temperature),
          sensor.signal !== undefined && sensor.signal !== null ? sensor.signal : "-",
          [
            sensor.kind,
            sensor.status || (sensor.present === false ? "missing" : sensor.listed ? "listed" : "-"),
            sensor.battery !== undefined && sensor.battery !== null ? `battery ${sensor.battery}` : "",
          ].filter(Boolean).join(" / ")
        ])).join("") || row(["-", "No sensor data", "-", "-", "-"]);
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

    document.querySelectorAll(".subnav").forEach((nav) => {
      nav.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-subview-button]");
        if (!button) return;
        const scope = button.dataset.subviewButton;
        const subview = button.dataset.subview;
        document.querySelectorAll(`[data-subview-button="${scope}"]`).forEach((item) => item.classList.toggle("active", item === button));
        document.querySelectorAll(`[id^="${scope}-"]`).forEach((item) => item.classList.toggle("active", item.id === `${scope}-${subview}`));
      });
    });

    $("theme-toggle").addEventListener("click", () => {
      const order = ["system", "light", "dark"];
      selectedTheme = order[(order.indexOf(selectedTheme) + 1) % order.length];
      localStorage.setItem(THEME_KEY, selectedTheme);
      applyTheme();
    });

    if (window.matchMedia) {
      window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", applyTheme);
    }

    $("view-service").addEventListener("click", async (event) => {
      const button = event.target.closest("button[data-service-action]");
      if (!button) return;
      const action = button.dataset.serviceAction;
      button.disabled = true;
      const previous = button.textContent;
      button.textContent = "Saving";
      try {
        if (action === "pair-sensor") {
          await sendCommand("pair_sensor", {pairing: button.dataset.pairing === "true"});
        } else if (action === "group-name") {
          const card = button.closest("[data-service-group]");
          await sendCommand("group_name", {
            group: Number(button.dataset.group),
            name: card.querySelector('[data-field="group-name"]').value,
          });
        } else if (action === "grouping") {
          const card = button.closest("[data-service-group]");
          await sendCommand("grouping", {
            group: Number(button.dataset.group),
            zone_start: Number(card.querySelector('[data-field="zone-start"]').value),
            zone_count: Number(card.querySelector('[data-field="zone-count"]').value),
            min_percent: Number(card.querySelector('[data-field="min-percent"]').value),
            thermostat: Number(card.querySelector('[data-field="thermostat"]').value),
          });
        } else if (action === "spill") {
          const spillGroups = Array.from(document.querySelectorAll("[data-spill-group]"))
            .filter((input) => input.checked)
            .map((input) => Number(input.dataset.spillGroup));
          const acSpillTypes = Array.from(document.querySelectorAll("[data-spill-ac]"))
            .sort((a, b) => Number(a.dataset.spillAc) - Number(b.dataset.spillAc))
            .map((select) => Number(select.value));
          await sendCommand("spill", {ac_spill_types: acSpillTypes, spill_groups: spillGroups});
        } else if (action === "balance-start") {
          await sendCommand("balance_start", {});
        } else if (action === "balance-stop") {
          await sendCommand("balance_stop", {});
        } else if (action === "preference") {
          await sendCommand("preference", {system_name: $("system-name-input").value});
        } else if (action === "service-contact") {
          await sendCommand("service", {
            company: $("service-company-input").value,
            phone: $("service-phone-input").value,
          });
        }
        setTimeout(refresh, 300);
      } catch (err) {
        setStatus({ok: false, error: err.message});
      } finally {
        setTimeout(() => {
          button.disabled = false;
          button.textContent = previous;
          refresh();
        }, 900);
      }
    });

    $("groups").addEventListener("click", async (event) => {
      const button = event.target.closest("button[data-action]");
      if (!button) return;
      const action = button.dataset.action;
      if (!["group-power", "group-setpoint", "group-percentage", "group-turbo"].includes(action)) return;
      const group = button.dataset.group;
      pendingGroups.add(group);
      button.disabled = true;
      button.textContent = button.classList.contains("power-button") ? "..." : "Sending";
      try {
        if (action === "group-power") {
          await sendCommand("group_power", {
            group: Number(group),
            on: button.dataset.on === "true",
            sensor_control: button.dataset.sensorControl === "true",
            setpoint: Number(button.dataset.setpoint),
            percentage: Number(button.dataset.percentage)
          });
        } else if (action === "group-setpoint") {
          await sendCommand("group_setpoint", {
            group: Number(group),
            setpoint: Number(button.dataset.setpoint)
          });
        } else if (action === "group-percentage") {
          await sendCommand("group_percentage", {
            group: Number(group),
            percentage: Number(button.dataset.percentage)
          });
        } else if (action === "group-turbo") {
          await sendCommand("group_turbo", {
            group: Number(group),
            sensor_control: button.dataset.sensorControl === "true",
            setpoint: Number(button.dataset.setpoint),
            percentage: Number(button.dataset.percentage)
          });
        }
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

    $("groups").addEventListener("change", async (event) => {
      const input = event.target.closest("input[data-action]");
      if (!input) return;
      const action = input.dataset.action;
      if (!["group-setpoint", "group-percentage"].includes(action)) return;
      const group = input.dataset.group;
      pendingGroups.add(group);
      input.disabled = true;
      try {
        if (action === "group-setpoint") {
          await sendCommand("group_setpoint", {
            group: Number(group),
            setpoint: Number(input.value)
          });
        } else {
          await sendCommand("group_percentage", {
            group: Number(group),
            percentage: Number(input.value)
          });
        }
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
        renderState(state, events);
        renderEvents(events);
      } catch (err) {
        setStatus({ok: false, error: err.message});
      }
    }

    applyTheme();
    refresh();
    setInterval(refresh, 1500);
  </script>
</body>
</html>
"""

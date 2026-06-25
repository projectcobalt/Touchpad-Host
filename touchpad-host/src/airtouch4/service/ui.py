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
      --panel-deep: #eef4f6;
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
      --shadow: 0 18px 36px rgba(22, 33, 44, .12);
      --shadow-soft: 0 8px 20px rgba(22, 33, 44, .08);
      --surface-ring: rgba(15, 110, 142, .18);
      --glass: rgba(255, 255, 255, .76);
      --lcd: #f7fbfb;
    }
    body[data-theme="dark"] {
      color-scheme: dark;
      --bg: #10161c;
      --panel: #17212a;
      --panel-soft: #1d2933;
      --panel-deep: #111a22;
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
      --shadow: 0 10px 28px rgba(0, 0, 0, .22);
      --shadow-soft: 0 4px 14px rgba(0, 0, 0, .18);
      --surface-ring: rgba(87, 182, 212, .24);
      --glass: rgba(23, 33, 42, .78);
      --lcd: #121b22;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background:
        radial-gradient(circle at 12% 0%, color-mix(in srgb, var(--accent) 16%, transparent) 0, transparent 340px),
        radial-gradient(circle at 92% 8%, color-mix(in srgb, var(--ok) 10%, transparent) 0, transparent 300px),
        linear-gradient(180deg, color-mix(in srgb, var(--accent) 8%, transparent) 0, transparent 260px),
        var(--bg);
      color: var(--ink);
      font: 14px/1.42 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    header {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 14px;
      align-items: center;
      padding: 16px 18px 12px;
      background: color-mix(in srgb, var(--header) 88%, black 8%);
      color: var(--header-ink);
      border-bottom: 1px solid color-mix(in srgb, var(--accent) 70%, transparent);
      box-shadow: var(--shadow);
      position: sticky;
      top: 0;
      z-index: 5;
    }
    h1 { margin: 0; font-size: 23px; font-weight: 760; }
    h2 { margin: 0 0 12px; font-size: 16px; font-weight: 760; }
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
      font-size: 23px;
      line-height: 1;
    }
    .section-title .count-detail {
      color: var(--muted);
      font-size: 23px;
      line-height: 1;
      font-weight: 760;
    }
    main {
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 10px;
      padding: 16px;
    }
    section {
      background: color-mix(in srgb, var(--glass) 84%, var(--panel));
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      min-width: 0;
      box-shadow: var(--shadow-soft);
      backdrop-filter: blur(10px);
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
      gap: 4px;
      width: fit-content;
      padding: 4px;
      border: 1px solid rgba(255,255,255,.14);
      border-radius: 8px;
      background: rgba(255,255,255,.06);
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
      transform: translateX(0);
    }
    .error-track.scrolling {
      animation: ticker var(--ticker-duration, 48s) linear infinite;
      will-change: transform;
    }
    @keyframes ticker {
      from { transform: translateX(var(--ticker-start, 100%)); }
      to { transform: translateX(var(--ticker-end, -100%)); }
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
      min-height: 36px;
      border-color: transparent;
      background: transparent;
      color: #fff;
      border-radius: 6px;
    }
    .nav button.active {
      background: var(--active-bg);
      color: var(--active-ink);
      border-color: var(--active-bg);
      box-shadow: 0 6px 14px rgba(0,0,0,.18);
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
      border-radius: 8px;
    }
    .view { display: none; }
    .view.active { display: grid; gap: 14px; }
    .subnav {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      padding: 4px;
      width: fit-content;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel-soft);
    }
    .subnav button {
      border-color: var(--line);
      background: transparent;
      color: var(--ink);
      border-radius: 6px;
    }
    .subnav button.active {
      border-color: var(--accent);
      background: var(--active-bg);
      color: var(--active-ink);
      box-shadow: var(--shadow-soft);
    }
    .subview { display: none; }
    .subview.active { display: grid; gap: 14px; }
    .control-grid {
      display: grid;
      grid-template-columns: minmax(500px, 7fr) minmax(310px, 3fr);
      gap: 16px;
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
      border-radius: 8px;
      padding: 10px;
      background: var(--panel-soft);
      color: var(--ink);
      text-align: left;
      display: grid;
      gap: 4px;
      align-content: start;
    }
    .ac-select-card.active {
      border-color: var(--accent);
      background: linear-gradient(135deg, var(--accent-soft), var(--panel));
      color: var(--ink);
      box-shadow: inset 4px 0 0 var(--accent), var(--shadow-soft);
    }
    .ac-board {
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 12px;
    }
    .ac-panel {
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 18px;
      background:
        linear-gradient(160deg, color-mix(in srgb, var(--accent) 8%, transparent) 0%, transparent 42%),
        var(--panel);
      display: grid;
      gap: 16px;
      min-height: 430px;
      box-shadow: var(--shadow-soft);
    }
    .ac-panel.on {
      border-color: color-mix(in srgb, var(--ok) 54%, var(--line));
      background:
        linear-gradient(160deg, color-mix(in srgb, var(--ok) 16%, transparent) 0%, transparent 48%),
        var(--panel);
    }
    .ac-panel.off {
      background:
        linear-gradient(160deg, color-mix(in srgb, var(--muted) 12%, transparent) 0%, transparent 48%),
        color-mix(in srgb, var(--panel) 62%, var(--bg));
    }
    .ac-panel.off .thermostat-face,
    .ac-panel.off .ac-mode-bank,
    .ac-panel.off .thermostat-stepper {
      opacity: .58;
    }
    .ac-top {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 46px;
      gap: 10px;
      align-items: start;
    }
    .ac-name { font-size: 26px; font-weight: 780; overflow-wrap: anywhere; }
    .ac-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      align-items: center;
      margin-top: 3px;
    }
    .ac-state-pill {
      min-height: 18px;
      padding: 1px 7px;
      font-size: 10px;
      line-height: 1;
    }
    .thermostat-face {
      width: min(260px, 100%);
      aspect-ratio: 1;
      margin: 2px auto 4px;
      border-radius: 999px;
      border: 1px solid color-mix(in srgb, var(--accent) 34%, var(--line));
      background:
        radial-gradient(circle at center, var(--lcd) 0 50%, transparent 51%),
        conic-gradient(from 225deg, var(--cool) 0 50%, var(--warm) 50% 100%);
      box-shadow: inset 0 0 0 14px color-mix(in srgb, var(--panel) 76%, transparent), var(--shadow-soft);
      display: grid;
      place-items: center;
      position: relative;
      overflow: hidden;
    }
    .thermostat-face::after {
      content: "";
      position: absolute;
      inset: 17px;
      border-radius: inherit;
      border: 1px solid color-mix(in srgb, var(--line) 72%, transparent);
      pointer-events: none;
    }
    .thermostat-marker {
      position: absolute;
      inset: 18px;
      border-radius: inherit;
      transform: rotate(var(--angle));
      pointer-events: none;
    }
    .thermostat-marker::after {
      content: "";
      position: absolute;
      left: 50%;
      top: -2px;
      width: 10px;
      height: 10px;
      margin-left: -5px;
      border-radius: 999px;
      background: var(--marker);
      box-shadow: 0 0 0 3px color-mix(in srgb, var(--panel) 82%, transparent);
    }
    .thermostat-current::after { width: 8px; height: 8px; margin-left: -4px; }
    .thermostat-readout {
      position: relative;
      z-index: 1;
      display: grid;
      gap: 4px;
      text-align: center;
      justify-items: center;
    }
    .thermostat-value {
      font-size: 56px;
      line-height: .95;
      font-weight: 800;
      letter-spacing: 0;
    }
    .thermostat-sub {
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }
    .thermostat-stepper {
      display: grid;
      grid-template-columns: 48px minmax(0, 1fr) 48px;
      gap: 10px;
      align-items: center;
    }
    .thermostat-stepper button {
      min-height: 48px;
      border-radius: 999px;
      padding: 0;
      font-size: 24px;
      line-height: 1;
    }
    .thermostat-range {
      text-align: center;
      color: var(--muted);
      font-weight: 700;
    }
    .ac-mode-bank {
      display: grid;
      gap: 12px;
    }
    .reading {
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 11px;
      background: var(--lcd);
      box-shadow: inset 0 1px 0 rgba(255,255,255,.04);
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
    .control-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    .groups-board {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(178px, 1fr));
      gap: 12px;
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
      min-height: 214px;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 12px;
      background:
        linear-gradient(180deg, color-mix(in srgb, var(--muted) 12%, transparent) 0 4px, transparent 4px),
        var(--panel);
      display: grid;
      grid-template-columns: 1fr auto;
      grid-template-areas:
        "head power"
        "temp temp"
        "actions actions"
        "damper damper";
      gap: 10px;
      align-items: start;
      box-shadow: var(--shadow-soft);
      position: relative;
      overflow: hidden;
    }
    .group-tile.on {
      border-color: color-mix(in srgb, var(--ok) 50%, var(--line));
      background:
        linear-gradient(180deg, var(--ok) 0 4px, transparent 4px),
        linear-gradient(135deg, color-mix(in srgb, var(--ok) 14%, transparent) 0%, transparent 46%),
        var(--panel);
      box-shadow: 0 0 0 1px var(--surface-ring), var(--shadow-soft);
    }
    .group-tile.off {
      background:
        linear-gradient(180deg, color-mix(in srgb, var(--muted) 28%, transparent) 0 4px, transparent 4px),
        color-mix(in srgb, var(--panel) 60%, var(--bg));
    }
    .group-tile.off .group-name,
    .group-tile.off .group-num {
      color: var(--muted);
    }
    .group-tile.off .group-body,
    .group-tile.off .tile-foot {
      opacity: .58;
    }
    .group-tile.spill {
      border-color: color-mix(in srgb, var(--warn) 56%, var(--line));
      background:
        linear-gradient(180deg, var(--warn) 0 4px, transparent 4px),
        linear-gradient(135deg, color-mix(in srgb, var(--warn) 16%, transparent) 0%, transparent 46%),
        var(--panel);
    }
    .group-head {
      grid-area: head;
      display: grid;
      gap: 7px;
      align-items: center;
      min-width: 0;
    }
    .group-name {
      font-size: 18px;
      font-weight: 780;
      overflow-wrap: anywhere;
    }
    .group-num {
      color: var(--muted);
      font-size: 11px;
      font-weight: 650;
      text-transform: uppercase;
    }
    .group-body {
      grid-area: temp;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      align-content: center;
      align-items: center;
    }
    .group-body .reading {
      padding: 9px;
      min-height: 74px;
      height: 100%;
    }
    .power-button {
      grid-area: power;
      width: 46px;
      height: 46px;
      min-height: 46px;
      max-width: 46px;
      flex: 0 0 46px;
      padding: 0;
      border-radius: 999px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      line-height: 1;
      white-space: nowrap;
      font-size: 22px;
      overflow: hidden;
      box-shadow: inset 0 -2px 0 rgba(0,0,0,.14), var(--shadow-soft);
    }
    .power-button.on {
      background: var(--ok);
      border-color: var(--ok);
      color: #fff;
    }
    .power-button.off {
      background: var(--panel-deep);
      border-color: var(--line);
      color: var(--muted);
    }
    .ac-top .power-button {
      grid-area: auto;
    }
    .group-body .big {
      font-size: 27px;
    }
    .group-body .small-value {
      font-size: 20px;
    }
    .damper { min-width: 0; }
    .group-tile .damper {
      grid-area: damper;
    }
    .damper .label {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .history-strip {
      margin-top: 7px;
      display: grid;
      gap: 4px;
    }
    .temp-line {
      width: 100%;
      height: 24px;
      display: block;
      overflow: visible;
    }
    .temp-line path {
      fill: none;
      stroke: var(--accent);
      stroke-width: 2.2;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .temp-line .area {
      fill: color-mix(in srgb, var(--accent) 13%, transparent);
      stroke: none;
    }
    .temp-line .axis {
      stroke: var(--line);
      stroke-width: 1;
    }
    .history-meta {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      color: var(--muted);
      font-size: 11px;
      line-height: 1.1;
    }
    .bar {
      height: 8px;
      border-radius: 999px;
      background: color-mix(in srgb, var(--line) 70%, var(--panel-deep));
      overflow: hidden;
      margin-top: 5px;
    }
    .bar-fill {
      height: 100%;
      width: 0%;
      background: linear-gradient(90deg, var(--accent), var(--ok));
    }
    .zone-slider {
      width: 100%;
      accent-color: var(--accent);
      margin: 10px 0 0;
    }
    .tile-foot {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      min-height: 22px;
      align-items: center;
    }
    .tile-actions {
      grid-area: actions;
      display: grid;
      grid-template-columns: repeat(2, minmax(48px, 1fr));
      gap: 8px;
      align-items: center;
      min-width: 0;
    }
    .tile-actions button { padding-inline: 8px; min-height: 38px; }
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
      background: color-mix(in srgb, var(--panel-soft) 70%, transparent);
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
      border-radius: 7px;
      padding: 5px 12px;
      background: linear-gradient(180deg, color-mix(in srgb, var(--accent) 92%, white 8%), var(--accent));
      color: #fff;
      font: inherit;
      font-weight: 720;
      cursor: pointer;
    }
    button:hover { filter: brightness(.95); }
    button:disabled { cursor: progress; opacity: .62; }
    button.secondary {
      border-color: var(--line);
      background: var(--panel-soft);
      color: var(--ink);
    }
    button.option {
      border-color: var(--line);
      background: var(--panel-soft);
      color: var(--ink);
    }
    button.option.active {
      border-color: var(--accent);
      background: linear-gradient(180deg, color-mix(in srgb, var(--active-bg) 92%, white 8%), var(--active-bg));
      color: var(--active-ink);
      box-shadow: var(--shadow-soft);
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
      border-radius: 8px;
      padding: 10px;
      background: color-mix(in srgb, var(--panel-soft) 84%, var(--panel));
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
      .groups-board {
        grid-template-columns: repeat(auto-fit, minmax(168px, 1fr));
      }
    }
    @media (max-width: 620px) {
      header { grid-template-columns: 1fr; }
      main { padding: 10px; gap: 10px; }
      section { padding: 10px; }
      .error-strip {
        max-height: 86px;
        overflow: auto;
      }
      .error-track {
        animation: none;
        transform: none;
        white-space: normal;
        flex-wrap: wrap;
        gap: 8px;
      }
      .group-tile {
        grid-template-columns: 1fr 42px;
        align-items: start;
      }
      .group-body {
        grid-template-columns: 1fr 1fr;
      }
      .tile-actions {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
      .groups-board { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .thermostat-face { width: min(230px, 100%); }
    }
    @media (max-width: 380px) {
      .groups-board {
        grid-template-columns: 1fr;
      }
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
          <div class="section-title"><strong id="zone-count">0</strong><span>Zones</span><span id="zone-active-count" class="count-detail">0 active</span></div>
          <div class="zone-toolbar">
            <div class="zone-pages" id="zone-pages"></div>
          </div>
          <div class="groups-board" id="groups"></div>
        </section>
        <section>
          <div class="section-title"><strong id="ac-count">0</strong><span>AC</span></div>
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
    let latestState = {};

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

    function temperatureHistoryLine(history = []) {
      const points = history
        .map((entry) => Number(entry.temperature))
        .filter((value) => Number.isFinite(value))
        .slice(-24);
      if (points.length < 2) {
        return `<div class="history-strip"><svg class="temp-line" viewBox="0 0 120 28" preserveAspectRatio="none" aria-hidden="true"><line class="axis" x1="0" y1="18" x2="120" y2="18"></line></svg><div class="history-meta"><span>History</span><span>${points.length ? temp(points[0]) : "-"}</span></div></div>`;
      }
      const min = Math.min(...points);
      const max = Math.max(...points);
      const spread = Math.max(1, max - min);
      const coords = points.map((value, index) => {
        const x = points.length === 1 ? 0 : (index / (points.length - 1)) * 120;
        const y = 24 - ((value - min) / spread) * 20;
        return [x, y];
      });
      const line = coords.map(([x, y], index) => `${index === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
      const area = `${line} L 120 27 L 0 27 Z`;
      return `<div class="history-strip">
        <svg class="temp-line" viewBox="0 0 120 28" preserveAspectRatio="none" aria-hidden="true">
          <path class="area" d="${area}"></path>
          <path d="${line}"></path>
        </svg>
        <div class="history-meta"><span>${escapeHtml(temp(points[0]))}</span><span>${escapeHtml(temp(points[points.length - 1]))}</span></div>
      </div>`;
    }

    function timeText(timer) {
      return timer && timer.enabled ? `${timer.hour}:${String(timer.minute).padStart(2, "0")}` : "-";
    }

    function timerFields(prefix, timer = {}) {
      return `
        <div class="field"><label>${prefix} enabled</label><select data-field="${prefix.toLowerCase()}-enabled">
          <option value="true" ${timer.enabled ? "selected" : ""}>On</option>
          <option value="false" ${!timer.enabled ? "selected" : ""}>Off</option>
        </select></div>
        <div class="field"><label>${prefix} hour</label><input data-field="${prefix.toLowerCase()}-hour" type="number" min="0" max="23" value="${escapeHtml(timer.hour ?? 0)}"></div>
        <div class="field"><label>${prefix} min</label><input data-field="${prefix.toLowerCase()}-minute" type="number" min="0" max="59" value="${escapeHtml(timer.minute ?? 0)}"></div>`;
    }

    function boolSelect(field, label, value) {
      return `<div class="field"><label>${escapeHtml(label)}</label><select data-field="${escapeHtml(field)}"><option value="true" ${value ? "selected" : ""}>On</option><option value="false" ${!value ? "selected" : ""}>Off</option></select></div>`;
    }

    function numberField(field, label, value, min, max) {
      return `<div class="field"><label>${escapeHtml(label)}</label><input data-field="${escapeHtml(field)}" type="number" min="${escapeHtml(min)}" max="${escapeHtml(max)}" value="${escapeHtml(value)}"></div>`;
    }

    function textField(field, label, value, maxlength = 16) {
      return `<div class="field"><label>${escapeHtml(label)}</label><input data-field="${escapeHtml(field)}" maxlength="${escapeHtml(maxlength)}" value="${escapeHtml(value || "")}" autocomplete="off"></div>`;
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
      requestAnimationFrame(updateAlertTicker);
    }

    function updateAlertTicker() {
      const strip = $("error-strip");
      const track = $("error-track");
      if (!strip || !track || !strip.classList.contains("active")) return;
      track.classList.remove("scrolling");
      track.style.removeProperty("--ticker-duration");
      track.style.removeProperty("--ticker-start");
      track.style.removeProperty("--ticker-end");
      if (window.matchMedia("(max-width: 620px)").matches) return;
      const stripWidth = strip.clientWidth;
      const trackWidth = track.scrollWidth;
      if (trackWidth <= stripWidth + 16) return;
      const distance = stripWidth + trackWidth;
      const seconds = Math.max(32, Math.min(110, Math.round(distance / 42)));
      track.style.setProperty("--ticker-duration", `${seconds}s`);
      track.style.setProperty("--ticker-start", `${stripWidth}px`);
      track.style.setProperty("--ticker-end", `-${trackWidth}px`);
      track.classList.add("scrolling");
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

    function averageZoneTemperature(state, {activeOnly = false} = {}) {
      const entries = Object.entries((state && (state.active_groups || state.groups)) || {});
      const values = entries
        .map(([_id, group]) => group.status || {})
        .filter((status) => {
          const active = status.power_name === "on" || status.power_name === "turbo";
          return status.has_sensor === true && Number.isFinite(Number(status.temperature)) && (!activeOnly || active);
        })
        .map((status) => Number(status.temperature));
      if (!values.length) return null;
      return values.reduce((sum, value) => sum + value, 0) / values.length;
    }

    function renderIndoor(integrations, state) {
      const chip = $("indoor-chip");
      const indoor = integrations && integrations.indoor && integrations.indoor.state;
      const average = averageZoneTemperature(state);
      const hasIndoorTemp = indoor && indoor.temperature !== undefined && indoor.temperature !== null;
      const hasIndoorHumidity = indoor && indoor.humidity !== undefined && indoor.humidity !== null;
      if (!hasIndoorTemp && average === null && !hasIndoorHumidity) {
        chip.classList.remove("active");
        chip.textContent = "";
        return;
      }
      const tempUnit = (indoor && indoor.temperature_unit) || "C";
      const humidityUnit = (indoor && indoor.humidity_unit) || "%";
      const tempText = hasIndoorTemp
        ? `${indoor.temperature} ${tempUnit}`
        : (average === null ? "" : `${average.toFixed(1)} C`);
      const humidityText = hasIndoorHumidity ? `${indoor.humidity} ${humidityUnit}` : "";
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

    function selectedAcRecordName(state, acId) {
      const ac = (state.acs || {})[acId] || {};
      return (ac.base || {}).name || `AC ${Number(acId) + 1}`;
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

    function finiteNumber(value) {
      const number = Number(value);
      return Number.isFinite(number) ? number : null;
    }

    function averageNumbers(values) {
      const numeric = values.map(finiteNumber).filter((value) => value !== null);
      if (!numeric.length) return null;
      return numeric.reduce((sum, value) => sum + value, 0) / numeric.length;
    }

    function groupIsActive(group) {
      const status = (group || {}).status || {};
      return status.power_name === "on" || status.power_name === "turbo" || status.power_code === 1;
    }

    function configuredModeOptions(settings) {
      const modeFlags = (settings || {}).modes || {};
      const options = [
        [0, "Auto", "auto"],
        [1, "Heat", "heat"],
        [2, "Dry", "dry"],
        [3, "Fan", "fan"],
        [4, "Cool", "cool"],
      ];
      const configured = options.filter(([_value, _label, key]) => modeFlags[key] === true);
      return configured.length ? configured : options;
    }

    function configuredFanOptions(settings) {
      const values = (settings || {}).fan_values || {};
      const options = [
        ["auto", "Auto", 0],
        ["quiet", "Quiet", null],
        ["low", "Low", 1],
        ["medium", "Med", 2],
        ["high", "High", 3],
        ["powerful", "Powerful", null],
        ["turbo", "Turbo", null],
      ];
      const seen = new Set();
      const configured = [];
      options.forEach(([key, label, fallback]) => {
        const value = finiteNumber(values[key]);
        const fanValue = value !== null && value > 0 ? value : fallback;
        if (fanValue === null || seen.has(fanValue)) return;
        seen.add(fanValue);
        configured.push([fanValue, label, key]);
      });
      return configured.length ? configured : [[0, "Auto"], [1, "Low"], [2, "Med"], [3, "High"]];
    }

    function deriveAcThermostat(ac, zoneEntries) {
      const status = ac.status || {};
      const settings = ac.settings || {};
      const min = finiteNumber(settings.min_setpoint) ?? 16;
      const max = finiteNumber(settings.max_setpoint) ?? 30;
      const activeGroups = (zoneEntries || []).map(([_id, group]) => group).filter(groupIsActive);
      const activeSensorGroups = activeGroups
        .map((group) => group.status || {})
        .filter((zoneStatus) => zoneStatus.has_sensor === true);
      const activeSetpoint = averageNumbers(
        activeSensorGroups
          .filter((zoneStatus) => zoneStatus.sensor_control === true)
          .map((zoneStatus) => zoneStatus.setpoint)
      );
      const activeTemperature = averageNumbers(activeSensorGroups.map((zoneStatus) => zoneStatus.temperature));
      const mappedSensorTemperature = averageNumbers(
        (zoneEntries || [])
          .map(([_id, group]) => (group.status || {}))
          .filter((zoneStatus) => zoneStatus.has_sensor === true && zoneStatus.sensor_control === true)
          .map((zoneStatus) => zoneStatus.temperature)
      );
      const anyTemperature = averageNumbers(
        (zoneEntries || [])
          .map(([_id, group]) => (group.status || {}))
          .filter((zoneStatus) => zoneStatus.has_sensor === true)
          .map((zoneStatus) => zoneStatus.temperature)
      );
      const statusSetpoint = finiteNumber(status.setpoint);
      const statusTemperature = finiteNumber(status.sensor_temp ?? status.temperature ?? status.current_temp);
      return {
        min,
        max,
        setpoint: activeSetpoint ?? statusSetpoint,
        current: activeTemperature ?? mappedSensorTemperature ?? anyTemperature ?? statusTemperature,
        source: activeSetpoint !== null ? "active_zones" : mappedSensorTemperature !== null ? "mapped_zones" : anyTemperature !== null ? "zone_average" : "ac_status",
      };
    }

    function thermostatAngle(value, min, max) {
      const numeric = finiteNumber(value);
      if (numeric === null || max <= min) return "-135deg";
      const bounded = Math.min(max, Math.max(min, numeric));
      return `${-135 + ((bounded - min) / (max - min)) * 270}deg`;
    }

    function acCard(id, ac, zoneEntries) {
      const status = ac.status || {};
      const base = ac.base || {};
      const settings = ac.settings || {};
      const power = status.power_on === true ? "on" : status.power_on === false ? "off" : "-";
      const isOn = power === "on";
      const pending = pendingAcs.has(String(id));
      const mode = Number.isInteger(status.mode) ? status.mode : null;
      const fan = Number.isInteger(status.fan) ? status.fan : null;
      const thermostat = deriveAcThermostat(ac, zoneEntries);
      const setpoint = thermostat.setpoint === null ? null : Math.round(thermostat.setpoint);
      const current = thermostat.current === null ? null : thermostat.current;
      const rangeText = `${thermostat.min}-${thermostat.max} C range`;
      const currentText = current === null ? "-" : `${current.toFixed(1)} C`;
      const setpointText = setpoint === null ? "-" : String(setpoint);
      const setMarker = setpoint === null ? "" : `<span class="thermostat-marker thermostat-set" style="--angle:${thermostatAngle(setpoint, thermostat.min, thermostat.max)};--marker:var(--warm)" title="Set ${escapeHtml(setpointText)} C"></span>`;
      const currentMarker = current === null ? "" : `<span class="thermostat-marker thermostat-current" style="--angle:${thermostatAngle(current, thermostat.min, thermostat.max)};--marker:var(--cool)" title="Current ${escapeHtml(currentText)}"></span>`;
      const modes = configuredModeOptions(settings);
      const fans = configuredFanOptions(settings);
      const modeLabel = (modes.find(([value]) => value === mode) || [mode, modeName(mode)])[1];
      const fanLabel = (fans.find(([value]) => value === fan) || [fan, fanName(fan)])[1];
      return `
        <article class="ac-panel ${isOn ? "on" : "off"}">
          <div class="ac-top">
            <div>
              <div class="ac-name">${escapeHtml(base.name || `AC ${Number(id) + 1}`)}</div>
              <div class="muted ac-meta">
                <span>${escapeHtml(modeLabel)} mode</span>
                <span>${escapeHtml(fanLabel)} fan</span>
                <span class="${isOn ? "pill on ac-state-pill" : "pill ac-state-pill"}">${escapeHtml(power)}</span>
              </div>
            </div>
            <button
              type="button"
              class="power-button ${isOn ? "on" : "off"}"
              data-action="ac-status"
              data-ac="${escapeHtml(id)}"
              data-power-on="${isOn ? "false" : "true"}"
              aria-label="${escapeHtml(isOn ? "Turn AC off" : "Turn AC on")}"
              title="${escapeHtml(isOn ? "Turn AC off" : "Turn AC on")}"
              ${pending ? "disabled" : ""}
            >${pending ? "..." : "&#9211;"}</button>
          </div>
          <div class="thermostat-face">
            ${currentMarker}
            ${setMarker}
            <div class="thermostat-readout">
              <div class="thermostat-sub">Setpoint</div>
              <div class="thermostat-value">${escapeHtml(setpointText)}</div>
              <div class="thermostat-sub">Now ${escapeHtml(currentText)}</div>
            </div>
          </div>
          <div class="thermostat-stepper">
            <button type="button" class="secondary" data-action="ac-status" data-ac="${escapeHtml(id)}" data-setpoint="${setpoint === null ? "" : setpoint - 1}" ${pending || setpoint === null ? "disabled" : ""}>-</button>
            <div class="thermostat-range">${escapeHtml(rangeText)}</div>
            <button type="button" class="secondary" data-action="ac-status" data-ac="${escapeHtml(id)}" data-setpoint="${setpoint === null ? "" : setpoint + 1}" ${pending || setpoint === null ? "disabled" : ""}>+</button>
          </div>
          <div class="ac-mode-bank">
            <div>
              <div class="label">Mode</div>
              <div class="control-row">${modes.map(([value, label]) => `<button type="button" class="option ${mode === value ? "active" : ""}" data-action="ac-status" data-ac="${escapeHtml(id)}" data-mode="${value}" ${pending ? "disabled" : ""}>${label}</button>`).join("")}</div>
            </div>
            <div>
              <div class="label">Fan</div>
              <div class="control-row">${fans.map(([value, label]) => `<button type="button" class="option ${fan === value ? "active" : ""}" data-action="ac-status" data-ac="${escapeHtml(id)}" data-fan="${value}" ${pending ? "disabled" : ""}>${label}</button>`).join("")}</div>
            </div>
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
      const history = temperatureHistoryLine(group.temperature_history || []);
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
        ? ""
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
          >${pending ? "..." : "&#9211;"}</button>
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
          </div>
          <div class="damper">
            <div class="label"><span>Damper</span><span>${escapeHtml(damper === null ? "-" : `${damper}%`)}</span></div>
            <div class="bar"><div class="bar-fill" style="width:${damper === null ? 0 : damper}%"></div></div>
            ${slider}
            ${history}
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
        const groupChecks = Array.from({length: 16}, (_value, index) => {
          const selected = index < 8
            ? !!((favourite.groups_1_8_bitmap || 0) & (1 << index))
            : !!((favourite.groups_9_16_bitmap || 0) & (1 << (index - 8)));
          const name = (groups[index] || {}).name || `Zone ${index + 1}`;
          return `<label class="check-row"><input type="checkbox" data-favourite-group="${index}" ${selected ? "checked" : ""}><span>${escapeHtml(name)}</span></label>`;
        }).join("");
        return `
          <article class="card" data-favourite-card="${escapeHtml(id)}">
            <div class="card-title">${escapeHtml(favourite.name || `Favourite ${Number(id) + 1}`)}</div>
            <div class="muted">${escapeHtml(groupNames.length ? groupNames.join(", ") : "No zones selected")}</div>
            <div class="service-card-body">
              <div class="field-grid">
                ${textField("favourite-name", "Name", favourite.name || "", 8)}
              </div>
              <div class="field-grid">${groupChecks}</div>
              <div class="service-actions">
                <button type="button" data-action="active-favourite" data-favourite="${escapeHtml(id)}" ${pending ? "disabled" : ""}>${escapeHtml(pending ? "Sending" : "Apply")}</button>
                <button type="button" class="secondary" data-action="favourite-save" data-favourite="${escapeHtml(id)}">Save Favourite</button>
              </div>
            </div>
          </article>`;
      }).join("") || '<div class="muted">No favourite data</div>';
    }

    function acBaseRecordsFromState() {
      return visibleAcs(latestState).map(([id, ac]) => ({
        ac: Number(id),
        group_start: Number((ac.base || {}).group_start ?? 0),
        group_count: Number((ac.base || {}).group_count ?? 0),
        brand: Number((ac.base || {}).brand ?? 0),
        name: (ac.base || {}).name || `AC ${Number(id) + 1}`
      }));
    }

    function acSettingRecordsFromState() {
      return visibleAcs(latestState).map(([id, ac]) => {
        const settings = ac.settings || {};
        return {
          ac: Number(id),
          hide_spill_group: !!settings.hide_spill_group,
          ctrl_thermostat: Number(settings.ctrl_thermostat ?? 0),
          cool_adjust: Number(settings.cool_adjust ?? 0),
          heat_adjust: Number(settings.heat_adjust ?? 0),
          modes: settings.modes || {},
          fan_values: settings.fan_values || {},
          auto_off: !!settings.auto_off,
          on_time_limit: Number(settings.on_time_limit ?? 0),
          max_setpoint: Number(settings.max_setpoint ?? 30),
          min_setpoint: Number(settings.min_setpoint ?? 16),
          selector_visibility: settings.selector_visibility || {}
        };
      });
    }

    function programRecordsFromState() {
      return Object.entries(latestState.programs || {})
        .sort(([a], [b]) => Number(a) - Number(b))
        .map(([id, program]) => ({
          ...program,
          program: Number(program.program ?? id),
          enabled: !!program.enabled,
          days_bitmap: Number(program.days_bitmap ?? 0),
          groups_1_8_bitmap: Number(program.groups_1_8_bitmap ?? 0),
          groups_9_16_bitmap: Number(program.groups_9_16_bitmap ?? 0),
          active_ac_bitmap: Number(program.active_ac_bitmap ?? 0),
          on_setpoint: Number(program.on_setpoint ?? 26),
          on_timer: program.on_timer || {enabled: false},
          off_timer: program.off_timer || {enabled: false}
        }));
    }

    function acTimerRecordsFromState() {
      return visibleAcs(latestState).map(([id, ac]) => {
        const timer = ac.timer || {};
        return {
          ac: Number(id),
          on_timer: timer.on_timer || timer.timer || {enabled: false},
          off_timer: timer.off_timer || {enabled: false}
        };
      });
    }

    function timerFromCard(card, prefix) {
      return {
        enabled: card.querySelector(`[data-field="${prefix}-enabled"]`).value === "true",
        hour: Number(card.querySelector(`[data-field="${prefix}-hour"]`).value),
        minute: Number(card.querySelector(`[data-field="${prefix}-minute"]`).value)
      };
    }

    function fieldBool(card, field) {
      return card.querySelector(`[data-field="${field}"]`).value === "true";
    }

    function fieldNumber(card, field) {
      return Number(card.querySelector(`[data-field="${field}"]`).value);
    }

    function balanceValuesFromPage() {
      const values = Array(16).fill(0);
      document.querySelectorAll("[data-balance-value]").forEach((input) => {
        const zone = Number(input.dataset.balanceValue);
        if (zone >= 0 && zone < values.length) values[zone] = Number(input.value);
      });
      return values;
    }

    function turboGroupsFromState() {
      const values = [];
      (((latestState.system || {}).turbo_group || {}).records || []).forEach((record) => {
        values[Number(record.ac)] = record.group === null || record.group === undefined ? 255 : Number(record.group);
      });
      return values;
    }

    function favouriteGroupsFromCard(card) {
      return Array.from(card.querySelectorAll("[data-favourite-group]"))
        .filter((input) => input.checked)
        .map((input) => Number(input.dataset.favouriteGroup));
    }

    function renderPrograms(programs, groups) {
      const entries = Object.entries(programs || {}).sort(([a], [b]) => Number(a) - Number(b));
      $("programs").innerHTML = entries.map(([_id, program]) => {
        const groupNames = groupNamesFromBitmap(groups, program.groups_1_8_bitmap || 0, program.groups_9_16_bitmap || 0);
        const onTimer = program.on_timer || {};
        const offTimer = program.off_timer || {};
        return `
          <article class="card" data-program="${escapeHtml(program.program ?? _id)}">
            <div class="card-title">${escapeHtml(program.name || `Program ${(program.program ?? 0) + 1}`)}</div>
            <div class="muted">${escapeHtml(groupNames.length ? groupNames.join(", ") : "No zones selected")}</div>
            <div><span class="${program.enabled ? "pill on" : "pill"}">${escapeHtml(program.enabled ? "enabled" : "off")}</span></div>
            <div class="muted">On ${escapeHtml(timeText(onTimer))} / Off ${escapeHtml(timeText(offTimer))}</div>
            <div class="service-card-body">
              <div class="field-grid">
                <div class="field"><label>Name</label><input data-field="program-name" maxlength="8" value="${escapeHtml(program.name || "")}"></div>
                <div class="field"><label>Enabled</label><select data-field="program-enabled"><option value="true" ${program.enabled ? "selected" : ""}>On</option><option value="false" ${!program.enabled ? "selected" : ""}>Off</option></select></div>
                <div class="field"><label>Days</label><input data-field="program-days" type="number" min="0" max="127" value="${escapeHtml(program.days_bitmap ?? 0)}"></div>
                <div class="field"><label>Zones 1-8</label><input data-field="program-groups-1" type="number" min="0" max="255" value="${escapeHtml(program.groups_1_8_bitmap ?? 0)}"></div>
                <div class="field"><label>Zones 9-16</label><input data-field="program-groups-2" type="number" min="0" max="255" value="${escapeHtml(program.groups_9_16_bitmap ?? 0)}"></div>
                <div class="field"><label>AC mask</label><input data-field="program-acs" type="number" min="0" max="15" value="${escapeHtml(program.active_ac_bitmap ?? 0)}"></div>
                ${timerFields("On", onTimer)}
                <div class="field"><label>Setpoint</label><input data-field="program-on-setpoint" type="number" min="0" max="63" value="${escapeHtml(program.on_setpoint ?? 26)}"></div>
                ${timerFields("Off", offTimer)}
              </div>
              <div class="service-actions"><button type="button" data-program-action="program-save" data-program="${escapeHtml(program.program ?? _id)}">Save Program</button></div>
            </div>
          </article>`;
      }).join("") || '<div class="muted">No program data</div>';
    }

    function renderProgramSupport(state) {
      const programs = state.programs || {};
      const acs = visibleAcs(state);
      $("ac-timers").innerHTML = acs.map(([id, ac]) => {
        const base = ac.base || {};
        const status = ac.status || {};
        const timer = ac.timer || {};
        const onTimer = timer.on_timer || timer.timer || {};
        const offTimer = timer.off_timer || {};
        return `
          <article class="card" data-ac-timer="${escapeHtml(id)}">
            <div class="card-title">${escapeHtml(base.name || `AC ${Number(id) + 1}`)}</div>
            <div class="muted">${escapeHtml(status.power_on ? "On" : "Off")} / ${escapeHtml(modeName(status.mode))} / ${escapeHtml(fanName(status.fan))} / ${escapeHtml(temp(status.setpoint))}</div>
            <div class="muted">On ${escapeHtml(timeText(onTimer))} / Off ${escapeHtml(timeText(offTimer))}</div>
            <div class="service-card-body">
              <div class="field-grid">${timerFields("On", onTimer)}${timerFields("Off", offTimer)}</div>
              <div class="service-actions"><button type="button" data-program-action="ac-timer-save" data-ac="${escapeHtml(id)}">Save Timer</button></div>
            </div>
          </article>`;
      }).join("") || '<div class="muted">No AC timer data</div>';
      $("program-options").textContent = JSON.stringify({
        known_programs: Object.keys(programs).length,
        active_favourite: (state.system || {}).active_favourite,
        linked_ac: (state.system || {}).programs_linked_ac,
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
          return `<tr data-balance-zone="${escapeHtml(zone.zone)}">
            <td>${escapeHtml(group.name || `Zone ${Number(zone.zone) + 1}`)}</td>
            <td><input data-balance-value="${escapeHtml(zone.zone)}" type="number" min="0" max="255" value="${escapeHtml(zone.set_value ?? 0)}"></td>
            <td>${escapeHtml(zone.current_value ?? "-")}</td>
            <td>
              <div class="service-actions">
                <button type="button" data-service-action="balance-zone" data-zone="${escapeHtml(zone.zone)}">Set</button>
                <span class="muted">${escapeHtml((group.status || {}).power_name || "-")}</span>
              </div>
            </td>
          </tr>`;
        }).join("")
        : row(["-", "No balance data", "-", "-"]);
      $("balance").innerHTML += `<tr><td colspan="4"><div class="service-actions"><button type="button" data-service-action="balance-start">Start Balance</button><button type="button" class="secondary" data-service-action="balance-stop">Stop Balance</button></div></td></tr>`;
      $("ac-setup").innerHTML = acs.map(([id, ac]) => {
        const base = ac.base || {};
        const settings = ac.settings || {};
        const modes = settings.modes || {};
        const fans = settings.fan_values || {};
        const selectors = settings.selector_visibility || {};
        const turboRecord = (((system.turbo_group || {}).records || []).find((item) => Number(item.ac) === Number(id))) || {};
        return `
          <article class="card" data-service-ac="${escapeHtml(id)}">
            <div class="card-title">${escapeHtml(base.name || `AC ${Number(id) + 1}`)}</div>
            <div class="muted">Groups ${escapeHtml(text(base.group_start))}-${escapeHtml(Number.isInteger(base.group_start) && Number.isInteger(base.group_count) ? base.group_start + base.group_count - 1 : "-")} / brand ${escapeHtml(text(base.brand))} / hide spill ${escapeHtml(settings.hide_spill_group ? "yes" : "no")}</div>
            <div class="service-card-body">
              <div class="field-grid">
                <div class="field"><label>Name</label><input data-field="ac-name" maxlength="8" value="${escapeHtml(base.name || "")}"></div>
                <div class="field"><label>Group start</label><input data-field="ac-group-start" type="number" min="0" max="63" value="${escapeHtml(base.group_start ?? 0)}"></div>
                <div class="field"><label>Group count</label><input data-field="ac-group-count" type="number" min="0" max="63" value="${escapeHtml(base.group_count ?? 0)}"></div>
                <div class="field"><label>Brand</label><input data-field="ac-brand" type="number" min="0" max="65535" value="${escapeHtml(base.brand ?? 0)}"></div>
                <div class="field"><label>Hide spill</label><select data-field="hide-spill"><option value="true" ${settings.hide_spill_group ? "selected" : ""}>Yes</option><option value="false" ${!settings.hide_spill_group ? "selected" : ""}>No</option></select></div>
                <div class="field"><label>Thermostat</label><input data-field="ctrl-thermostat" type="number" min="0" max="255" value="${escapeHtml(settings.ctrl_thermostat ?? 0)}"></div>
                <div class="field"><label>Cool adjust</label><input data-field="cool-adjust" type="number" min="-8" max="7" value="${escapeHtml(settings.cool_adjust ?? 0)}"></div>
                <div class="field"><label>Heat adjust</label><input data-field="heat-adjust" type="number" min="-8" max="7" value="${escapeHtml(settings.heat_adjust ?? 0)}"></div>
                <div class="field"><label>Min set</label><input data-field="min-setpoint" type="number" min="0" max="255" value="${escapeHtml(settings.min_setpoint ?? 16)}"></div>
                <div class="field"><label>Max set</label><input data-field="max-setpoint" type="number" min="0" max="255" value="${escapeHtml(settings.max_setpoint ?? 30)}"></div>
                <div class="field"><label>Auto off</label><select data-field="auto-off"><option value="true" ${settings.auto_off ? "selected" : ""}>On</option><option value="false" ${!settings.auto_off ? "selected" : ""}>Off</option></select></div>
                <div class="field"><label>Time limit</label><input data-field="on-time-limit" type="number" min="0" max="15" value="${escapeHtml(settings.on_time_limit ?? 0)}"></div>
                ${["auto", "cool", "heat", "dry", "fan"].map((mode) => boolSelect(`mode-${mode}`, `Mode ${mode}`, !!modes[mode])).join("")}
                ${["auto", "quiet", "low", "medium", "high", "powerful", "turbo"].map((fan) => numberField(`fan-${fan}`, `Fan ${fan}`, fans[fan] ?? 0, 0, 15)).join("")}
                ${["auto", "touchpad_1", "touchpad_2", "average", "economy"].map((selector) => boolSelect(`selector-${selector}`, `Show ${selector}`, !!selectors[selector])).join("")}
                ${numberField("selector-groups-1", "Selector zones 1-8", selectors.groups_1_8_bitmap ?? 0, 0, 255)}
                ${numberField("selector-groups-2", "Selector zones 9-16", selectors.groups_9_16_bitmap ?? 0, 0, 255)}
                ${numberField("turbo-group", "Turbo zone", turboRecord.group ?? 255, 0, 255)}
              </div>
              <div class="service-actions">
                <button type="button" data-service-action="ac-base-info" data-ac="${escapeHtml(id)}">Save AC Base</button>
                <button type="button" class="secondary" data-service-action="ac-setting-new" data-ac="${escapeHtml(id)}">Save AC Settings</button>
                <button type="button" class="secondary" data-service-action="turbo-group" data-ac="${escapeHtml(id)}">Save Turbo Zone</button>
              </div>
            </div>
          </article>`;
      }).join("") || '<div class="muted">No AC setup data</div>';
      if (document.activeElement !== $("system-name-input")) $("system-name-input").value = system.system_name || "";
      const service = state.service || {};
      if (document.activeElement !== $("service-company-input")) $("service-company-input").value = service.company || service.company_name || "";
      if (document.activeElement !== $("service-phone-input")) $("service-phone-input").value = service.phone || service.phone_number || "";
      $("parameters").innerHTML = `
        <article class="card">
          <div class="card-title">Preference</div>
          <div class="field-grid">
            ${boolSelect("show-ac-errors", "Show AC errors", !!system.show_ac_errors)}
            ${boolSelect("pref-show-outside-temp", "Show outside temp", !!system.show_outside_temp)}
            ${boolSelect("pref-show-control-sensor", "Show control sensor", !!system.show_control_sensor)}
            ${boolSelect("use-fahrenheit", "Fahrenheit", !!system.use_fahrenheit)}
            ${numberField("location", "Location", system.location ?? system.address_or_location ?? 0, 0, 127)}
            ${boolSelect("screensaver-enabled", "Screensaver", !!system.screensaver_enabled)}
            ${numberField("screensaver-timeout", "Screen timeout", system.screensaver_timeout ?? 0, 0, 127)}
          </div>
          <div class="service-actions"><button type="button" data-service-action="preference">Save Preference</button></div>
        </article>
        <article class="card">
          <div class="card-title">Parameters</div>
          <div class="field-grid">
            ${numberField("group-count", "Groups", system.group_count ?? (Object.keys(groups).length || 1), 1, 16)}
            ${numberField("damper-rpm", "Damper RPM", system.damper_rpm ?? 100, 0, 255)}
            ${numberField("touchpad-1-location", "Touchpad 1 location", system.touchpad_1_location ?? 255, 0, 255)}
            ${numberField("touchpad-2-location", "Touchpad 2 location", system.touchpad_2_location ?? 255, 0, 255)}
            ${boolSelect("ac-button-blocked", "Block AC button", !!system.ac_button_blocked)}
            ${boolSelect("param-show-outside-temp", "Outside temp", !!system.show_outside_temp)}
            ${boolSelect("lock-to-temp-control", "Lock temp control", !!system.lock_to_temp_control)}
            ${boolSelect("param-show-control-sensor", "Control sensor", !!system.show_control_sensor)}
          </div>
          <div class="service-actions"><button type="button" data-service-action="parameters">Save Parameters</button></div>
        </article>
        ${metric("Device ID", system.device_id || "-")}
        ${metric("Firmware", system.firmware_version_raw || "-")}
        ${metric("Sensors", (system.sensor_addresses || []).join(", ") || "-")}`;
      $("system").innerHTML = `
        <article class="card">
          <div class="card-title">Service Reminder</div>
          <div class="field-grid">
            ${boolSelect("show-service-due", "Show service due", !!service.show_service_due)}
            ${boolSelect("service-due-locked", "Lock service due", !!service.service_due_locked)}
            ${boolSelect("filter-clean-due", "Filter clean due", !!service.filter_clean_due)}
            ${boolSelect("maintenance-due", "Maintenance due", !!service.maintenance_due)}
            ${numberField("service-months", "Months", service.months ?? 0, 0, 255)}
            ${numberField("service-days", "Days", service.days ?? 0, 0, 65535)}
            ${numberField("service-runtime-hours", "Runtime hours", service.runtime_hours ?? 0, 0, 4294967295)}
          </div>
          <div class="service-actions"><button type="button" data-service-action="service-contact">Save Service</button></div>
        </article>
        ${metric("Password Pages", Object.keys(state.password || {}).length)}
        ${metric("Last LED", (state.last_led || {}).led_code ?? "-")}
        ${metric("Supply Air", (system.supply_air || []).map((item) => item.status || item.temperature || "-").join(", ") || "-")}
        ${metric("Touchpads", (((system.sensor_list || {}).touchpad_addresses) || []).map((item) => `0x${Number(item).toString(16).toUpperCase()}`).join(", ") || "-")}
        ${metric("Runtime", (system.expanded || {}).software_version || "-")}`;
    }

    function renderState(payload, eventsPayload = {}) {
      const controller = payload.controller || {};
      const runtime = (payload.runtime && payload.runtime.runtime) || {};
      const transactions = (payload.runtime && payload.runtime.transactions) || {};
      const state = (payload.runtime && payload.runtime.state) || {};
      latestState = state;
      const integrations = payload.integrations || {};
      const config = controller.config || {};
      configuredTheme = config.ui_theme || "system";
      applyTheme();
      $("app-title").textContent = detectAirTouchModel(state);
      renderAlerts(collectAlerts(controller, state, integrations, transactions));
      renderWeather(integrations);
      renderIndoor(integrations, state);
      const acEntries = visibleAcs(state);
      if (!acEntries.some(([id]) => Number(id) === selectedAc)) selectedAc = Number(acEntries[0] && acEntries[0][0]) || 0;
      const allZoneEntries = zoneEntriesForAc(state, selectedAc);
      const activeZoneCount = allZoneEntries.filter(([_id, group]) => {
        const status = group.status || {};
        return status.power_name === "on" || status.power_name === "turbo";
      }).length;

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
      $("ac-count").textContent = String(acEntries.length);
      $("acs").innerHTML = acEntries.length
        ? acCard(String(selectedAc), selectedAcRecord, allZoneEntries)
        : '<div class="muted">No AC data</div>';

      const groups = state.active_groups || state.groups || {};
      const zoneEntries = allZoneEntries;
      const pageCount = Math.max(1, Math.ceil(zoneEntries.length / 8));
      if (zonePage >= pageCount) zonePage = pageCount - 1;
      const pageStart = zonePage * 8;
      const pageEntries = zoneEntries.slice(pageStart, pageStart + 8);
      $("zone-count").textContent = String(zoneEntries.length);
      $("zone-active-count").textContent = `${activeZoneCount} active`;
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
          await sendCommand("balance_start", {current_values: balanceValuesFromPage()});
        } else if (action === "balance-zone") {
          const zone = Number(button.dataset.zone);
          await sendCommand("balance_start", {
            current_values: balanceValuesFromPage(),
            zone,
            value: Number(document.querySelector(`[data-balance-value="${zone}"]`).value)
          });
        } else if (action === "balance-stop") {
          await sendCommand("balance_stop", {current_values: balanceValuesFromPage()});
        } else if (action === "ac-base-info") {
          const ac = Number(button.dataset.ac);
          const card = button.closest("[data-service-ac]");
          const records = acBaseRecordsFromState();
          const record = records.find((item) => item.ac === ac);
          if (!record) throw new Error(`No AC base state for AC ${ac + 1}`);
          record.name = card.querySelector('[data-field="ac-name"]').value;
          record.group_start = Number(card.querySelector('[data-field="ac-group-start"]').value);
          record.group_count = Number(card.querySelector('[data-field="ac-group-count"]').value);
          record.brand = Number(card.querySelector('[data-field="ac-brand"]').value);
          await sendCommand("ac_base_info", {
            one_duct_system: !!((latestState.system || {}).one_duct_system),
            ac_count: records.length,
            records
          });
        } else if (action === "ac-setting-new") {
          const ac = Number(button.dataset.ac);
          const card = button.closest("[data-service-ac]");
          const records = acSettingRecordsFromState();
          const record = records.find((item) => item.ac === ac);
          if (!record) throw new Error(`No AC setting state for AC ${ac + 1}`);
          record.hide_spill_group = fieldBool(card, "hide-spill");
          record.ctrl_thermostat = fieldNumber(card, "ctrl-thermostat");
          record.cool_adjust = fieldNumber(card, "cool-adjust");
          record.heat_adjust = fieldNumber(card, "heat-adjust");
          record.min_setpoint = fieldNumber(card, "min-setpoint");
          record.max_setpoint = fieldNumber(card, "max-setpoint");
          record.auto_off = fieldBool(card, "auto-off");
          record.on_time_limit = fieldNumber(card, "on-time-limit");
          record.modes = {
            auto: fieldBool(card, "mode-auto"),
            cool: fieldBool(card, "mode-cool"),
            heat: fieldBool(card, "mode-heat"),
            dry: fieldBool(card, "mode-dry"),
            fan: fieldBool(card, "mode-fan")
          };
          record.fan_values = {
            auto: fieldNumber(card, "fan-auto"),
            quiet: fieldNumber(card, "fan-quiet"),
            low: fieldNumber(card, "fan-low"),
            medium: fieldNumber(card, "fan-medium"),
            high: fieldNumber(card, "fan-high"),
            powerful: fieldNumber(card, "fan-powerful"),
            turbo: fieldNumber(card, "fan-turbo")
          };
          record.selector_visibility = {
            auto: fieldBool(card, "selector-auto"),
            touchpad_1: fieldBool(card, "selector-touchpad_1"),
            touchpad_2: fieldBool(card, "selector-touchpad_2"),
            average: fieldBool(card, "selector-average"),
            economy: fieldBool(card, "selector-economy"),
            groups_1_8_bitmap: fieldNumber(card, "selector-groups-1"),
            groups_9_16_bitmap: fieldNumber(card, "selector-groups-2")
          };
          await sendCommand("ac_setting_new", {records});
        } else if (action === "turbo-group") {
          const ac = Number(button.dataset.ac);
          const card = button.closest("[data-service-ac]");
          await sendCommand("turbo_group", {
            ac,
            group: fieldNumber(card, "turbo-group"),
            current_groups: turboGroupsFromState(),
            one_duct_system: !!((latestState.system || {}).one_duct_system),
            ac_count: Math.max(1, visibleAcs(latestState).length)
          });
        } else if (action === "preference") {
          const preferenceCard = button.closest(".card") || $("service-parameters");
          await sendCommand("preference", {
            system_name: $("system-name-input").value,
            show_ac_errors: fieldBool(preferenceCard, "show-ac-errors"),
            show_outside_temp: fieldBool(preferenceCard, "pref-show-outside-temp"),
            show_control_sensor: fieldBool(preferenceCard, "pref-show-control-sensor"),
            use_fahrenheit: fieldBool(preferenceCard, "use-fahrenheit"),
            location: fieldNumber(preferenceCard, "location"),
            screensaver_enabled: fieldBool(preferenceCard, "screensaver-enabled"),
            screensaver_timeout: fieldNumber(preferenceCard, "screensaver-timeout")
          });
        } else if (action === "parameters") {
          const card = button.closest(".card");
          await sendCommand("parameters", {
            group_count: fieldNumber(card, "group-count"),
            damper_rpm: fieldNumber(card, "damper-rpm"),
            touchpad_1_location: fieldNumber(card, "touchpad-1-location"),
            touchpad_2_location: fieldNumber(card, "touchpad-2-location"),
            ac_button_blocked: fieldBool(card, "ac-button-blocked"),
            show_outside_temp: fieldBool(card, "param-show-outside-temp"),
            lock_to_temp_control: fieldBool(card, "lock-to-temp-control"),
            show_control_sensor: fieldBool(card, "param-show-control-sensor")
          });
        } else if (action === "service-contact") {
          const serviceCard = button.closest(".card") || $("service-system");
          await sendCommand("service", {
            company: $("service-company-input").value,
            phone: $("service-phone-input").value,
            show_service_due: fieldBool(serviceCard, "show-service-due"),
            service_due_locked: fieldBool(serviceCard, "service-due-locked"),
            filter_clean_due: fieldBool(serviceCard, "filter-clean-due"),
            maintenance_due: fieldBool(serviceCard, "maintenance-due"),
            months: fieldNumber(serviceCard, "service-months"),
            days: fieldNumber(serviceCard, "service-days"),
            runtime_hours: fieldNumber(serviceCard, "service-runtime-hours")
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
      const button = event.target.closest("button[data-action]");
      if (!button) return;
      const action = button.dataset.action;
      const favourite = button.dataset.favourite;
      pendingFavourites.add(favourite);
      try {
        if (action === "active-favourite") {
          await sendCommand("active_favourite", {favourite: Number(favourite)});
        } else if (action === "favourite-save") {
          const card = button.closest("[data-favourite-card]");
          await sendCommand("favourite", {
            favourite: Number(favourite),
            name: card.querySelector('[data-field="favourite-name"]').value,
            groups: favouriteGroupsFromCard(card)
          });
        }
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

    $("view-programs").addEventListener("click", async (event) => {
      const button = event.target.closest("button[data-program-action]");
      if (!button) return;
      const previous = button.textContent;
      button.disabled = true;
      button.textContent = "Saving";
      try {
        if (button.dataset.programAction === "program-save") {
          const program = Number(button.dataset.program);
          const card = button.closest("[data-program]");
          const records = programRecordsFromState();
          const record = records.find((item) => item.program === program);
          if (!record) throw new Error(`No program state for program ${program + 1}`);
          record.name = card.querySelector('[data-field="program-name"]').value;
          record.enabled = card.querySelector('[data-field="program-enabled"]').value === "true";
          record.days_bitmap = Number(card.querySelector('[data-field="program-days"]').value);
          record.groups_1_8_bitmap = Number(card.querySelector('[data-field="program-groups-1"]').value);
          record.groups_9_16_bitmap = Number(card.querySelector('[data-field="program-groups-2"]').value);
          record.active_ac_bitmap = Number(card.querySelector('[data-field="program-acs"]').value);
          record.on_timer = timerFromCard(card, "on");
          record.off_timer = timerFromCard(card, "off");
          record.on_setpoint = Number(card.querySelector('[data-field="program-on-setpoint"]').value);
          await sendCommand("program_define_new", {
            program_count: Number((latestState.system || {}).program_count ?? records.length),
            linked_ac: !!((latestState.system || {}).programs_linked_ac),
            records
          });
        } else if (button.dataset.programAction === "ac-timer-save") {
          const ac = Number(button.dataset.ac);
          const card = button.closest("[data-ac-timer]");
          const records = acTimerRecordsFromState();
          const record = records.find((item) => item.ac === ac);
          if (!record) throw new Error(`No AC timer state for AC ${ac + 1}`);
          record.on_timer = timerFromCard(card, "on");
          record.off_timer = timerFromCard(card, "off");
          await sendCommand("ac_timer_table", {records, ac_count: records.length || 4});
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
    window.addEventListener("resize", () => requestAnimationFrame(updateAlertTicker));
    refresh();
    setInterval(refresh, 1500);
  </script>
</body>
</html>
"""

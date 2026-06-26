"""Ingress UI for the AirTouch runtime service."""

from __future__ import annotations


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>OpenAirtouch</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #000000;
      --panel: var(--card-background-color, #ffffff);
      --panel-soft: var(--secondary-background-color, #f7f7f5);
      --panel-deep: #eeeeeb;
      --ink: var(--primary-text-color, #20201e);
      --muted: var(--secondary-text-color, #6f706b);
      --line: var(--divider-color, #deded8);
      --ok: var(--success-color, #14795a);
      --bad: var(--error-color, #b42318);
      --warn: var(--warning-color, #996700);
      --accent: #4f5d75;
      --accent-soft: #eceff5;
      --cool: #2d6cdf;
      --warm: #b45f06;
      --led-blue: #1e88ff;
      --led-purple: #8b5cf6;
      --led-red: var(--error-color, #e02b20);
      --led-amber: var(--warning-color, #d18b00);
      --header: #000000;
      --header-ink: var(--text-primary-color, #ffffff);
      --active-bg: #4f5d75;
      --active-ink: var(--text-primary-color, #ffffff);
      --shadow: 0 18px 36px rgba(32, 32, 30, .12);
      --shadow-soft: 0 8px 20px rgba(32, 32, 30, .08);
      --glass: rgba(255, 255, 255, .76);
      --lcd: #fafaf8;
    }
    body[data-theme="dark"] {
      color-scheme: dark;
      --bg: #000000;
      --panel: var(--card-background-color, #1b1b19);
      --panel-soft: var(--secondary-background-color, #242421);
      --panel-deep: #151514;
      --ink: var(--primary-text-color, #eeeeea);
      --muted: var(--secondary-text-color, #aaa9a2);
      --line: var(--divider-color, #3a3a35);
      --ok: var(--success-color, #42b883);
      --bad: var(--error-color, #ff6b5f);
      --warn: var(--warning-color, #d8a63c);
      --accent: #9aa8c7;
      --accent-soft: #22283a;
      --cool: #73a7ff;
      --warm: #f0a650;
      --led-blue: #49a8ff;
      --led-purple: #a78bfa;
      --led-red: var(--error-color, #ff5a4f);
      --led-amber: var(--warning-color, #f0b23e);
      --header: #000000;
      --header-ink: #f6f6f2;
      --active-bg: #9aa8c7;
      --active-ink: #111318;
      --shadow: 0 10px 28px rgba(0, 0, 0, .22);
      --shadow-soft: 0 4px 14px rgba(0, 0, 0, .18);
      --glass: rgba(27, 27, 25, .78);
      --lcd: #171716;
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
    .header-status {
      width: 18px;
      min-width: 18px;
      justify-content: center;
    }
    .header-status .status-text {
      display: none;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 0;
    }
    .dot {
      width: 12px;
      height: 12px;
      border-radius: 999px;
      background: var(--led-amber);
      flex: 0 0 auto;
      box-shadow: 0 0 0 2px rgba(255,255,255,.18), 0 0 12px color-mix(in srgb, var(--led-amber) 72%, transparent);
    }
    .led-blue .dot {
      background: var(--led-blue);
      box-shadow: 0 0 0 2px rgba(255,255,255,.18), 0 0 14px color-mix(in srgb, var(--led-blue) 74%, transparent);
    }
    .led-purple .dot {
      background: var(--led-purple);
      box-shadow: 0 0 0 2px rgba(255,255,255,.18), 0 0 14px color-mix(in srgb, var(--led-purple) 74%, transparent);
    }
    .led-red .dot {
      background: var(--led-red);
      box-shadow: 0 0 0 2px rgba(255,255,255,.18), 0 0 14px color-mix(in srgb, var(--led-red) 78%, transparent);
    }
    .led-amber .dot {
      background: var(--led-amber);
      box-shadow: 0 0 0 2px rgba(255,255,255,.18), 0 0 12px color-mix(in srgb, var(--led-amber) 72%, transparent);
    }
    .led-blue-red .dot {
      animation: led-blue-red 2s steps(1, end) infinite;
    }
    @keyframes led-blue-red {
      0%, 49% {
        background: var(--led-blue);
        box-shadow: 0 0 0 2px rgba(255,255,255,.18), 0 0 14px color-mix(in srgb, var(--led-blue) 74%, transparent);
      }
      50%, 100% {
        background: var(--led-red);
        box-shadow: 0 0 0 2px rgba(255,255,255,.18), 0 0 14px color-mix(in srgb, var(--led-red) 78%, transparent);
      }
    }
    .nav {
      grid-column: 1 / -1;
      display: grid;
      grid-template-columns: minmax(0, max-content) auto;
      gap: 8px;
      width: 100%;
      align-items: stretch;
      justify-content: space-between;
    }
    .nav-group {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      padding: 4px;
      border: 1px solid rgba(255,255,255,.14);
      border-radius: 8px;
      background: rgba(255,255,255,.06);
    }
    .nav-pages {
      min-width: 0;
      width: fit-content;
      max-width: 100%;
      justify-self: start;
    }
    .nav-settings {
      flex: 0 0 auto;
    }
    .nav .settings-tab {
      width: 50px;
      min-width: 50px;
      min-height: 44px;
      font-size: 22px;
      line-height: 1;
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
    .chip-stack {
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
      background: var(--panel);
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
      background: var(--panel);
      display: grid;
      gap: 16px;
      min-height: 430px;
      box-shadow: var(--shadow-soft);
    }
    .ac-panel.on {
      border-color: color-mix(in srgb, var(--ok) 54%, var(--line));
      background: var(--panel);
    }
    .ac-panel.off {
      background: color-mix(in srgb, var(--panel) 62%, var(--bg));
    }
    .ac-panel.off .thermostat-face,
    .ac-panel.off .ac-mode-bank,
    .ac-panel.off .ac-stat-grid,
    .ac-panel.off .thermostat-stepper {
      opacity: .58;
    }
    .ac-top {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(360px, 440px) 46px;
      gap: 10px;
      align-items: start;
    }
    .ac-name { font-size: 26px; font-weight: 780; overflow-wrap: anywhere; }
    .ac-stat-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(72px, 1fr));
      gap: 8px;
      width: min(440px, 100%);
      justify-self: end;
      margin-top: 2px;
    }
    .ac-stat-pill {
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 7px 10px;
      background: var(--lcd);
      display: grid;
      gap: 1px;
      line-height: 1.1;
    }
    .ac-stat-pill span:first-child {
      color: var(--muted);
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
    }
    .ac-stat-pill span:last-child {
      color: var(--ink);
      font-size: 13px;
      font-weight: 760;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .thermostat-face {
      width: min(236px, 100%);
      aspect-ratio: 1;
      margin: 0 auto 2px;
      border-radius: 999px;
      background:
        radial-gradient(circle at center, var(--lcd) 0 60%, transparent 61%),
        conic-gradient(from 225deg, var(--cool) 0deg, var(--warm) 270deg, transparent 270deg 360deg);
      box-shadow: var(--shadow-soft);
      display: grid;
      place-items: center;
      position: relative;
      overflow: hidden;
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
      font-size: 42px;
      line-height: 1;
      font-weight: 800;
      letter-spacing: 0;
      white-space: nowrap;
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
      background: var(--panel);
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
    .theme-choices {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .theme-choices .option {
      min-width: 96px;
      justify-content: center;
    }
    .group-tile.on {
      border-color: color-mix(in srgb, var(--ok) 50%, var(--line));
      background: var(--panel);
      box-shadow: var(--shadow-soft);
    }
    .group-tile.off {
      background: color-mix(in srgb, var(--panel) 60%, var(--bg));
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
      background: var(--panel);
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
      height: 46px;
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
      fill: color-mix(in srgb, var(--muted) 10%, transparent);
      stroke: none;
    }
    .temp-line .axis {
      stroke: var(--line);
      stroke-width: 1;
    }
    .temp-line .damper-line {
      fill: none;
      stroke: color-mix(in srgb, var(--muted) 58%, var(--panel));
      stroke-width: 1.4;
      stroke-linecap: round;
      stroke-linejoin: round;
      stroke-dasharray: 2.4 3.2;
      opacity: .62;
    }
    .temp-line .prediction-line {
      fill: none;
      stroke: var(--warm);
      stroke-width: 1.7;
      stroke-linecap: round;
      stroke-linejoin: round;
      stroke-dasharray: 4 3;
      opacity: .82;
    }
    .temp-line .context-line {
      fill: none;
      stroke: color-mix(in srgb, var(--muted) 62%, var(--panel));
      stroke-width: 1.2;
      stroke-linecap: round;
      stroke-linejoin: round;
      stroke-dasharray: 2 4;
      opacity: .66;
    }
    .temp-line .now-line {
      stroke: color-mix(in srgb, var(--ink) 42%, transparent);
      stroke-width: 1;
      stroke-dasharray: 2 3;
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
      background: var(--accent);
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
      background: var(--active-bg);
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
    #ac-timers {
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      align-items: start;
    }
    .ac-timer-card {
      min-height: 0;
    }
    .timer-stack {
      display: grid;
      grid-template-columns: 1fr;
      gap: 10px;
    }
    .timer-block {
      display: grid;
      gap: 8px;
      padding: 9px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: color-mix(in srgb, var(--panel-soft) 72%, transparent);
    }
    .timer-block-title {
      color: var(--ink);
      font-size: 13px;
      font-weight: 760;
    }
    input,
    select {
      width: 100%;
      min-height: 36px;
      border: 1px solid var(--line);
      border-radius: 5px;
      background: var(--panel-soft);
      color: var(--ink);
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
    .check-row.compact {
      min-height: 30px;
      font-size: 12px;
    }
    .chip-grid {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .model-row {
      display: grid;
      grid-template-columns: minmax(130px, 1.2fr) minmax(220px, 2fr) auto;
      align-items: center;
      gap: 8px;
      width: 100%;
      padding: 6px 0;
      border-bottom: 1px solid var(--line);
    }
    .model-row:last-child { border-bottom: 0; }
    .model-row .model-actions {
      display: flex;
      gap: 6px;
      justify-content: flex-end;
      flex-wrap: wrap;
    }
    .model-row button {
      min-height: 30px;
      padding: 5px 8px;
    }
    .analytics-rows {
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 8px;
    }
    .analytics-row {
      min-height: 92px;
      display: grid;
      grid-template-columns: minmax(150px, .9fr) minmax(420px, 2.8fr) minmax(280px, 1.4fr) auto;
      gap: 12px;
      align-items: center;
    }
    .analytics-row-main {
      display: grid;
      gap: 6px;
      min-width: 0;
    }
    .analytics-row .tile-foot {
      min-height: auto;
      align-content: center;
    }
    .analytics-row-chart {
      min-width: 0;
    }
    .analytics-sparkline {
      display: grid;
      gap: 4px;
      min-width: 0;
    }
    .analytics-sparkline-meta {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      color: var(--muted);
      font-size: 11px;
      line-height: 1.1;
    }
    .analytics-row-metrics {
      min-width: 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.25;
    }
    .analytics-model-badges {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      min-width: 0;
    }
    .model-badge {
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 5px 8px;
      background: var(--lcd);
      display: inline-flex;
      align-items: baseline;
      gap: 5px;
      line-height: 1.1;
    }
    .model-badge span:first-child {
      color: var(--muted);
      font-size: 10px;
      font-weight: 720;
      text-transform: uppercase;
    }
    .model-badge span:last-child {
      color: var(--ink);
      font-size: 11px;
      font-weight: 760;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .analytics-row-actions {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }
    .balance-rows {
      display: grid;
      gap: 8px;
    }
    .sensor-rows {
      display: grid;
      gap: 8px;
    }
    .sensor-row {
      min-height: 82px;
      display: grid;
      grid-template-columns: minmax(150px, 1.2fr) minmax(120px, .8fr) minmax(160px, 1fr) minmax(190px, 1.2fr);
      gap: 12px;
      align-items: center;
    }
    .sensor-row-main {
      display: grid;
      gap: 4px;
      min-width: 0;
    }
    .sensor-row-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      min-width: 0;
    }
    .sensor-row-temp {
      display: grid;
      gap: 3px;
      min-width: 0;
    }
    .sensor-calibration {
      display: grid;
      grid-template-columns: minmax(140px, 1fr) 54px;
      gap: 8px;
      align-items: center;
      min-width: 0;
    }
    .sensor-calibration input[type="range"] {
      min-height: 32px;
    }
    @media (max-width: 880px) {
      .sensor-row {
        grid-template-columns: minmax(0, 1fr);
        align-items: stretch;
      }
    }
    .balance-row {
      min-height: 76px;
      display: grid;
      grid-template-columns: minmax(140px, 1.1fr) minmax(120px, .8fr) minmax(240px, 1.7fr) auto;
      gap: 12px;
      align-items: center;
    }
    .balance-row-main {
      display: grid;
      gap: 4px;
      min-width: 0;
    }
    .balance-row-value {
      display: grid;
      gap: 3px;
      min-width: 0;
    }
    .balance-row-control {
      display: grid;
      grid-template-columns: minmax(160px, 1fr) 72px;
      gap: 8px;
      align-items: center;
      min-width: 0;
    }
    .balance-row-control input[type="number"] {
      min-height: 38px;
    }
    .balance-actions {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }
    @media (max-width: 880px) {
      .balance-row {
        grid-template-columns: minmax(0, 1fr);
        align-items: stretch;
      }
      .balance-actions {
        justify-content: flex-start;
      }
    }
    @media (max-width: 880px) {
      .analytics-row {
        grid-template-columns: minmax(0, 1fr);
        align-items: stretch;
      }
      .analytics-row-actions {
        justify-content: flex-start;
      }
    }
    .day-chip input {
      position: absolute;
      opacity: 0;
      pointer-events: none;
    }
    .day-chip span {
      display: inline-flex;
      min-width: 42px;
      min-height: 30px;
      align-items: center;
      justify-content: center;
      padding: 5px 9px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--panel-soft);
      color: var(--ink);
      font-weight: 720;
    }
    .day-chip input:checked + span {
      border-color: var(--accent);
      background: var(--active-bg);
      color: var(--active-ink);
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
    details.advanced-panel {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 8px;
      background: color-mix(in srgb, var(--panel-soft) 70%, transparent);
    }
    details.advanced-panel summary {
      cursor: pointer;
      color: var(--muted);
      font-weight: 740;
    }
    details.advanced-panel[open] summary {
      margin-bottom: 10px;
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
      .nav {
        grid-template-columns: minmax(0, 1fr) auto;
      }
      .nav-pages {
        width: auto;
        justify-self: stretch;
      }
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
      .ac-top {
        grid-template-columns: minmax(0, 1fr) 46px;
      }
      .ac-top .ac-stat-grid {
        grid-column: 1 / -1;
        justify-self: stretch;
        width: 100%;
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
    <div class="brand">
      <div id="status" class="status header-status led-amber" title="Connecting" aria-label="Connecting"><span class="dot"></span><span class="status-text">Connecting</span></div>
      <h1 id="app-title">OpenAirtouch</h1>
    </div>
    <div class="header-actions">
      <div class="chip-stack">
        <div id="weather-chip" class="weather-chip"></div>
        <div id="indoor-chip" class="weather-chip"></div>
      </div>
    </div>
    <nav class="nav" aria-label="Primary">
      <div class="nav-group nav-pages">
        <button type="button" class="active" data-view-button="control">Control</button>
        <button type="button" data-view-button="programs">Favourites & Programs</button>
        <button type="button" data-view-button="adaptive">Adaptive</button>
      </div>
      <div class="nav-group nav-settings">
        <button type="button" class="settings-tab" data-view-button="settings" aria-label="Settings" title="Settings">&#9881;</button>
      </div>
    </nav>
  </header>
  <main>
    <div id="view-control" class="view active">
      <div id="error-strip" class="error-strip" aria-live="polite"><div id="error-track" class="error-track"></div></div>
      <div class="control-grid">
        <section>
          <div class="section-title"><strong id="zone-count">0/0 Zones</strong></div>
          <div class="zone-toolbar">
            <div class="zone-pages" id="zone-pages"></div>
          </div>
          <div class="groups-board" id="groups"></div>
        </section>
        <section>
          <div class="section-title"><strong id="ac-count">0 ACs</strong></div>
          <div class="ac-selector" id="ac-selector"></div>
          <div class="ac-board" id="acs"></div>
        </section>
      </div>
    </div>

    <div id="view-programs" class="view">
      <div class="subnav" aria-label="Favourites And Programs">
        <button type="button" class="active" data-subview-button="programs" data-subview="favourites">Favourites</button>
        <button type="button" data-subview-button="programs" data-subview="program-list">Programs</button>
        <button type="button" data-subview-button="programs" data-subview="ac-timer">AC Timer</button>
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
    </div>

    <div id="view-adaptive" class="view">
      <div class="subnav" aria-label="Adaptive Pages">
        <button type="button" class="active" data-subview-button="adaptive-page" data-subview="status">Status</button>
        <button type="button" data-subview-button="adaptive-page" data-subview="config">Config</button>
        <button type="button" data-subview-button="adaptive-page" data-subview="analytics">Analytics</button>
      </div>
      <div id="adaptive-page-status" class="subview active">
        <section>
          <h2>Adaptive</h2>
          <div class="cards" id="adaptive-status"></div>
        </section>
      </div>
      <div id="adaptive-page-config" class="subview">
        <section>
          <h2>Adaptive Config</h2>
          <article class="card">
            <div class="field-grid">
              <div class="field">
                <label>Control Mode</label>
                <select id="adaptive-mode">
                  <option value="off">Off</option>
                  <option value="recommend">Recommend</option>
                  <option value="auto_off">Auto Off</option>
                  <option value="adaptive">Adaptive</option>
                </select>
              </div>
              <div class="field"><label>Cool Differential</label><input id="adaptive-cool-diff" type="number" min="0" max="15" step="1"></div>
              <div class="field"><label>Cool Comfort Limit</label><input id="adaptive-cool-comfort-temp" type="number" min="16" max="32" step="1"></div>
              <div class="field"><label>Heat Differential</label><input id="adaptive-heat-diff" type="number" min="0" max="15" step="1"></div>
              <div class="field"><label>Heat Comfort Limit</label><input id="adaptive-heat-comfort-temp" type="number" min="16" max="32" step="1"></div>
              <div class="field"><label>Check Interval</label><input id="adaptive-check-interval" type="number" min="5" max="3600" step="5"></div>
              <div class="field"><label>Command Cooldown</label><input id="adaptive-command-cooldown" type="number" min="1" max="7200" step="10"></div>
              <div class="field">
                <label>MPC Control</label>
                <select id="adaptive-mpc-control">
                  <option value="off">Off</option>
                  <option value="control">Control</option>
                </select>
              </div>
              <div class="field"><label>MPC Horizon</label><input id="adaptive-mpc-horizon-hours" type="number" min="1" max="24" step="1"></div>
              <div class="field"><label>Minimum Run Time</label><input id="adaptive-compressor-min-run-time" type="number" min="0" step="60"></div>
              <div class="field"><label>Minimum Off Time</label><input id="adaptive-compressor-min-off-time" type="number" min="0" step="60"></div>
            </div>
            <div class="field">
              <label>Control Zones</label>
              <div class="chip-grid" id="adaptive-control-zones"></div>
            </div>
            <div class="service-actions">
              <button type="button" data-adaptive-save="true">Save Adaptive</button>
              <button type="button" class="secondary" data-adaptive-model-action="reset_all">Reset Models</button>
            </div>
          </article>
        </section>
      </div>
      <div id="adaptive-page-analytics" class="subview">
        <section>
          <h2>Analytics</h2>
          <div class="analytics-rows" id="adaptive-analytics-cards"></div>
        </section>
      </div>
    </div>

    <div id="view-settings" class="view">
      <div class="subnav" aria-label="Settings Pages">
        <button type="button" class="active" data-subview-button="settings" data-subview="app">App</button>
        <button type="button" data-subview-button="settings" data-subview="sensors">Sensors</button>
        <button type="button" data-subview-button="settings" data-subview="grouping">Grouping</button>
        <button type="button" data-subview-button="settings" data-subview="spill">Spill</button>
        <button type="button" data-subview-button="settings" data-subview="balance">Balance</button>
        <button type="button" data-subview-button="settings" data-subview="ac-setup">AC Setup</button>
        <button type="button" data-subview-button="settings" data-subview="parameters">Parameters</button>
        <button type="button" data-subview-button="settings" data-subview="system">System Info</button>
        <button type="button" data-subview-button="settings" data-subview="diagnostics">Diagnostics</button>
      </div>
      <div id="settings-app" class="subview active">
        <section>
          <h2>App Settings</h2>
          <div class="field-grid">
            <div class="field">
              <label>Theme</label>
              <div id="theme-selector" class="theme-choices" role="group" aria-label="Theme">
                <button type="button" class="option" data-theme-choice="system">&#128187; System</button>
                <button type="button" class="option" data-theme-choice="light">&#9728; Light</button>
                <button type="button" class="option" data-theme-choice="dark">&#9790; Dark</button>
              </div>
            </div>
          </div>
        </section>
      </div>
      <div id="settings-sensors" class="subview">
        <section>
          <h2>Sensors</h2>
          <div class="service-actions">
            <button type="button" data-service-action="pair-sensor" data-pairing="true">Start Pair</button>
            <button type="button" class="secondary" data-service-action="pair-sensor" data-pairing="false">Stop Pair</button>
          </div>
          <div class="sensor-rows" id="sensors"></div>
        </section>
      </div>
      <div id="settings-grouping" class="subview">
        <section>
          <h2>Grouping</h2>
          <div class="cards" id="grouping"></div>
        </section>
      </div>
      <div id="settings-spill" class="subview">
        <section>
          <h2>Spill</h2>
          <div class="cards" id="spill"></div>
        </section>
      </div>
      <div id="settings-balance" class="subview">
        <section>
          <h2>Balance</h2>
          <div class="balance-rows" id="balance"></div>
        </section>
      </div>
      <div id="settings-ac-setup" class="subview">
        <section>
          <h2>AC Setup</h2>
          <div class="cards" id="ac-setup"></div>
        </section>
      </div>
      <div id="settings-parameters" class="subview">
        <section>
          <h2>Parameters</h2>
          <div class="field-grid">
            <div class="field">
              <label for="system-name-input">System Name</label>
              <input id="system-name-input" maxlength="16" autocomplete="off">
            </div>
            <button type="button" data-service-action="preference">Save Name</button>
          </div>
          <div class="cards" id="parameters"></div>
        </section>
      </div>
      <div id="settings-system" class="subview">
        <section>
          <h2>System Info</h2>
          <div class="field-grid">
            <div class="field">
              <label for="service-company-input">Service Company</label>
              <input id="service-company-input" maxlength="10" autocomplete="off">
            </div>
            <div class="field">
              <label for="service-phone-input">Service Phone</label>
              <input id="service-phone-input" maxlength="12" autocomplete="off">
            </div>
            <button type="button" data-service-action="service-contact">Save Service</button>
          </div>
          <div class="cards" id="system"></div>
        </section>
      </div>
      <div id="settings-diagnostics" class="subview">
        <section class="diagnostics">
          <h2>Diagnostics</h2>
          <div class="cards" id="metrics"></div>
          <h2>System Debug</h2>
          <div class="cards" id="system-debug"></div>
          <table>
            <thead><tr><th>Type</th><th>Command</th><th>Message</th></tr></thead>
            <tbody id="events"></tbody>
          </table>
          <h2>Program Debug</h2>
          <div class="split">
            <div>
              <h3>Options</h3>
              <div class="json" id="program-options">{}</div>
            </div>
            <div>
              <h3>Summary</h3>
              <div class="json" id="program-summary">{}</div>
            </div>
          </div>
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
    let selectedAc = 0;
    let zonePage = 0;
    let configuredTheme = "system";
    let selectedTheme = localStorage.getItem(THEME_KEY) || "system";
    let latestState = {};
    let latestHealth = {ok: false, status: "Connecting"};
    let editingUntil = 0;
    let balanceCommitTimer = null;

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

    function titleText(value, fallback = "-") {
      const raw = text(value, fallback).replace(/_/g, " ");
      if (raw === "-") return raw;
      return raw
        .replace(/\b([a-z])/g, (match) => match.toUpperCase())
        .replace(/\b(Ac|Led|Mqtt|Tcp|Ui|Rx|Tx|Ok)\b/g, (match) => match.toUpperCase());
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
      return formatTemp(value);
    }

    function formatTemp(value, digits = null) {
      if (value === undefined || value === null) return "-";
      const number = Number(value);
      if (!Number.isFinite(number)) return "-";
      const formatted = digits === null
        ? (Number.isInteger(number) ? String(number) : number.toFixed(1))
        : number.toFixed(digits);
      return `${formatted}°`;
    }

    function formatExternalTemp(value, unit = "C", digits = null) {
      if (value === undefined || value === null) return "";
      const number = Number(value);
      if (!Number.isFinite(number)) return "";
      const suffix = String(unit || "C").toUpperCase().includes("F") ? "°F" : "°";
      const formatted = digits === null
        ? (Number.isInteger(number) ? String(number) : number.toFixed(1))
        : number.toFixed(digits);
      return `${formatted}${suffix}`;
    }

    function temperatureHistoryLine(history = []) {
      const entries = history
        .filter((entry) => Number.isFinite(Number(entry.temperature)))
        .slice(-24);
      const points = entries.map((entry) => Number(entry.temperature));
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
      const damperCoords = entries
        .map((entry, index) => {
          const value = Number(entry.percentage);
          if (!Number.isFinite(value)) return null;
          const bounded = Math.min(100, Math.max(0, value));
          const x = entries.length === 1 ? 0 : (index / (entries.length - 1)) * 120;
          const y = 24 - (bounded / 100) * 20;
          return [x, y];
        })
        .filter(Boolean);
      const damperLine = damperCoords.length >= 2
        ? damperCoords.map(([x, y], index) => `${index === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`).join(" ")
        : "";
      return `<div class="history-strip">
        <svg class="temp-line" viewBox="0 0 120 28" preserveAspectRatio="none" aria-hidden="true">
          <path class="area" d="${area}"></path>
          ${damperLine ? `<path class="damper-line" d="${damperLine}"></path>` : ""}
          <path d="${line}"></path>
        </svg>
        <div class="history-meta"><span>${escapeHtml(temp(points[0]))}</span><span>${escapeHtml(temp(points[points.length - 1]))}</span></div>
      </div>`;
    }

    function adaptiveSparkline(history = [], forecast = []) {
      const historyEntries = (Array.isArray(history) ? history : [])
        .map((point, index) => {
          if (typeof point === "number") return {x: null, actual: point, forecast: null, context: null};
          if (!point || typeof point !== "object") return null;
          return {
            x: finiteNumber(point.ts) ?? index,
            actual: finiteNumber(point.temperature ?? point.room_temperature ?? point.actual ?? point.value),
            forecast: finiteNumber(point.prediction ?? point.predicted_temperature ?? point.predicted),
            context: finiteNumber(point.outdoor_temperature),
          };
        })
        .filter((point) => point && (point.actual !== null || point.forecast !== null || point.context !== null))
        .slice(-36);
      const lastHistoryX = historyEntries.length ? historyEntries[historyEntries.length - 1].x : 0;
      const firstHistoryX = historyEntries.length ? historyEntries[0].x : lastHistoryX - 3600;
      const historySpan = Math.max(300, lastHistoryX - firstHistoryX);
      const forecastEntries = (Array.isArray(forecast) ? forecast : [])
        .map((point, index) => {
          if (typeof point === "number") return {x: lastHistoryX + ((index + 1) * 300), actual: null, forecast: point, context: null};
          if (!point || typeof point !== "object") return null;
          const offset = finiteNumber(point.offset_minutes);
          return {
            x: lastHistoryX + ((offset === null ? (index + 1) * 5 : offset) * 60),
            actual: null,
            forecast: finiteNumber(point.temperature ?? point.prediction ?? point.predicted_temperature ?? point.predicted),
            context: finiteNumber(point.outdoor_temperature),
          };
        })
        .filter((point) => point && (point.forecast !== null || point.context !== null))
        .slice(0, 96);
      const fallbackForecast = !forecastEntries.length
        ? historyEntries
            .filter((point) => point.forecast !== null)
            .map((point) => ({...point, actual: null}))
        : [];
      const futureEntries = forecastEntries.length ? forecastEntries : fallbackForecast;
      const values = historyEntries
        .concat(futureEntries)
        .flatMap((point) => [point.actual, point.forecast, point.context])
        .filter((value) => value !== null);
      const latestActual = historyEntries.map((point) => point.actual).filter((value) => value !== null).slice(-1)[0];
      const latestForecast = futureEntries.map((point) => point.forecast).filter((value) => value !== null).slice(-1)[0];
      if (values.length < 2) {
        return `<div class="analytics-sparkline"><svg class="temp-line" viewBox="0 0 160 44" preserveAspectRatio="none" aria-hidden="true"><line class="axis" x1="0" y1="28" x2="160" y2="28"></line><line class="now-line" x1="62" y1="4" x2="62" y2="40"></line></svg><div class="analytics-sparkline-meta"><span>History / Now / Forecast</span><span>${historyEntries.length} Points</span></div></div>`;
      }
      const min = Math.min(...values);
      const max = Math.max(...values);
      const spread = Math.max(1, max - min);
      const nowX = 62;
      const forecastSpan = Math.max(300, (futureEntries.slice(-1)[0]?.x ?? lastHistoryX + 3600) - lastHistoryX);
      const xFor = (point) => point.x <= lastHistoryX
        ? nowX - (((lastHistoryX - point.x) / historySpan) * nowX)
        : nowX + (((point.x - lastHistoryX) / forecastSpan) * (160 - nowX));
      const yFor = (value) => 38 - ((value - min) / spread) * 31;
      const pathFor = (entries, key) => entries
        .map((point) => {
          const value = point[key];
          if (value === null) return null;
          const x = xFor(point);
          const y = yFor(value);
          return `${x.toFixed(1)} ${y.toFixed(1)}`;
        })
        .filter(Boolean)
        .map((xy, index) => `${index === 0 ? "M" : "L"} ${xy}`)
        .join(" ");
      const contextEntries = historyEntries.concat(futureEntries);
      const actualLine = pathFor(historyEntries, "actual");
      const forecastLine = pathFor(futureEntries, "forecast");
      const contextLine = pathFor(contextEntries, "context");
      const label = `${latestActual === undefined ? "-" : temp(latestActual)} -> ${latestForecast === undefined ? "-" : temp(latestForecast)}`;
      return `<div class="analytics-sparkline"><svg class="temp-line" viewBox="0 0 160 44" preserveAspectRatio="none" aria-hidden="true">
        <line class="axis" x1="0" y1="28" x2="160" y2="28"></line>
        <line class="now-line" x1="${nowX}" y1="4" x2="${nowX}" y2="40"></line>
        ${contextLine ? `<path class="context-line" d="${contextLine}"></path>` : ""}
        ${actualLine ? `<path d="${actualLine}"></path>` : ""}
        ${forecastLine ? `<path class="prediction-line" d="${forecastLine}"></path>` : ""}
      </svg><div class="analytics-sparkline-meta"><span>History / Now / Forecast</span><span>${escapeHtml(label)}</span></div></div>`;
    }

    function modelValue(value, digits = 2, suffix = "") {
      const number = finiteNumber(value);
      return number === null ? "-" : `${number.toFixed(digits)}${suffix}`;
    }

    function timeConstantText(alpha) {
      const value = finiteNumber(alpha);
      if (value === null || value <= 0) return "-";
      const hours = 1 / value;
      return hours >= 10 ? `${Math.round(hours)} h` : `${hours.toFixed(1)} h`;
    }

    function modelBadge(label, value) {
      return `<div class="model-badge"><span>${escapeHtml(label)}</span><span>${escapeHtml(value)}</span></div>`;
    }

    function zoneHasAdaptiveTemperature(group, history, learningZone) {
      const status = (group || {}).status || {};
      if (Number.isFinite(Number(status.temperature))) return true;
      if (learningZone && Number.isFinite(Number(learningZone.last_temperature))) return true;
      return (Array.isArray(history) ? history : []).some((point) => {
        if (typeof point === "number") return Number.isFinite(point);
        return point && Number.isFinite(Number(point.temperature ?? point.room_temperature ?? point.actual ?? point.value));
      });
    }

    function adaptiveModelBadges(zone) {
      const confidence = finiteNumber(zone && zone.confidence);
      const std = finiteNumber(zone && zone.prediction_std);
      return [
        modelBadge("Confidence", confidence === null ? "-" : `${Math.round(confidence * 100)}%`),
        modelBadge("Error", std === null ? "-" : `${std.toFixed(2)}°`),
        modelBadge("Time Const", timeConstantText(zone && zone.alpha)),
        modelBadge("Solar Gain", modelValue(zone && zone.beta_solar, 2)),
        modelBadge("Drift", modelValue(zone && zone.passive_drift_per_hour, 2, "°/h")),
        modelBadge("Response", modelValue(zone && zone.active_response_per_hour, 2, "°/h")),
      ].join("");
    }

    function timeText(timer) {
      return timer && timer.enabled ? `${timer.hour}:${String(timer.minute).padStart(2, "0")}` : "-";
    }

    function timeValue(timer = {}) {
      const hour = Number(timer.hour ?? 0);
      const minute = Number(timer.minute ?? 0);
      return `${String(Number.isFinite(hour) ? hour : 0).padStart(2, "0")}:${String(Number.isFinite(minute) ? minute : 0).padStart(2, "0")}`;
    }

    function timerFields(prefix, timer = {}) {
      return `
        <div class="timer-block">
          <div class="timer-block-title">${prefix} Timer</div>
          <div class="field"><label>Enabled</label><select data-field="${prefix.toLowerCase()}-enabled">
            <option value="true" ${timer.enabled ? "selected" : ""}>On</option>
            <option value="false" ${!timer.enabled ? "selected" : ""}>Off</option>
          </select></div>
          <div class="field"><label>Time</label><input data-field="${prefix.toLowerCase()}-time" type="time" value="${escapeHtml(timeValue(timer))}"></div>
        </div>`;
    }

    function boolSelect(field, label, value) {
      return `<div class="field"><label>${escapeHtml(label)}</label><select data-field="${escapeHtml(field)}"><option value="true" ${value ? "selected" : ""}>On</option><option value="false" ${!value ? "selected" : ""}>Off</option></select></div>`;
    }

    function selectField(field, label, value, options) {
      return `<div class="field"><label>${escapeHtml(label)}</label><select data-field="${escapeHtml(field)}">${options.map(([optionValue, optionLabel]) => `<option value="${escapeHtml(optionValue)}" ${Number(optionValue) === Number(value) ? "selected" : ""}>${escapeHtml(optionLabel)}</option>`).join("")}</select></div>`;
    }

    function numberField(field, label, value, min, max) {
      return `<div class="field"><label>${escapeHtml(label)}</label><input data-field="${escapeHtml(field)}" type="number" min="${escapeHtml(min)}" max="${escapeHtml(max)}" value="${escapeHtml(value)}"></div>`;
    }

    function textField(field, label, value, maxlength = 16) {
      return `<div class="field"><label>${escapeHtml(label)}</label><input data-field="${escapeHtml(field)}" maxlength="${escapeHtml(maxlength)}" value="${escapeHtml(value || "")}" autocomplete="off"></div>`;
    }

    function markEditing() {
      editingUntil = Date.now() + 2500;
    }

    function isEditingForm() {
      const active = document.activeElement;
      return (active && active.matches && active.matches("input, select, textarea")) || Date.now() < editingUntil;
    }

    function themeToApply() {
      const theme = selectedTheme === "system" ? configuredTheme : selectedTheme;
      if (theme === "dark" || theme === "light") return theme;
      return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }

    function applyTheme() {
      document.body.dataset.theme = themeToApply();
      document.querySelectorAll("[data-theme-choice]").forEach((button) => {
        const active = button.dataset.themeChoice === selectedTheme;
        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", active ? "true" : "false");
      });
    }

    function modeName(value) {
      const modes = {0: "Auto", 1: "Heat", 2: "Dry", 3: "Fan", 4: "Cool", 7: "-"};
      return modes[value] || text(value);
    }

    function fanName(value) {
      const fans = {0: "Auto", 1: "Low", 2: "Med", 3: "High", 7: "-"};
      return fans[value] || text(value);
    }

    function formatProtocol(runtime) {
      const profile = runtime.protocol_name || titleText(runtime.protocol || "at4");
      const mode = text(runtime.protocol_mode || "auto").toUpperCase();
      const detected = runtime.detected_protocol ? titleText(runtime.detected_protocol) : "";
      if (runtime.protocol_mismatch) {
        return `${profile} / ${mode} / Mismatch${detected ? ` ${detected}` : ""}`;
      }
      return detected ? `${profile} / ${mode} / Detected ${detected}` : `${profile} / ${mode}`;
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
      const forecastError = integrations && integrations.forecast && integrations.forecast.error;
      if (forecastError) alerts.push(`Forecast weather: ${describeControllerError(forecastError)}`);
      const indoorError = integrations && integrations.indoor && integrations.indoor.error;
      if (indoorError) alerts.push(`Indoor climate: ${describeControllerError(indoorError)}`);
      const mqtt = integrations && integrations.mqtt;
      if (mqtt && mqtt.enabled && mqtt.error) alerts.push(`MQTT: ${describeControllerError(mqtt.error)}`);
      if (mqtt && mqtt.enabled && mqtt.error && Number(mqtt.failed_publish_count) > 0) {
        alerts.push(`MQTT publish failures: ${mqtt.failed_publish_count}`);
      }
      const errorResolver = integrations && integrations.error_resolver;
      if (errorResolver && errorResolver.enabled && errorResolver.last_error) {
        alerts.push(`Error lookup: ${describeControllerError(errorResolver.last_error)}`);
      }
      const adaptive = integrations && integrations.adaptive;
      if (adaptive && Array.isArray(adaptive.errors)) {
        adaptive.errors.forEach((error) => alerts.push(`Adaptive: ${describeControllerError(error)}`));
      }
      if (adaptive && adaptive.mode === "recommend" && Array.isArray(adaptive.recommendations)) {
        adaptive.recommendations.forEach((message) => alerts.push(`Adaptive: ${message}`));
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
      if (/ConnectionRefusedError|ECONNREFUSED/i.test(message)) return `Runtime Connection Refused: ${message}`;
      if (/TimeoutError|timed out/i.test(message)) return `Runtime Timeout: ${message}`;
      if (/SerialException|could not open port/i.test(message)) return `Serial Transport Error: ${message}`;
      if (/mqtt/i.test(message)) return `MQTT Error: ${message}`;
      return message;
    }

    function describeAcFault(code, display) {
      if (display && display.label) {
        return display.description ? `${display.label}: ${display.description}` : display.label;
      }
      const number = Number(code);
      if (number === 65534) return "Code: FFFE: Error In The Communication Of The Gateway With The Main Module.";
      if (number === 65535) return "Code: FFFF: Error In The Communication Of The Gateway With The AC Unit.";
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
      const tempText = formatExternalTemp(weather.temperature, unit);
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
      const entries = configuredGroupEntries(state || {});
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
        ? formatExternalTemp(indoor.temperature, tempUnit)
        : (average === null ? "" : formatTemp(average, 1));
      const humidityText = hasIndoorHumidity ? `${indoor.humidity} ${humidityUnit}` : "";
      chip.innerHTML = [
        '<span class="chip-label">Indoor</span>',
        tempText ? `<span>${escapeHtml(tempText)}</span>` : "",
        humidityText ? `<span>${escapeHtml(humidityText)}</span>` : ""
      ].filter(Boolean).join(" ");
      chip.classList.add("active");
    }

    function renderAdaptive(adaptive = {}, config = {}) {
      const current = adaptive.config || config || {};
      const setValue = (id, value) => {
        const element = $(id);
        if (element && document.activeElement !== element) element.value = value ?? "";
      };
      setValue("adaptive-mode", current.mode || adaptive.mode || "off");
      setValue("adaptive-cool-diff", current.cool_diff ?? 4);
      setValue("adaptive-cool-comfort-temp", current.cool_comfort_temp ?? 24);
      setValue("adaptive-heat-diff", current.heat_diff ?? 4);
      setValue("adaptive-heat-comfort-temp", current.heat_comfort_temp ?? 20);
      setValue("adaptive-check-interval", current.check_interval ?? 60);
      setValue("adaptive-command-cooldown", current.command_cooldown ?? 300);
      setValue("adaptive-mpc-control", current.learning_mode === "control" ? "control" : "off");
      setValue("adaptive-mpc-horizon-hours", current.mpc_horizon_hours ?? 6);
      setValue("adaptive-compressor-min-run-time", current.compressor_min_run_time ?? 0);
      setValue("adaptive-compressor-min-off-time", current.compressor_min_off_time ?? 0);
      const controlZones = new Set((current.control_zones || []).map((zone) => Number(zone)));
      const controlZoneContainer = $("adaptive-control-zones");
      if (controlZoneContainer && !controlZoneContainer.contains(document.activeElement)) {
        const entries = configuredGroupEntries(latestState || {});
        controlZoneContainer.innerHTML = entries.map(([id, group]) => {
          const zone = Number(id);
          const learningZone = ((adaptive.learning || {}).zones || {})[String(zone)] || {};
          const statusItems = [
            learningZone.learn === true ? "Learning" : "No Learning",
            controlZones.has(zone) ? "Control Enabled" : "Monitor",
          ].filter(Boolean).join(" / ");
          return `<label class="check-row compact">
            <input type="checkbox" data-adaptive-control-zone="${escapeHtml(zone)}" ${controlZones.has(zone) ? "checked" : ""}>
            <span>${escapeHtml(group.name || `Zone ${zone + 1}`)}</span>
            ${statusItems ? `<span class="pill">${escapeHtml(statusItems)}</span>` : ""}
          </label>`;
        }).join("") || '<span class="muted">No Zones</span>';
      }
      const outside = adaptive.outside_temperature === undefined || adaptive.outside_temperature === null
        ? "-"
        : formatTemp(adaptive.outside_temperature, 1);
      const recommendations = Array.isArray(adaptive.recommendations) ? adaptive.recommendations : [];
      const actions = Array.isArray(adaptive.actions) ? adaptive.actions : [];
      const errors = Array.isArray(adaptive.errors) ? adaptive.errors : [];
      const learning = adaptive.learning || {};
      const learningZones = learning.zones || {};
      const confidenceValues = Object.values(learningZones)
        .map((zone) => Number(zone && zone.confidence))
        .filter((value) => Number.isFinite(value));
      const confidence = confidenceValues.length
        ? `${Math.round((confidenceValues.reduce((total, value) => total + value, 0) / confidenceValues.length) * 100)}%`
        : "-";
      const zoneModels = Object.values(learningZones);
      const learningCount = zoneModels.filter((zone) => zone && zone.learn === true).length;
      const readyCount = zoneModels.filter((zone) => zone && zone.mpc_ready === true).length;
      const passiveSamples = zoneModels.reduce((total, zone) => total + Number((zone || {}).passive_samples || 0), 0);
      const activeSamples = zoneModels.reduce((total, zone) => total + Number((zone || {}).active_samples || 0), 0);
      const stdValues = zoneModels
        .map((zone) => Number(zone && zone.prediction_std))
        .filter((value) => Number.isFinite(value));
      const predictionStd = stdValues.length
        ? (stdValues.reduce((total, value) => total + value, 0) / stdValues.length).toFixed(2)
        : "-";
      const evaluations = Array.isArray(adaptive.evaluations) ? adaptive.evaluations : [];
      const mpcEvaluation = evaluations.slice().reverse().find((item) => item && item.mpc);
      const mpc = mpcEvaluation ? mpcEvaluation.mpc : null;
      const plans = learning.plans || {};
      const latestPlanEntry = Object.entries(plans).slice(-1)[0];
      const latestPlan = latestPlanEntry ? latestPlanEntry[1] : null;
      const mpcText = mpc
        ? `AC ${Number(mpcEvaluation.ac) + 1}: ${mpc.action || mpc.source || "mpc"} ${mpc.target ?? "-"} (${Math.round(Number(mpc.confidence || 0) * 100)}%)`
        : latestPlanEntry
          ? `AC ${Number(latestPlanEntry[0]) + 1}: ${latestPlan.action || latestPlan.source || "mpc"} ${latestPlan.target ?? "-"} (${Math.round(Number(latestPlan.confidence || 0) * 100)}%)`
          : "None";
      const compressor = learning.compressor || {};
      const compressorItems = Object.entries(compressor).map(([ac, state]) => {
        const seconds = state && state.seconds_since_change !== null && state.seconds_since_change !== undefined
          ? `${Math.round(Number(state.seconds_since_change))}s`
          : "-";
        return `AC ${Number(ac) + 1} ${state && state.power_on ? "On" : "Off"} ${seconds}`;
      });
      $("adaptive-status").innerHTML = [
        metric("Control Mode", titleText(adaptive.mode || current.mode || "off")),
        metric("MPC Control", current.learning_mode === "control" ? "Enabled" : "Off"),
        metric("Control Zones", `${controlZones.size} Enabled`),
        metric("Learning Models", `${Object.keys(learningZones).length} Models / ${learningCount} Learning / ${readyCount} Ready`),
        metric("Samples", `${passiveSamples} Passive / ${activeSamples} Active`),
        metric("Confidence", `${confidence} / Std ${predictionStd}`),
        metric("Latest Plan", mpcText),
        metric("Compressor Guard", compressorItems.join(", ") || "-"),
        metric("Outside", outside),
        metric("Active AC", (adaptive.active_ac || []).join(", ") || "-"),
        metric("Active Zones", (adaptive.active_groups || []).map((item) => Number(item) + 1).join(", ") || "-"),
        infoCard("Recommendations", recommendations.join(" / ") || "None"),
        infoCard("Actions", actions.join(" / ") || "None"),
        errors.length ? infoCard("Errors", errors.join(" / ")) : "",
      ].filter(Boolean).join("");
      const analyticsContainer = $("adaptive-analytics-cards");
      if (analyticsContainer) {
        const analyticsHistory = learning.analytics || {};
        const analyticsForecasts = learning.forecasts || {};
        const entries = configuredGroupEntries(latestState || {});
        analyticsContainer.innerHTML = entries.map(([id, group]) => {
          const zone = Number(id);
          const learningZone = learningZones[String(zone)] || {};
          const progress = Number(learningZone.learning_progress);
          const plan = plans[String(zone)] || null;
          const history = analyticsHistory[String(zone)] || analyticsHistory[zone] || [];
          const forecast = analyticsForecasts[String(zone)] || analyticsForecasts[zone] || [];
          if (!zoneHasAdaptiveTemperature(group, history, learningZone)) return "";
          const badges = [
            learningZone.learn === true ? '<span class="pill cool">Learning</span>' : '<span class="pill">Monitor</span>',
            controlZones.has(zone) ? '<span class="pill on">Control Enabled</span>' : '',
            learningZone.mpc_ready === true ? '<span class="pill cool">MPC Ready</span>' : '<span class="pill warn">Warming</span>',
            learningZone.accelerated_learning === true ? '<span class="pill warn">Fast</span>' : '',
          ].filter(Boolean).join("");
          const state = [
            Number.isFinite(progress) ? `Learning ${Math.round(progress * 100)}%` : "Learning -",
            `Idle ${Number(learningZone.passive_samples || learningZone.idle_samples || 0)}`,
            `Active ${Number(learningZone.active_samples || 0)}`,
            Number.isFinite(Number(learningZone.ekf_updates)) ? `Model Updates ${Number(learningZone.ekf_updates)}` : "",
            Number.isFinite(Number(learningZone.outside_coupling_per_hour)) ? `Outside ${Number(learningZone.outside_coupling_per_hour).toFixed(2)}/h` : "",
            learningZone.last_skip_reason ? `Skip ${titleText(learningZone.last_skip_reason)}` : "",
            learningZone.readiness_reason && learningZone.readiness_reason !== "ready" ? titleText(learningZone.readiness_reason) : "",
            plan ? `Plan ${titleText(plan.action || plan.source || "mpc")} ${plan.target ?? "-"}` : "",
          ].filter(Boolean).join(" / ");
          return `<article class="card analytics-row">
            <div class="analytics-row-main">
              <div class="card-title">${escapeHtml(group.name || `Zone ${zone + 1}`)}</div>
              <div class="analytics-row-metrics">${escapeHtml(state)}</div>
              <div class="tile-foot">${badges}</div>
            </div>
            <div class="analytics-row-chart">${adaptiveSparkline(history, forecast)}</div>
            <div class="analytics-model-badges">${adaptiveModelBadges(learningZone)}</div>
            <div class="analytics-row-actions">
              <button type="button" class="secondary" data-adaptive-model-action="accelerate_zone" data-zone="${escapeHtml(zone)}" data-enabled="${learningZone.accelerated_learning === true ? "false" : "true"}">${learningZone.accelerated_learning === true ? "Normal" : "Fast"}</button>
              <button type="button" class="secondary" data-adaptive-model-action="reset_zone" data-zone="${escapeHtml(zone)}">Reset</button>
            </div>
          </article>`;
        }).join("") || '<div class="muted">No Analytics</div>';
      }
    }

    function supplyAirText(items = []) {
      return items.map((item) => {
        if (item.temperature !== undefined && item.temperature !== null) return formatTemp(item.temperature);
        return item.status || "-";
      }).join(", ");
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
        const group = groups[i];
        if ((low & (1 << i)) && group) names.push(group.name || `Zone ${i + 1}`);
      }
      for (let i = 0; i < 8; i += 1) {
        const group = groups[i + 8];
        if ((high & (1 << i)) && group) names.push(group.name || `Zone ${i + 9}`);
      }
      return names;
    }

    function configuredGroupEntries(state) {
      const source = (state && (state.active_groups || state.groups)) || {};
      let entries = Object.entries(source).sort(([a], [b]) => Number(a) - Number(b));
      const count = Number(state && state.system && state.system.group_count);
      if (Number.isInteger(count) && count > 0) {
        entries = entries.filter(([id]) => Number(id) < count);
      }
      return entries;
    }

    function configuredGroups(state) {
      return Object.fromEntries(configuredGroupEntries(state));
    }

    function sensorName(value) {
      const sensor = Number(value);
      if (!Number.isFinite(sensor) || sensor === 255) return "None";
      if (sensor === 128) return "AC Sensor";
      if (sensor === 144) return "Touchpad 1";
      if (sensor === 145) return "Touchpad 2";
      if (sensor === 146) return "Average";
      if (sensor === 147) return "Economy";
      return `RF Sensor ${sensor}`;
    }

    function sensorKindLabel(kind) {
      if (kind === "rf") return "RF";
      if (kind === "touchpad") return "Touchpad";
      if (kind === "supply_air") return "Supply Air";
      return titleText(kind || "Sensor");
    }

    function sensorDisplayName(row) {
      if (!row) return "None";
      const id = Number(row.id);
      const fallback = Number.isFinite(id) ? sensorName(id) : titleText(row.name || row.id || "Sensor");
      const rawName = String(row.name || "");
      if (!rawName || rawName === `rf_sensor_${row.id}` || rawName === `sensor_addr_${row.id}`) return fallback;
      return titleText(rawName);
    }

    function sensorStatusPill(row) {
      const status = String(row.status || (row.present === false ? "missing" : row.listed ? "listed" : "unknown")).toLowerCase();
      const cls = status === "ok" || status === "listed" ? "pill on" : status === "missing" || status === "lost" || status === "error" ? "pill warn" : "pill";
      return `<span class="${cls}">${escapeHtml(titleText(status))}</span>`;
    }

    function sensorRowsFromState(state) {
      const view = Array.isArray(state.sensor_view) ? state.sensor_view : [];
      if (view.length) return view;
      return Object.entries(state.sensors || {}).map(([id, sensor]) => ({
        id: Number(id),
        address: Number(id) >= 0x80 ? `0x${Number(id).toString(16).toUpperCase()}` : id,
        name: sensor.sensor_name,
        kind: sensor.kind,
        temperature: sensor.temperature,
        status: sensor.status || (sensor.present === false ? "missing" : sensor.listed ? "listed" : "unknown"),
        present: sensor.present,
        listed: sensor.listed,
        signal: sensor.signal,
        battery: sensor.battery,
        low_battery: sensor.low_battery,
        mac: sensor.mac,
        mapped_groups: [],
      }));
    }

    function sensorOptions(state, currentValue) {
      const seen = new Set();
      const options = [[255, "None"], [144, "Touchpad 1"], [145, "Touchpad 2"], [146, "Average"]];
      sensorRowsFromState(state).forEach((row) => {
        const sensor = Number(row.id);
        if (Number.isFinite(sensor) && row.kind !== "supply_air") options.push([sensor, sensorDisplayName(row)]);
      });
      const current = Number(currentValue);
      if (Number.isFinite(current) && !options.some(([value]) => Number(value) === current)) {
        options.push([current, sensorName(current)]);
      }
      return options.filter(([value]) => {
        const key = Number(value);
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });
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
      const entries = configuredGroupEntries(state);
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

    function acForZone(state, groupId) {
      const group = Number(groupId);
      const acs = state.acs || {};
      const entries = Object.entries(acs);
      for (const [id, ac] of entries) {
        const base = (ac || {}).base || {};
        if (Number.isInteger(base.group_start) && Number.isInteger(base.group_count)) {
          const start = base.group_start;
          const end = start + base.group_count;
          if (group >= start && group < end) return [id, ac];
        }
      }
      return entries.length === 1 ? entries[0] : null;
    }

    function setpointLimitsForZone(state, groupId) {
      const entry = acForZone(state, groupId);
      if (!entry) return {min: 4, max: 35};
      const settings = (entry[1] || {}).settings || {};
      const min = finiteNumber(settings.min_setpoint);
      const max = finiteNumber(settings.max_setpoint);
      return {
        min: Math.max(4, min === null ? 4 : min),
        max: Math.min(35, max === null ? 35 : max),
      };
    }

    function ledStateFromHealth(health, led) {
      const label = health.ok ? "Running" : titleText(health.error, text(health.status, "Error"));
      if (!health.ok) {
        return {className: "led-red", label: `Runtime ${label}`};
      }
      const code = led && Number.isInteger(led.led_code) ? led.led_code : null;
      if (code === null) {
        return {className: "led-amber", label: `${label} / Waiting For Touchpad LED`};
      }
      if (code === 0x00) {
        return {className: "led-purple", label: `${label} / AC Off / No Error`};
      }
      if (code === 0x01) {
        return {className: "led-blue", label: `${label} / AC On`};
      }
      if (code === 0x16) {
        return {className: "led-blue-red", label: `${label} / Error`};
      }
      return {className: "led-amber", label: `${label} / Unmapped LED 0x${code.toString(16).toUpperCase().padStart(2, "0")}`};
    }

    function setStatus(health, led = null) {
      latestHealth = health;
      const el = $("status");
      const state = ledStateFromHealth(health, led);
      el.className = "status header-status " + state.className;
      el.lastElementChild.textContent = state.label;
      el.title = state.label;
      el.setAttribute("aria-label", state.label);
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

    function runtimeHoursText(runtime) {
      const hours = finiteNumber(runtime && (runtime.running_hours ?? runtime.minutes_or_flags));
      return hours === null ? "-" : `${Math.round(hours)} h`;
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
      const hasConfiguredValues = Object.keys(values).length > 0;
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
        const fanValue = value !== null ? value : fallback;
        if (value !== null && (fanValue < 0 || fanValue > 6)) return;
        if (value === null && hasConfiguredValues) return;
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
      const hasActiveSensorZone = activeSensorGroups.length > 0;
      const allActiveSensorZonesUseTempControl = hasActiveSensorZone && activeSensorGroups.every((zoneStatus) => zoneStatus.sensor_control === true);
      const activeSetpoint = averageNumbers(
        activeSensorGroups
          .filter((zoneStatus) => zoneStatus.sensor_control === true)
          .map((zoneStatus) => zoneStatus.setpoint)
      );
      const controlTemperature = finiteNumber(status.sensor_temp ?? status.temperature ?? status.current_temp);
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
      const fallbackTemperature = mappedSensorTemperature ?? anyTemperature;
      return {
        min,
        max,
        setpoint: hasActiveSensorZone ? activeSetpoint ?? statusSetpoint : null,
        current: controlTemperature ?? fallbackTemperature,
        showSetpoint: hasActiveSensorZone,
        canChangeSetpoint: hasActiveSensorZone && !allActiveSensorZonesUseTempControl,
        source: controlTemperature !== null ? "AC Control Temp" : mappedSensorTemperature !== null ? "Zone Control Temp Avg" : anyTemperature !== null ? "Zone Temp Avg" : "No Temp",
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
      const runtime = ac.runtime || {};
      const power = status.power_on === true ? "on" : status.power_on === false ? "off" : "-";
      const isOn = power === "on";
      const pending = pendingAcs.has(String(id));
      const mode = Number.isInteger(status.mode) ? status.mode : null;
      const fan = Number.isInteger(status.fan) ? status.fan : null;
      const thermostat = deriveAcThermostat(ac, zoneEntries);
      const setpoint = thermostat.setpoint === null ? null : Math.round(thermostat.setpoint);
      const current = thermostat.current === null ? null : thermostat.current;
      const rangeText = `${formatTemp(thermostat.min)}-${formatTemp(thermostat.max)} Range`;
      const currentText = current === null ? "-" : formatTemp(current, 1);
      const setpointText = setpoint === null ? "-" : formatTemp(setpoint);
      const setMarker = setpoint === null ? "" : `<span class="thermostat-marker thermostat-set" style="--angle:${thermostatAngle(setpoint, thermostat.min, thermostat.max)};--marker:var(--warm)" title="Set ${escapeHtml(formatTemp(setpoint))}"></span>`;
      const currentMarker = current === null ? "" : `<span class="thermostat-marker thermostat-current" style="--angle:${thermostatAngle(current, thermostat.min, thermostat.max)};--marker:var(--cool)" title="Current ${escapeHtml(currentText)}"></span>`;
      const thermostatReadout = thermostat.showSetpoint
        ? `
              <div class="thermostat-sub">Setpoint</div>
              <div class="thermostat-value">${escapeHtml(setpointText)}</div>
              <div class="thermostat-sub">${escapeHtml(thermostat.source)} ${escapeHtml(currentText)}</div>`
        : `
              <div class="thermostat-sub">${escapeHtml(thermostat.source)}</div>
              <div class="thermostat-value">${escapeHtml(currentText)}</div>`;
      const nextSetpointDown = setpoint === null ? "" : Math.max(thermostat.min, setpoint - 1);
      const nextSetpointUp = setpoint === null ? "" : Math.min(thermostat.max, setpoint + 1);
      const atMin = setpoint !== null && setpoint <= thermostat.min;
      const atMax = setpoint !== null && setpoint >= thermostat.max;
      const setpointControls = thermostat.showSetpoint && thermostat.canChangeSetpoint
        ? `<div class="thermostat-stepper">
            <button type="button" class="secondary" data-action="ac-status" data-ac="${escapeHtml(id)}" data-setpoint="${nextSetpointDown}" ${pending || setpoint === null || atMin ? "disabled" : ""}>-</button>
            <div class="thermostat-range">${escapeHtml(rangeText)}</div>
            <button type="button" class="secondary" data-action="ac-status" data-ac="${escapeHtml(id)}" data-setpoint="${nextSetpointUp}" ${pending || setpoint === null || atMax ? "disabled" : ""}>+</button>
          </div>`
        : "";
      const modes = configuredModeOptions(settings);
      const fans = configuredFanOptions(settings);
      return `
        <article class="ac-panel ${isOn ? "on" : "off"}">
          <div class="ac-top">
            <div>
              <div class="ac-name">${escapeHtml(base.name || `AC ${Number(id) + 1}`)}</div>
            </div>
            <div class="ac-stat-grid">
              <div class="ac-stat-pill"><span>Runtime</span><span>${escapeHtml(runtimeHoursText(runtime))}</span></div>
              <div class="ac-stat-pill"><span>Filter</span><span>-</span></div>
              <div class="ac-stat-pill"><span>Service</span><span>-</span></div>
              <div class="ac-stat-pill"><span>Demand</span><span>-</span></div>
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
              ${thermostatReadout}
            </div>
          </div>
          ${setpointControls}
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
          <span class="muted">${escapeHtml(titleText(power))} &middot; ${escapeHtml(modeName(status.mode))} &middot; ${escapeHtml(temp(status.setpoint))}</span>
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
      const setpointLimits = setpointLimitsForZone(latestState, id);
      const nextSetpointDown = setpoint === null ? "" : Math.max(setpointLimits.min, setpoint - 1);
      const nextSetpointUp = setpoint === null ? "" : Math.min(setpointLimits.max, setpoint + 1);
      const atMin = setpoint !== null && setpoint <= setpointLimits.min;
      const atMax = setpoint !== null && setpoint >= setpointLimits.max;
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
      if (isSpill) badges.push('<span class="pill warn">Spill</span>');
      if (sensorControl) badges.push('<span class="pill cool">Sensor</span>');
      if (status.low_battery) badges.push('<span class="pill warn">Battery</span>');
      if (status.timer_on) badges.push('<span class="pill">Program</span>');
      if (power === "turbo") badges.push('<span class="pill">Turbo</span>');
      if (grouping.thermostat_name) badges.push(`<span class="pill">${escapeHtml(grouping.thermostat_name)}</span>`);
      const slider = sensorControl
        ? ""
        : `<input class="zone-slider" type="range" min="0" max="100" step="5" value="${percentage === null ? 0 : percentage}" data-action="group-percentage" data-group="${escapeHtml(id)}" ${pending || percentage === null || !isOn ? "disabled" : ""}>`;
      const valueButtons = sensorControl
        ? `
          <button type="button" class="secondary" data-action="group-setpoint" data-group="${escapeHtml(id)}" data-setpoint="${nextSetpointDown}" ${pending || setpoint === null || !isOn || atMin ? "disabled" : ""}>Set -</button>
          <button type="button" class="secondary" data-action="group-setpoint" data-group="${escapeHtml(id)}" data-setpoint="${nextSetpointUp}" ${pending || setpoint === null || !isOn || atMax ? "disabled" : ""}>Set +</button>`
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
              <div class="label">Zone Temp</div>
              <div class="big">${escapeHtml(roomTemp)}</div>
            </div>
            <div class="reading">
              <div class="label">${escapeHtml(sensorControl ? "Set" : "Vent")}</div>
              <div class="small-value">${escapeHtml(valueLabel)}</div>
              <div class="muted">${escapeHtml(status.has_sensor ? "Mapped Sensor" : "No Sensor")}</div>
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
      const groupEntries = Object.entries(groups || {}).sort(([a], [b]) => Number(a) - Number(b));
      $("favourites").innerHTML = entries.map(([id, favourite]) => {
        const groupNames = groupNamesFromBitmap(groups, favourite.groups_1_8_bitmap || 0, favourite.groups_9_16_bitmap || 0);
        const pending = pendingFavourites.has(String(id));
        const groupChecks = groupEntries.map(([groupId, group]) => {
          const index = Number(groupId);
          const selected = index < 8
            ? !!((favourite.groups_1_8_bitmap || 0) & (1 << index))
            : !!((favourite.groups_9_16_bitmap || 0) & (1 << (index - 8)));
          const name = group.name || `Zone ${index + 1}`;
          return `<label class="check-row"><input type="checkbox" data-favourite-group="${index}" ${selected ? "checked" : ""}><span>${escapeHtml(name)}</span></label>`;
        }).join("");
        return `
          <article class="card" data-favourite-card="${escapeHtml(id)}">
            <div class="card-title">Favourite ${escapeHtml(Number(id) + 1)}: ${escapeHtml(favourite.name || "Empty")}</div>
            <div><span class="${groupNames.length ? "pill on" : "pill"}">${escapeHtml(groupNames.length ? `${groupNames.length} Zones` : "No Zones")}</span></div>
            <div class="muted">${escapeHtml(groupNames.length ? groupNames.join(", ") : "No Zones Selected")}</div>
            <div class="service-card-body">
              <div class="field-grid">
                ${textField("favourite-name", "Name", favourite.name || "", 8)}
              </div>
              <div class="chip-grid">${groupChecks}</div>
              <div class="service-actions">
                <button type="button" data-action="active-favourite" data-favourite="${escapeHtml(id)}" ${pending ? "disabled" : ""}>${escapeHtml(pending ? "Sending" : "Run")}</button>
                <button type="button" class="secondary" data-action="favourite-save" data-favourite="${escapeHtml(id)}">Save</button>
                <button type="button" class="secondary" data-action="favourite-clear" data-favourite="${escapeHtml(id)}">Clear Favourite</button>
              </div>
            </div>
          </article>`;
      }).join("") || '<div class="muted">No Favourite Data</div>';
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

    function applyAcSettingsCard(record, card) {
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
      return record;
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
      const value = card.querySelector(`[data-field="${prefix}-time"]`).value || "00:00";
      const [hour, minute] = value.split(":").map((item) => Number(item));
      return {
        enabled: card.querySelector(`[data-field="${prefix}-enabled"]`).value === "true",
        hour: Number.isFinite(hour) ? hour : 0,
        minute: Number.isFinite(minute) ? minute : 0
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
      document.querySelectorAll("[data-balance-number]").forEach((input) => {
        const zone = Number(input.dataset.balanceNumber);
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

    function checkedValues(card, selector) {
      return Array.from(card.querySelectorAll(selector))
        .filter((input) => input.checked)
        .map((input) => Number(input.value));
    }

    function bitmapFromValues(values) {
      return values.reduce((mask, value) => mask | (1 << Number(value)), 0);
    }

    function groupBitmapFromValues(values) {
      const low = [];
      const high = [];
      values.forEach((group) => {
        if (group < 8) {
          low.push(group);
        } else {
          high.push(group - 8);
        }
      });
      return {
        groups_1_8_bitmap: bitmapFromValues(low),
        groups_9_16_bitmap: bitmapFromValues(high)
      };
    }

    function programZoneChecks(groups, program) {
      return Object.entries(groups || {}).sort(([a], [b]) => Number(a) - Number(b)).map(([groupId, group]) => {
        const index = Number(groupId);
        const selected = index < 8
          ? !!((program.groups_1_8_bitmap || 0) & (1 << index))
          : !!((program.groups_9_16_bitmap || 0) & (1 << (index - 8)));
        const name = group.name || `Zone ${index + 1}`;
        return `<label class="check-row compact"><input type="checkbox" data-program-zone value="${index}" ${selected ? "checked" : ""}><span>${escapeHtml(name)}</span></label>`;
      }).join("");
    }

    function programAcChecks(program) {
      return visibleAcs(latestState).map(([id, ac]) => {
        const index = Number(id);
        const selected = !!((program.active_ac_bitmap || 0) & (1 << index));
        const name = (ac.base || {}).name || `AC ${index + 1}`;
        return `<label class="check-row compact"><input type="checkbox" data-program-ac value="${index}" ${selected ? "checked" : ""}><span>${escapeHtml(name)}</span></label>`;
      }).join("");
    }

    function dayChips(program) {
      const days = [["Mon", 1], ["Tue", 2], ["Wed", 3], ["Thu", 4], ["Fri", 5], ["Sat", 6], ["Sun", 0]];
      const bitmap = Number(program.days_bitmap || 0);
      return days.map(([label, bit]) => `<label class="day-chip"><input type="checkbox" data-program-day value="${bit}" ${bitmap & (1 << bit) ? "checked" : ""}><span>${label}</span></label>`).join("");
    }

    function clearedProgramRecord(program) {
      return {
        program,
        enabled: false,
        days_bitmap: 0,
        name: "",
        groups_1_8_bitmap: 0,
        groups_9_16_bitmap: 0,
        active_ac_bitmap: 0,
        on_timer: {enabled: false, hour: 0, minute: 0},
        on_setpoint: 26,
        off_timer: {enabled: false, hour: 0, minute: 0}
      };
    }

    function renderPrograms(programs, groups) {
      const entries = Object.entries(programs || {}).sort(([a], [b]) => Number(a) - Number(b));
      $("programs").innerHTML = entries.map(([_id, program]) => {
        const groupNames = groupNamesFromBitmap(groups, program.groups_1_8_bitmap || 0, program.groups_9_16_bitmap || 0);
        const onTimer = program.on_timer || {};
        const offTimer = program.off_timer || {};
        const acNames = visibleAcs(latestState)
          .filter(([id]) => !!((program.active_ac_bitmap || 0) & (1 << Number(id))))
          .map(([id, ac]) => (ac.base || {}).name || `AC ${Number(id) + 1}`);
        return `
          <article class="card" data-program="${escapeHtml(program.program ?? _id)}">
            <div class="card-title">Program ${escapeHtml(Number(program.program ?? _id) + 1)}: ${escapeHtml(program.name || "Empty")}</div>
            <div><span class="${program.enabled ? "pill on" : "pill"}">${escapeHtml(program.enabled ? "Enabled" : "Off")}</span></div>
            <div class="muted">${escapeHtml(groupNames.length ? groupNames.join(", ") : "No Zones Selected")}</div>
            <div class="muted">${escapeHtml(acNames.length ? acNames.join(", ") : "No AC Selected")}</div>
            <div class="muted">On ${escapeHtml(timeText(onTimer))} / Off ${escapeHtml(timeText(offTimer))}</div>
            <div class="service-card-body">
              <div class="field-grid">
                <div class="field"><label>Name</label><input data-field="program-name" maxlength="8" value="${escapeHtml(program.name || "")}"></div>
                <div class="field"><label>Enabled</label><select data-field="program-enabled"><option value="true" ${program.enabled ? "selected" : ""}>On</option><option value="false" ${!program.enabled ? "selected" : ""}>Off</option></select></div>
                ${timerFields("On", onTimer)}
                <div class="field"><label>Setpoint</label><input data-field="program-on-setpoint" type="number" min="16" max="30" value="${escapeHtml(program.on_setpoint ?? 26)}"></div>
                ${timerFields("Off", offTimer)}
              </div>
              <div class="field">
                <label>Days</label>
                <div class="chip-grid">${dayChips(program)}</div>
              </div>
              <div class="field">
                <label>Zones</label>
                <div class="chip-grid">${programZoneChecks(groups, program)}</div>
              </div>
              <div class="field">
                <label>AC</label>
                <div class="chip-grid">${programAcChecks(program)}</div>
              </div>
              <div class="service-actions">
                <button type="button" data-program-action="program-save" data-program="${escapeHtml(program.program ?? _id)}">Save Program</button>
                <button type="button" class="secondary" data-program-action="program-clear" data-program="${escapeHtml(program.program ?? _id)}">Clear Program</button>
              </div>
            </div>
          </article>`;
      }).join("") || '<div class="muted">No Program Data</div>';
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
        const hasTimer = !!(onTimer.enabled || offTimer.enabled);
        return `
          <article class="card ac-timer-card" data-ac-timer="${escapeHtml(id)}">
            <div class="card-title">${escapeHtml(base.name || `AC ${Number(id) + 1}`)}</div>
            <div><span class="${hasTimer ? "pill on" : "pill"}">${escapeHtml(hasTimer ? "Timer Set" : "No Timer")}</span></div>
            <div class="muted">${escapeHtml(status.power_on ? "On" : "Off")} / ${escapeHtml(modeName(status.mode))} / ${escapeHtml(fanName(status.fan))} / ${escapeHtml(temp(status.setpoint))}</div>
            <div class="muted">On ${escapeHtml(timeText(onTimer))} / Off ${escapeHtml(timeText(offTimer))}</div>
            <div class="service-card-body">
              <h3>Timer</h3>
              <div class="timer-stack">${timerFields("On", onTimer)}${timerFields("Off", offTimer)}</div>
              <div class="service-actions"><button type="button" data-program-action="ac-timer-save" data-ac="${escapeHtml(id)}">Save Timer</button></div>
            </div>
          </article>`;
      }).join("") || '<div class="muted">No AC Timer Data</div>';
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
      const groups = configuredGroups(state);
      const groupEntries = configuredGroupEntries(state);
      const acs = visibleAcs(state);
      const system = state.system || {};
      const sensorRows = sensorRowsFromState(state);
      const sensorById = new Map(sensorRows.filter((row) => Number.isFinite(Number(row.id))).map((row) => [Number(row.id), row]));
      const balanceByZone = new Map(((((state.system || {}).balance || {}).zones || [])
        .filter((zone) => groups[zone.zone]))
        .map((zone) => [Number(zone.zone), zone]));
      $("grouping").innerHTML = groupEntries
        .map(([id, group]) => {
          const grouping = group.grouping || {};
          const status = group.status || {};
          const groupName = group.name || `Zone ${Number(id) + 1}`;
          const zoneStart = grouping.zone_start ?? grouping.zone_1 ?? Number(id);
          const zoneCount = grouping.zone_count ?? 1;
          const minPercent = grouping.min_percent ?? status.min_percentage ?? 0;
          const thermostat = grouping.thermostat ?? status.sensor ?? 255;
          const thermostatRow = sensorById.get(Number(thermostat));
          const sensorLabel = thermostatRow ? sensorDisplayName(thermostatRow) : sensorName(thermostat);
          const sensorHealth = thermostatRow
            ? `${sensorKindLabel(thermostatRow.kind)} / ${titleText(thermostatRow.status || "unknown")} / ${temp(thermostatRow.temperature)}`
            : (Number(thermostat) === 255 ? "No Sensor" : "Configured, Not Reporting");
          const sensorMapped = thermostatRow && thermostatRow.mapped_groups && thermostatRow.mapped_groups.length
            ? ` / Mapped ${thermostatRow.mapped_groups.join(", ")}`
            : "";
          return `
            <article class="card" data-service-group="${escapeHtml(id)}">
              <div class="card-title">${escapeHtml(groupName)}</div>
              <div class="muted">Mapped Dampers ${escapeHtml(zoneStart)}-${escapeHtml(Number(zoneStart) + Number(zoneCount) - 1)} / Sensor ${escapeHtml(sensorLabel)}</div>
              <div class="muted">${escapeHtml(sensorHealth + sensorMapped)}</div>
              <div class="service-card-body">
                <div class="field-grid">
                  <div class="field"><label>Name</label><input data-field="group-name" maxlength="8" value="${escapeHtml(groupName)}"></div>
                  <div class="field"><label>Start</label><input data-field="zone-start" type="number" min="0" max="63" value="${escapeHtml(zoneStart)}"></div>
                  <div class="field"><label>Count</label><input data-field="zone-count" type="number" min="1" max="4" value="${escapeHtml(zoneCount)}"></div>
                  <div class="field"><label>Min %</label><input data-field="min-percent" type="number" min="0" max="100" value="${escapeHtml(minPercent)}"></div>
                  ${selectField("thermostat", "Sensor", thermostat, sensorOptions(state, thermostat))}
                </div>
                <div class="service-actions">
                  <button type="button" data-service-action="group-name" data-group="${escapeHtml(id)}">Save Name</button>
                  <button type="button" class="secondary" data-service-action="grouping" data-group="${escapeHtml(id)}">Save Grouping</button>
                </div>
              </div>
            </article>`;
        }).join("") || '<div class="muted">No Grouping Data</div>';
      const spillZoneChecks = Object.entries(groups)
        .sort(([a], [b]) => Number(a) - Number(b))
        .map(([id, group]) => {
          const status = group.status || {};
          const configured = group.spill_configured || status.spill_on;
          const damper = pct(status.percentage);
          const spillState = status.spill_on ? "Open" : "Reported";
          return `<label class="check-row compact">
            <input type="checkbox" data-spill-group="${escapeHtml(id)}" ${configured ? "checked" : ""}>
            <span>${escapeHtml(group.name || `Zone ${Number(id) + 1}`)}</span>
            <span class="${status.spill_on ? "pill warn" : "pill"}" data-spill-open="${escapeHtml(id)}">${escapeHtml(damper === null ? "-" : `${spillState} ${damper}%`)}</span>
          </label>`;
        }).join("");
      $("spill").innerHTML = `
        <article class="card">
          <div class="card-title">Spill Zones</div>
          <div class="chip-grid">${spillZoneChecks || '<span class="muted">No Spill Data</span>'}</div>
        </article>
        <article class="card">
          <div class="card-title">Display</div>
          <div class="chip-grid">
            ${acs.map(([id, ac]) => {
              const acIndex = Number(id);
              const hideSpill = !!((ac.settings || {}).hide_spill_group);
              const name = (ac.base || {}).name || `AC ${acIndex + 1}`;
              return `<label class="check-row compact">
                <input type="checkbox" data-spill-hide-ac="${acIndex}" ${hideSpill ? "checked" : ""}>
                <span>${escapeHtml(name)} Hide Spill</span>
              </label>`;
            }).join("")}
          </div>
          <details class="advanced-panel">
            <summary>AC Spill Mode</summary>
            <div class="field-grid">
              ${acs.map(([id, ac]) => {
                const acIndex = Number(id);
                const configured = (((system.spill || {}).ac_spill_types || [])[acIndex] || {}).value ?? 0;
                const name = (ac.base || {}).name || `AC ${acIndex + 1}`;
                return `<div class="field"><label>${escapeHtml(name)}</label><select data-spill-ac="${acIndex}">
                  ${[[0, "None"], [1, "Spill"], [2, "Bypass"]].map(([value, label]) => `<option value="${value}" ${configured === value ? "selected" : ""}>${label}</option>`).join("")}
                </select></div>`;
              }).join("")}
            </div>
          </details>
          <div class="service-actions"><button type="button" data-service-action="spill">Save Spill</button></div>
        </article>`;
      $("balance").innerHTML = groupEntries
        .map(([id, group]) => {
          const zoneId = Number(id);
          const balance = balanceByZone.get(zoneId) || {};
          const status = group.status || {};
          const hasBalance = balance.set_value !== undefined || balance.current_value !== undefined;
          const maxOpening = Number(balance.set_value ?? 0);
          const currentOpening = balance.current_value ?? status.percentage ?? "-";
          return `<article class="card balance-row" data-balance-zone="${escapeHtml(zoneId)}">
            <div class="balance-row-main">
              <div class="card-title">${escapeHtml(group.name || `Zone ${zoneId + 1}`)}</div>
              <div class="muted">Zone ${escapeHtml(zoneId + 1)} / ${escapeHtml(status.power_name || "-")}</div>
            </div>
            <div class="balance-row-value">
              <div class="label">Current Opening</div>
              <div class="small-value">${escapeHtml(currentOpening === "-" ? "-" : `${currentOpening}`)}</div>
            </div>
            <div class="balance-row-control">
              <input data-balance-value="${escapeHtml(zoneId)}" type="range" min="0" max="255" value="${escapeHtml(maxOpening)}">
              <input data-balance-number="${escapeHtml(zoneId)}" type="number" min="0" max="255" value="${escapeHtml(maxOpening)}" aria-label="Max Opening">
              <div class="muted">${escapeHtml(hasBalance ? "Max Opening" : "Max Opening Pending")}</div>
            </div>
            <div class="balance-actions">
              <span class="pill" data-balance-status="${escapeHtml(zoneId)}">Auto</span>
            </div>
          </article>`;
        }).join("") || '<div class="muted">No Zones</div>';
      $("balance").innerHTML += `<article class="card"><div class="card-title">Balance Mode</div><div class="muted">Start balance before setting individual zones, then stop when airflow balancing is complete.</div><div class="service-actions"><button type="button" data-service-action="balance-start">Start Balance</button><button type="button" class="secondary" data-service-action="balance-stop">Stop Balance</button></div></article>`;
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
            <div class="muted">Groups ${escapeHtml(text(base.group_start))}-${escapeHtml(Number.isInteger(base.group_start) && Number.isInteger(base.group_count) ? base.group_start + base.group_count - 1 : "-")} / Brand ${escapeHtml(text(base.brand))} / Hide Spill ${escapeHtml(settings.hide_spill_group ? "Yes" : "No")}</div>
            <div class="service-card-body">
              <h3>Base</h3>
              <div class="field-grid">
                <div class="field"><label>Name</label><input data-field="ac-name" maxlength="8" value="${escapeHtml(base.name || "")}"></div>
                <div class="field"><label>First Zone</label><input data-field="ac-group-start" type="number" min="0" max="63" value="${escapeHtml(base.group_start ?? 0)}"></div>
                <div class="field"><label>Zone Count</label><input data-field="ac-group-count" type="number" min="0" max="63" value="${escapeHtml(base.group_count ?? 0)}"></div>
              </div>
              <details class="advanced-panel">
                <summary>Advanced Base</summary>
                <div class="field-grid">
                  <div class="field"><label>Brand</label><input data-field="ac-brand" type="number" min="0" max="65535" value="${escapeHtml(base.brand ?? 0)}"></div>
                </div>
              </details>
              <h3>Control</h3>
              <div class="field-grid">
                <div class="field"><label>Hide Spill</label><select data-field="hide-spill"><option value="true" ${settings.hide_spill_group ? "selected" : ""}>Yes</option><option value="false" ${!settings.hide_spill_group ? "selected" : ""}>No</option></select></div>
                <div class="field"><label>Cool Adjust</label><input data-field="cool-adjust" type="number" min="-8" max="7" value="${escapeHtml(settings.cool_adjust ?? 0)}"></div>
                <div class="field"><label>Heat Adjust</label><input data-field="heat-adjust" type="number" min="-8" max="7" value="${escapeHtml(settings.heat_adjust ?? 0)}"></div>
                <div class="field"><label>Min Set</label><input data-field="min-setpoint" type="number" min="0" max="255" value="${escapeHtml(settings.min_setpoint ?? 16)}"></div>
                <div class="field"><label>Max Set</label><input data-field="max-setpoint" type="number" min="0" max="255" value="${escapeHtml(settings.max_setpoint ?? 30)}"></div>
                <div class="field"><label>Auto Off</label><select data-field="auto-off"><option value="true" ${settings.auto_off ? "selected" : ""}>On</option><option value="false" ${!settings.auto_off ? "selected" : ""}>Off</option></select></div>
                <div class="field"><label>Time Limit</label><input data-field="on-time-limit" type="number" min="0" max="15" value="${escapeHtml(settings.on_time_limit ?? 0)}"></div>
              </div>
              <details class="advanced-panel">
                <summary>Advanced Control</summary>
                <div class="field-grid">
                  <div class="field"><label>Thermostat Byte</label><input data-field="ctrl-thermostat" type="number" min="0" max="255" value="${escapeHtml(settings.ctrl_thermostat ?? 0)}"></div>
                </div>
              </details>
              <h3>Modes</h3>
              <div class="field-grid">${["auto", "cool", "heat", "dry", "fan"].map((mode) => boolSelect(`mode-${mode}`, `Mode ${titleText(mode)}`, !!modes[mode])).join("")}</div>
              <details class="advanced-panel">
                <summary>Fan Value Mapping</summary>
                <div class="field-grid">${["auto", "quiet", "low", "medium", "high", "powerful", "turbo"].map((fan) => numberField(`fan-${fan}`, `Fan ${titleText(fan)}`, fans[fan] ?? 0, 0, 15)).join("")}</div>
              </details>
              <h3>Selector Visibility</h3>
              <div class="field-grid">
                ${["auto", "touchpad_1", "touchpad_2", "average", "economy"].map((selector) => boolSelect(`selector-${selector}`, `Show ${titleText(selector)}`, !!selectors[selector])).join("")}
              </div>
              <details class="advanced-panel">
                <summary>Selector Zone Masks</summary>
                <div class="field-grid">
                  ${numberField("selector-groups-1", "Selector Zones 1-8", selectors.groups_1_8_bitmap ?? 0, 0, 255)}
                  ${numberField("selector-groups-2", "Selector Zones 9-16", selectors.groups_9_16_bitmap ?? 0, 0, 255)}
                </div>
              </details>
              <h3>Turbo</h3>
              <div class="field-grid">${numberField("turbo-group", "Turbo Zone", turboRecord.group ?? 255, 0, 255)}</div>
              <div class="service-actions">
                <button type="button" data-service-action="ac-base-info" data-ac="${escapeHtml(id)}">Save AC Base</button>
                <button type="button" class="secondary" data-service-action="ac-setting-new" data-ac="${escapeHtml(id)}">Save AC Settings</button>
                <button type="button" class="secondary" data-service-action="reset-temp-offsets" data-ac="${escapeHtml(id)}">Reset Offsets</button>
                <button type="button" class="secondary" data-service-action="turbo-group" data-ac="${escapeHtml(id)}">Save Turbo Zone</button>
              </div>
            </div>
          </article>`;
      }).join("") || '<div class="muted">No AC Setup Data</div>';
      if (document.activeElement !== $("system-name-input")) $("system-name-input").value = system.system_name || "";
      const service = state.service || {};
      if (document.activeElement !== $("service-company-input")) $("service-company-input").value = service.company || service.company_name || "";
      if (document.activeElement !== $("service-phone-input")) $("service-phone-input").value = service.phone || service.phone_number || "";
      $("parameters").innerHTML = `
        <article class="card">
          <div class="card-title">Preference</div>
          <div class="field-grid">
            ${boolSelect("show-ac-errors", "Show AC Errors", !!system.show_ac_errors)}
            ${boolSelect("pref-show-outside-temp", "Show Outside Temp", !!system.show_outside_temp)}
            ${boolSelect("pref-show-control-sensor", "Show Control Sensor", !!system.show_control_sensor)}
            ${boolSelect("use-fahrenheit", "Fahrenheit", !!system.use_fahrenheit)}
            ${numberField("location", "Location", system.location ?? system.address_or_location ?? 0, 0, 127)}
            ${boolSelect("screensaver-enabled", "Screensaver", !!system.screensaver_enabled)}
            ${numberField("screensaver-timeout", "Screen Timeout", system.screensaver_timeout ?? 0, 0, 127)}
          </div>
          <div class="service-actions"><button type="button" data-service-action="preference">Save Preference</button></div>
        </article>
        <article class="card">
          <div class="card-title">Parameters</div>
          <div class="field-grid">
            ${numberField("group-count", "Groups", system.group_count ?? (groupEntries.length || 1), 1, 16)}
            ${boolSelect("ac-button-blocked", "Block AC Button", !!system.ac_button_blocked)}
            ${boolSelect("param-show-outside-temp", "Outside Temp", !!system.show_outside_temp)}
            ${boolSelect("lock-to-temp-control", "Lock Temp Control", !!system.lock_to_temp_control)}
            ${boolSelect("param-show-control-sensor", "Control Sensor", !!system.show_control_sensor)}
          </div>
          <details class="advanced-panel">
            <summary>Advanced Parameters</summary>
            <div class="field-grid">
              ${numberField("damper-rpm", "Damper RPM", system.damper_rpm ?? 100, 0, 255)}
              ${numberField("touchpad-1-location", "Touchpad 1 Location", system.touchpad_1_location ?? 255, 0, 255)}
              ${numberField("touchpad-2-location", "Touchpad 2 Location", system.touchpad_2_location ?? 255, 0, 255)}
            </div>
          </details>
          <div class="service-actions"><button type="button" data-service-action="parameters">Save Parameters</button></div>
        </article>
        ${metric("Device ID", system.device_id || "-")}
        ${metric("Firmware", system.firmware_version_raw || "-")}
        ${metric("Sensors", (system.sensor_addresses || []).join(", ") || "-")}`;
      $("system").innerHTML = `
        <article class="card">
          <div class="card-title">Service Reminder</div>
          <div class="field-grid">
            ${boolSelect("show-service-due", "Show Service Due", !!service.show_service_due)}
            ${boolSelect("service-due-locked", "Lock Service Due", !!service.service_due_locked)}
            ${boolSelect("filter-clean-due", "Filter Clean Due", !!service.filter_clean_due)}
            ${boolSelect("maintenance-due", "Maintenance Due", !!service.maintenance_due)}
            ${numberField("service-months", "Months", service.months ?? 0, 0, 255)}
            ${numberField("service-days", "Days", service.days ?? 0, 0, 65535)}
            ${numberField("service-runtime-hours", "Runtime Hours", service.runtime_hours ?? 0, 0, 4294967295)}
          </div>
          <div class="service-actions"><button type="button" data-service-action="service-contact">Save Service</button></div>
        </article>`;
      $("system-debug").innerHTML = [
        metric("Password Pages", Object.keys(state.password || {}).length),
        metric("Last LED", (state.last_led || {}).led_code ?? "-"),
        metric("Supply Air", supplyAirText(system.supply_air || []) || "-"),
        metric("Touchpads", (((system.sensor_list || {}).touchpad_addresses) || []).map((item) => `0x${Number(item).toString(16).toUpperCase()}`).join(", ") || "-"),
        metric("Runtime", (system.expanded || {}).software_version || "-")
      ].join("");
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
      $("app-title").textContent = "OpenAirtouch";
      renderAlerts(collectAlerts(controller, state, integrations, transactions));
      renderWeather(integrations);
      renderIndoor(integrations, state);
      renderAdaptive(integrations.adaptive || {}, config.adaptive || {});
      setStatus(latestHealth, state.last_led || null);
      const acEntries = visibleAcs(state);
      if (!acEntries.some(([id]) => Number(id) === selectedAc)) selectedAc = Number(acEntries[0] && acEntries[0][0]) || 0;
      const allZoneEntries = zoneEntriesForAc(state, selectedAc);
      const activeZoneCount = allZoneEntries.filter(([_id, group]) => {
        const status = group.status || {};
        return status.power_name === "on" || status.power_name === "turbo";
      }).length;

      $("metrics").innerHTML = [
        metric("Protocol", formatProtocol(runtime)),
        metric("Service", titleText(controller.status, "-")),
        metric("Transport", titleText(config.transport)),
        metric("Endpoint", config.transport === "tcp_serial" ? `${config.tcp_host}:${config.tcp_port}` : config.port),
        metric("Address", runtime.src),
        metric("Boot", runtime.boot_complete ? "Complete" : "Pending"),
        metric("RX / TX", `${runtime.rx_count || 0} / ${runtime.tx_count || 0}`),
        metric("Transactions", `${(transactions.completed || []).length} OK, ${(transactions.failed || []).length} Fail`)
      ].join("");

      $("ac-selector").innerHTML = acEntries.length > 1
        ? acEntries.map(([id, ac]) => acSelectorCard(id, ac)).join("")
        : "";

      const selectedAcRecord = (state.acs || {})[selectedAc] || {};
      $("ac-count").textContent = `${acEntries.length} ${acEntries.length === 1 ? "AC" : "ACs"}`;
      $("acs").innerHTML = acEntries.length
        ? acCard(String(selectedAc), selectedAcRecord, allZoneEntries)
        : '<div class="muted">No AC Data</div>';

      const groups = configuredGroups(state);
      const zoneEntries = allZoneEntries;
      const pageCount = Math.max(1, Math.ceil(zoneEntries.length / 8));
      if (zonePage >= pageCount) zonePage = pageCount - 1;
      const pageStart = zonePage * 8;
      const pageEntries = zoneEntries.slice(pageStart, pageStart + 8);
      $("zone-count").textContent = `${activeZoneCount}/${zoneEntries.length} Zones`;
      $("zone-pages").innerHTML = pageCount > 1
        ? Array.from({length: pageCount}, (_value, index) => `<button type="button" class="option ${index === zonePage ? "active" : ""}" data-action="zone-page" data-page="${index}">${(index * 8) + 1}-${Math.min((index + 1) * 8, zoneEntries.length)}</button>`).join("")
        : "";
      $("groups").innerHTML = pageEntries
        .map(([id, group]) => groupTile(id, group))
        .join("") || '<div class="muted">No Zone Data</div>';

      renderFavourites(state.favourites || {}, groups);
      renderPrograms(state.programs || {}, groups);
      renderProgramSupport(state);
      renderServicePages(state);

      const sensorRows = sensorRowsFromState(state);
      $("sensors").innerHTML = sensorRows
        .sort((a, b) => String(a.address || a.id).localeCompare(String(b.address || b.id), undefined, {numeric: true}))
        .map((sensor) => {
          const mapped = (sensor.mapped_groups || []).length ? sensor.mapped_groups.join(", ") : "-";
          const currentTemp = finiteNumber(sensor.temperature);
          const canCalibrate = sensor.kind !== "supply_air" && currentTemp !== null && sensor.present !== false;
          const calibration = canCalibrate
            ? `<div class="sensor-calibration">
                <input type="range" min="-10" max="40" step="1" value="${escapeHtml(Math.round(currentTemp))}" data-sensor-temperature="${escapeHtml(sensor.id)}">
                <span class="pill" data-sensor-temperature-value="${escapeHtml(sensor.id)}">${escapeHtml(formatTemp(Math.round(currentTemp)))}</span>
              </div>`
            : '<div class="muted">Calibration Unavailable</div>';
          const diagnostics = [
            sensor.signal !== undefined && sensor.signal !== null ? `Signal ${sensor.signal}` : "",
            sensor.battery !== undefined && sensor.battery !== null ? `Battery ${sensor.battery}${sensor.low_battery ? " Low" : ""}` : "",
            sensor.mac ? `MAC ${sensor.mac}` : "",
          ].filter(Boolean).join(" / ") || "-";
          return `<article class="card sensor-row" data-sensor-row="${escapeHtml(sensor.id)}">
            <div class="sensor-row-main">
              <div class="card-title">${escapeHtml(sensorDisplayName(sensor))}</div>
              <div class="muted">${escapeHtml(sensor.address || sensor.id || "-")} / ${escapeHtml(sensorKindLabel(sensor.kind))}</div>
            </div>
            <div class="sensor-row-temp">
              <div class="label">${escapeHtml(sensor.kind === "supply_air" ? "Supply Air Temp" : sensor.kind === "touchpad" ? "Touchpad Temp" : "Sensor Temp")}</div>
              <div class="small-value">${escapeHtml(temp(sensor.temperature))}</div>
            </div>
            <div class="sensor-row-meta">
              ${sensorStatusPill(sensor)}
              ${sensor.low_battery ? '<span class="pill warn">Battery</span>' : ""}
            </div>
            <div>
              ${calibration}
              <div class="muted">${escapeHtml(`Mapped ${mapped}`)}<br>${escapeHtml(diagnostics)}</div>
            </div>
          </article>`;
        }).join("") || '<article class="card"><div class="card-title">No Sensor Data</div><div class="muted">Pairing or sensor list data has not been received yet.</div></article>';
    }

    function renderEvents(payload) {
      const events = (payload.events || []).slice(-10).reverse();
      $("events").innerHTML = events.map((event) => row([
        titleText(event.event),
        event.cmd_name || event.cmd,
        event.message || (event.transaction && event.transaction.name) || ""
      ])).join("") || row(["-", "-", "No Events Yet"]);
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

    function scheduleBalanceCommit(zone) {
      if (balanceCommitTimer) clearTimeout(balanceCommitTimer);
      const status = document.querySelector(`[data-balance-status="${zone}"]`);
      if (status) status.textContent = "Pending";
      balanceCommitTimer = setTimeout(async () => {
        try {
          const value = Number(document.querySelector(`[data-balance-number="${zone}"]`).value);
          await sendCommand("balance_start", {
            current_values: balanceValuesFromPage(),
            zone,
            value,
          });
          const latest = document.querySelector(`[data-balance-status="${zone}"]`);
          if (latest) latest.textContent = "Sent";
          setTimeout(refresh, 300);
        } catch (err) {
          setStatus({ok: false, error: err.message});
          const latest = document.querySelector(`[data-balance-status="${zone}"]`);
          if (latest) latest.textContent = "Error";
        }
      }, 450);
    }

    async function sendAdaptiveConfig(data) {
      const response = await fetch(apiPath("adaptive"), {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || `Adaptive update failed: ${response.status}`);
      }
      return response.json();
    }

    async function sendAdaptiveModelAction(data) {
      const response = await fetch(apiPath("adaptive/model"), {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || `Adaptive model update failed: ${response.status}`);
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

    $("theme-selector").addEventListener("click", (event) => {
      const button = event.target.closest("button[data-theme-choice]");
      if (!button) return;
      selectedTheme = button.dataset.themeChoice;
      localStorage.setItem(THEME_KEY, selectedTheme);
      applyTheme();
    });

    $("view-adaptive").addEventListener("click", async (event) => {
      const modelButton = event.target.closest("button[data-adaptive-model-action]");
      if (modelButton) {
        const action = modelButton.dataset.adaptiveModelAction;
        modelButton.disabled = true;
        const previous = modelButton.textContent;
        modelButton.textContent = "Working";
        try {
          await sendAdaptiveModelAction({
            action,
            zone: modelButton.dataset.zone === undefined ? undefined : Number(modelButton.dataset.zone),
            enabled: modelButton.dataset.enabled === undefined ? undefined : modelButton.dataset.enabled === "true",
          });
          setTimeout(refresh, 300);
        } catch (err) {
          alert(err.message || err);
        } finally {
          modelButton.disabled = false;
          modelButton.textContent = previous;
        }
        return;
      }
      const button = event.target.closest("button[data-adaptive-save]");
      if (!button) return;
      button.disabled = true;
      const previous = button.textContent;
      button.textContent = "Saving";
      try {
        await sendAdaptiveConfig({
          mode: $("adaptive-mode").value,
          cool_diff: Number($("adaptive-cool-diff").value),
          cool_comfort_temp: Number($("adaptive-cool-comfort-temp").value),
          heat_diff: Number($("adaptive-heat-diff").value),
          heat_comfort_temp: Number($("adaptive-heat-comfort-temp").value),
          check_interval: Number($("adaptive-check-interval").value),
          command_cooldown: Number($("adaptive-command-cooldown").value),
          learning_mode: $("adaptive-mpc-control").value,
          control_zones: Array.from(document.querySelectorAll("[data-adaptive-control-zone]"))
            .filter((input) => input.checked)
            .map((input) => Number(input.dataset.adaptiveControlZone)),
          mpc_horizon_hours: Number($("adaptive-mpc-horizon-hours").value),
          compressor_min_run_time: Number($("adaptive-compressor-min-run-time").value),
          compressor_min_off_time: Number($("adaptive-compressor-min-off-time").value),
        });
        setTimeout(refresh, 300);
      } catch (err) {
        setStatus({ok: false, error: err.message});
      } finally {
        setTimeout(() => {
          button.disabled = false;
          button.textContent = previous;
          refresh(true);
        }, 900);
      }
    });

    if (window.matchMedia) {
      window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", applyTheme);
    }

    document.addEventListener("focusin", (event) => {
      if (event.target && event.target.matches && event.target.matches("input, select, textarea")) markEditing();
    });
    document.addEventListener("input", (event) => {
      if (event.target && event.target.matches && event.target.matches("input, select, textarea")) markEditing();
    });
    document.addEventListener("change", (event) => {
      if (event.target && event.target.matches && event.target.matches("input, select, textarea")) markEditing();
    });

    $("view-settings").addEventListener("input", (event) => {
      const range = event.target.closest("input[data-balance-value]");
      const number = event.target.closest("input[data-balance-number]");
      const sensorTemp = event.target.closest("input[data-sensor-temperature]");
      if (range) {
        const peer = document.querySelector(`[data-balance-number="${range.dataset.balanceValue}"]`);
        if (peer) peer.value = range.value;
        scheduleBalanceCommit(Number(range.dataset.balanceValue));
      } else if (number) {
        const peer = document.querySelector(`[data-balance-value="${number.dataset.balanceNumber}"]`);
        if (peer) peer.value = number.value;
        scheduleBalanceCommit(Number(number.dataset.balanceNumber));
      } else if (sensorTemp) {
        const value = document.querySelector(`[data-sensor-temperature-value="${sensorTemp.dataset.sensorTemperature}"]`);
        if (value) value.textContent = formatTemp(Number(sensorTemp.value));
      }
    });

    $("view-settings").addEventListener("change", async (event) => {
      const sensorTemp = event.target.closest("input[data-sensor-temperature]");
      if (!sensorTemp) return;
      const sensor = Number(sensorTemp.dataset.sensorTemperature);
      const temperature = Number(sensorTemp.value);
      const previous = Number(sensorTemp.defaultValue);
      const value = document.querySelector(`[data-sensor-temperature-value="${sensorTemp.dataset.sensorTemperature}"]`);
      if (temperature === previous) return;
      if (!window.confirm(`Revise sensor temperature to ${formatTemp(temperature)}?`)) {
        sensorTemp.value = previous;
        if (value) value.textContent = formatTemp(previous);
        return;
      }
      try {
        sensorTemp.disabled = true;
        await sendCommand("sensor_temperature", {sensor, temperature});
        sensorTemp.defaultValue = String(temperature);
        if (value) value.textContent = formatTemp(temperature);
        setTimeout(refresh, 300);
      } catch (err) {
        sensorTemp.value = previous;
        if (value) value.textContent = formatTemp(previous);
        setStatus({ok: false, error: err.message});
      } finally {
        sensorTemp.disabled = false;
      }
    });

    $("view-settings").addEventListener("click", async (event) => {
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
          const hideSpillByAc = new Map(Array.from(document.querySelectorAll("[data-spill-hide-ac]"))
            .map((input) => [Number(input.dataset.spillHideAc), input.checked]));
          const records = acSettingRecordsFromState();
          let hideChanged = false;
          records.forEach((record) => {
            if (!hideSpillByAc.has(Number(record.ac))) return;
            const hideSpill = hideSpillByAc.get(Number(record.ac));
            hideChanged = hideChanged || record.hide_spill_group !== hideSpill;
            record.hide_spill_group = hideSpill;
          });
          await sendCommand("spill", {ac_spill_types: acSpillTypes, spill_groups: spillGroups});
          if (hideChanged) {
            await sendCommand("ac_setting_new", {records});
          }
        } else if (action === "balance-start") {
          await sendCommand("balance_start", {current_values: balanceValuesFromPage()});
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
          applyAcSettingsCard(record, card);
          await sendCommand("ac_setting_new", {records});
        } else if (action === "reset-temp-offsets") {
          const ac = Number(button.dataset.ac);
          const card = button.closest("[data-service-ac]");
          const records = acSettingRecordsFromState();
          const record = records.find((item) => item.ac === ac);
          if (!record) throw new Error(`No AC setting state for AC ${ac + 1}`);
          card.querySelector('[data-field="cool-adjust"]').value = 0;
          card.querySelector('[data-field="heat-adjust"]').value = 0;
          applyAcSettingsCard(record, card);
          record.cool_adjust = 0;
          record.heat_adjust = 0;
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
          refresh(true);
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
          refresh(true);
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
          refresh(true);
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
          refresh(true);
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
        } else if (action === "favourite-clear") {
          await sendCommand("favourite", {
            favourite: Number(favourite),
            name: "",
            groups: []
          });
        }
        setTimeout(refresh, 300);
      } catch (err) {
        setStatus({ok: false, error: err.message});
      } finally {
        setTimeout(() => {
          pendingFavourites.delete(favourite);
          refresh(true);
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
          record.days_bitmap = bitmapFromValues(checkedValues(card, "[data-program-day]"));
          Object.assign(record, groupBitmapFromValues(checkedValues(card, "[data-program-zone]")));
          record.active_ac_bitmap = bitmapFromValues(checkedValues(card, "[data-program-ac]"));
          record.on_timer = timerFromCard(card, "on");
          record.off_timer = timerFromCard(card, "off");
          record.on_setpoint = Number(card.querySelector('[data-field="program-on-setpoint"]').value);
          await sendCommand("program_define_new", {
            program_count: Number((latestState.system || {}).program_count ?? records.length),
            linked_ac: !!((latestState.system || {}).programs_linked_ac),
            records
          });
        } else if (button.dataset.programAction === "program-clear") {
          const program = Number(button.dataset.program);
          const records = programRecordsFromState();
          const index = records.findIndex((item) => item.program === program);
          if (index >= 0) {
            records[index] = clearedProgramRecord(program);
          } else {
            records.push(clearedProgramRecord(program));
          }
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
          refresh(true);
        }, 900);
      }
    });

    async function refresh(force = false) {
      try {
        const [health, state, events] = await Promise.all([
          fetch(apiPath("health")).then((r) => r.json()),
          fetch(apiPath("state")).then((r) => r.json()),
          fetch(apiPath("events")).then((r) => r.json())
        ]);
        setStatus(health);
        if (!force && isEditingForm()) {
          renderEvents(events);
          return;
        }
        renderState(state, events);
        renderEvents(events);
      } catch (err) {
        setStatus({ok: false, error: err.message});
      }
    }

    applyTheme();
    window.addEventListener("resize", () => requestAnimationFrame(updateAlertTicker));
    refresh();
    setInterval(() => refresh(), 1500);
  </script>
</body>
</html>
"""

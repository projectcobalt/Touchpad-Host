# AirTouch 4 Ingress UI Theme Modernization Research

Date: 2026-06-25

Scope: research and recommendations only. This document does not change the AirTouch app, add-on metadata, or runtime files.

## Current UI Snapshot

The current Home Assistant add-on UI lives in `src/airtouch4/service/ui.py` as a single inline HTML/CSS/JS document. It already has useful foundations:

- A practical daily-use `Control` view with zones first and AC controls beside it.
- Light/dark theme tokens and a local theme toggle.
- Dense, status-forward zone rows that suit an HVAC control surface.
- Clear operational states for on, off, spill, warning, pending commands, and service diagnostics.

The theme now feels more like an engineering console than a polished HA-native app. The main visual limitations are:

- Strong rectangular panels and visible borders dominate the page.
- The header is heavy and dark, which makes the UI feel separate from Home Assistant instead of embedded in it.
- State color is doing too much work, with limited depth, hierarchy, or soft surface layering.
- Controls are functionally clear but not very touch-native or fluid.
- Layout is responsive, but not especially adaptive in the modern dashboard sense: it reflows at breakpoints rather than using a more card-grid / section-grid rhythm.
- The theme toggle text/icon treatment is awkward enough to feel unfinished.

## Research References

### Home Assistant Native Direction

Home Assistant's current dashboard direction is section-based and card-based. The Sections view is now presented as a default dashboard layout pattern that organizes cards in a grid, supports dense placement, section backgrounds, conditional visibility, and per-section themes. Relevant reference: [Home Assistant Sections dashboard documentation](https://www.home-assistant.io/dashboards/sections/).

Home Assistant also frames dashboard cards as both display and control surfaces, with resizing in Sections view, actions, features, and conditional visibility. Relevant reference: [Home Assistant dashboard cards](https://www.home-assistant.io/dashboards/cards/).

The developer docs point to a public design portal for reusable UI components, card states, and light/dark comparison. Relevant reference: [Home Assistant frontend design docs](https://developers.home-assistant.io/docs/frontend/design/).

Implication for AirTouch: the app should feel like a first-class HA control panel, not a separate webpage. Borrow the rhythm of HA sections, tiles, chips, cards, and theme variables even though this add-on serves a standalone ingress page.

### Mushroom Cards

Mushroom remains a useful reference because it is widely adopted for clean Home Assistant dashboards. Its stated design goals include easy card configuration, icon and color pickers, Material UI colors, light/dark support, optional theme customization, and low dependency surface. Relevant reference: [Mushroom Lovelace cards](https://github.com/piitaya/lovelace-mushroom).

Patterns worth borrowing:

- Soft, compact cards with clear icon anchors.
- Small "chip" indicators for global status, weather, mode, humidity, and warnings.
- Material-influenced color tokens rather than one-off per-widget colors.
- Controls that remain simple: one primary action, secondary state detail, and optional compact sub-actions.

### Bubble Card

Bubble Card is another relevant HA reference because it focuses on minimalist, customizable cards, popups, horizontal button stacks, sub-buttons, and themeable CSS variables. Relevant reference: [Bubble Card](https://github.com/Clooos/Bubble-Card).

Patterns worth borrowing:

- Rounded, touch-friendly controls without making everything oversized.
- A sticky or footer-like navigation/action stack for mobile.
- Pop-up or drawer style secondary controls, keeping the daily surface uncluttered.
- Theme variables for border radius, background, accent, icon surfaces, sub-button surfaces, borders, and shadows.

### Open Dynamic Export Reference

Reference: [longzheng/open-dynamic-export](https://github.com/longzheng/open-dynamic-export) and project site [opendynamicexport.com](https://opendynamicexport.com/).

Open Dynamic Export is a TypeScript/Vite web dashboard using React, TanStack Router, Tailwind, and HeroUI. Its README describes it as a dynamic export control and solar curtailment project for Australian dynamic connections, fixed/zero export, two-way tariffs, and negative feed-in. The UI is available at the server web port and is built as an operational dashboard rather than a Home Assistant add-on.

Concrete UI observations from the repo:

- It is dark-first: the root shell applies `bg-background text-foreground dark` and keeps the whole app in a dark HeroUI theme.
- Navigation is a sticky, bordered top navbar with a small logo, simple route labels, and a mobile menu.
- The main shell is constrained with `container mx-auto max-w-7xl grow px-6 pt-4`, giving the UI a calm dashboard width rather than full-bleed sprawl.
- The home page uses large section headings followed by responsive card grids, especially `grid gap-4 lg:grid-cols-4`.
- Cards are pressable and navigational, so summary metrics are also drill-in affordances.
- Reading cards use a clear hierarchy: small uppercase domain label, medium title, icon block, large numeric value, muted unit, and subdued footer detail.
- Site / DER / Load readings use separate theme variants that inherit the dark base while changing the card primary color: site cyan, DER purple, load red.
- Directional energy state is shown with restrained semantic color, for example green for export and orange for import.
- Footer details are quiet, using opacity and dividers instead of heavy borders.
- Icons are simple line-style symbols from React icon libraries, housed in softly tinted square icon wells.

Transferable qualities for AirTouch:

- Dark-first can work well if it is intentional and calm, but AirTouch should still preserve the existing `system`, `light`, and `dark` options for Home Assistant ingress.
- The big-number card pattern maps cleanly to room temperature, setpoint, damper, selected AC state, and fault count.
- Domain-colored cards are useful, but for HVAC the domains should be AC, Zone, Sensor, and Service/Fault rather than Site, DER, and Load.
- The ODE purple DER accent should not be copied directly into AirTouch as a dominant theme. Use it only as evidence that per-domain primary color can work.
- The ODE grid rhythm is worth copying more than its exact framework: sticky app bar, constrained width, section headings, responsive metric/control cards, and pressable summary cards.
- ODE's strongest lesson is restraint: few routes, few colors, large readable values, muted secondary metadata, and direct navigation from summary cards.

## Recommended Visual Direction

Target style: HA-native, modern control dashboard, not a marketing app and not a factory LCD clone.

The best direction is a "soft technical dashboard" with an optional ODE-inspired dark-first treatment:

- Keep `system` mode as the add-on default, but make the dark theme polished enough to be the preferred control-room look.
- Light mode should use a calm near-neutral background.
- Dark mode should use warm dark surfaces instead of pure blue-black.
- Airflow and HVAC accents in teal/cyan, but limited to active state, sliders, and key affordances.
- Warm amber reserved for heat/warn/spill, not general decoration.
- Red reserved only for actual errors/faults.
- Cards with subtle elevation or tonal contrast, not heavy outlines.
- Touch-friendly zones and AC controls with compact metrics.
- A sticky mobile command/navigation area so the core controls do not jump around.
- Use ODE-style large operational readings where they help: selected AC temperature, zone setpoint, active damper percentage, current fault count, and runtime connection state.

Avoid:

- A big dark header bar as the main brand signal.
- Heavy gradients across every card.
- Over-rounded pill everything.
- Purple/blue gradient dashboard styling. A small purple domain color is fine if a future design needs a distinct service/diagnostic domain, but it should not become the app's dominant HVAC palette.
- Excessive glassmorphism or blurred backgrounds, especially inside Home Assistant ingress.
- Turning service/debug pages into a decorative dashboard.

## Token Proposal

Keep the existing `system`, `light`, and `dark` theme behavior, but move toward a richer token set that can be applied consistently.

Suggested light tokens:

```css
:root {
  color-scheme: light;
  --surface-page: #f6f8f9;
  --surface-card: #ffffff;
  --surface-raised: #fbfcfd;
  --surface-tint: #eef7f8;
  --text-primary: #11181c;
  --text-secondary: #5e6b73;
  --text-subtle: #7b878e;
  --border-subtle: #dfe7eb;
  --shadow-card: 0 1px 2px rgba(18, 32, 40, 0.08), 0 8px 24px rgba(18, 32, 40, 0.06);
  --accent: #008aa0;
  --accent-strong: #006d80;
  --accent-soft: #dff4f7;
  --ok: #16885f;
  --ok-soft: #e2f5ed;
  --warn: #b77900;
  --warn-soft: #fff1cf;
  --bad: #c0342b;
  --bad-soft: #ffe7e4;
  --cool: #3278d7;
  --heat: #c76a22;
  --radius-card: 12px;
  --radius-control: 10px;
  --radius-chip: 999px;
}
```

Suggested dark tokens:

```css
body[data-theme="dark"] {
  color-scheme: dark;
  --surface-page: #101416;
  --surface-card: #171d20;
  --surface-raised: #1d2529;
  --surface-tint: #12343b;
  --text-primary: #eef4f5;
  --text-secondary: #a8b4b8;
  --text-subtle: #7f8d92;
  --border-subtle: #2c383d;
  --shadow-card: 0 1px 2px rgba(0, 0, 0, 0.26), 0 10px 28px rgba(0, 0, 0, 0.22);
  --accent: #45c0d4;
  --accent-strong: #7fd8e5;
  --accent-soft: #153d45;
  --ok: #55c28d;
  --ok-soft: #143829;
  --warn: #e0ab3f;
  --warn-soft: #3d2f12;
  --bad: #ff766c;
  --bad-soft: #421d1a;
  --cool: #7fb1ff;
  --heat: #f0a15c;
}
```

Implementation note for a later coding thread: keep old variable names temporarily as aliases if needed, then migrate component styles in small passes.

ODE-inspired domain token mapping for AirTouch:

```css
:root {
  --domain-ac: #45c0d4;
  --domain-zone: #55c28d;
  --domain-sensor: #7fb1ff;
  --domain-service: #d5a8ff;
  --domain-fault: #ff766c;
}
```

Use these as small primary accents for icons, left-edge bars, active chips, or selected cards. Do not wash entire zone rows in domain color.

## Layout Recommendations

### 1. Replace the Heavy Header With an App Bar

Current: dark block header with title, status, theme/weather stack, and nav.

Recommended:

- Use a surface app bar that inherits page tone. In dark mode it can follow ODE's sticky bordered navbar pattern.
- Put `AirTouch 4` or `AirTouch 5` on the left.
- Put connection, weather, indoor temperature, active AC, and alert state as compact chips.
- Keep primary nav as a segmented control below or beside the title depending on width.
- Use icon-only theme toggle with a title/tooltip, not the visible word "Theme".

This makes the add-on feel like it belongs inside HA instead of launching a separate console.

### 2. Use Sections Instead of Page Panels

Current: `section` blocks with borders.

Recommended:

- Treat top-level areas as unframed sections.
- Use cards only for repeated content: zone rows, AC selector cards, metrics, favourites, programs, diagnostics.
- Use subtle section headers and let spacing create hierarchy.
- Borrow ODE's section rhythm: a concise heading followed by a `gap`-driven responsive grid.
- Consider a control layout like:
  - Top app bar: title, status chips, nav.
  - Main control grid: zones list wide, selected AC panel narrow.
  - Secondary row: current faults, weather/indoor, runtime compact metrics.

### 3. Modernize Zone Rows

Current zone rows are functional and dense, with columns for name, power, metrics, damper, and actions.

Recommended zone row anatomy:

- Left: zone name, small state chips (`On`, `Sensor`, `Spill`, `Turbo`).
- Center: room temp and setpoint as paired metric blocks.
- Right: damper slider/progress plus power and quick nudges.
- Active zone: soft accent or ok tint on the left edge or background, not a full green wash.
- Off zone: reduce affordance opacity lightly, but keep name and power button clear.
- Fault/spill: use small warning chip and tonal border, not a strong yellow panel.

### 4. Make the AC Panel Feel Like the Primary Controller

Current AC card has readings and action buttons, but it reads like a data panel.

Recommended:

- Selected AC card should have an ODE-style big-value treatment for setpoint and room temperature, with muted units and metadata.
- Mode, fan, power, and setpoint actions should be grouped into segmented controls or icon buttons.
- AC selector cards should become compact tabs/cards above the AC panel only when more than one AC exists.
- Use `cool`, `heat`, `fan`, and `dry` color accents sparingly, mostly in icons or small chips.

### 5. Mobile Behavior

Recommended:

- Preserve zones-first behavior.
- Make zone rows become compact cards with two-column metric blocks.
- Move view navigation to a bottom segmented action bar or sticky footer-like control.
- Keep AC controls reachable without pushing zones too far down: either sticky selected AC summary or collapsible AC panel.
- Make sliders and power buttons at least 40-44px touch targets.

## Component Recommendations

### Chips

Use chips for:

- Connection state.
- Weather and indoor condition.
- Active AC.
- Fault count.
- Spill/storage.
- Sensor source.
- Runtime boot status.

Chips should be status indicators, not command buttons unless explicitly interactive.

### Buttons

Use three button styles:

- Primary: only for the main action in a local context.
- Secondary: regular commands.
- Icon/tonal: repeated small actions such as power, plus/minus, fan, mode.

Avoid putting text labels on every tiny repeated action. For known symbols like power, plus, minus, theme, fan, and mode, use icons or simple glyphs with accessible labels.

### Cards

Use cards for repeated or movable units:

- Zone card/row.
- AC selector card.
- Favourite/program card.
- Metric card.
- Service group card.

Avoid nesting cards inside top-level cards.

ODE-specific card pattern to adapt:

- Small uppercase domain label.
- Human-readable title.
- Optional icon well at top right.
- Large primary value with muted unit.
- Footer for phase-like detail. In AirTouch this could be sensor source, min damper, spill status, or last update.
- Pressable summary cards only where the click target opens a deeper view or changes selection.

### Sliders and Progress

Damper percentage should stay visible as both number and bar/slider. The current range input is useful. The style should be softened:

- Track: neutral surface.
- Fill/accent: teal/cyan.
- Disabled/off state: muted track.
- Spill/warn state: amber fill only if the damper state itself is warning-related.

## Suggested Staged Plan For A Future Implementation Thread

### Phase 1: Token and Surface Refresh

- Add expanded semantic tokens.
- Replace heavy header colors with surface tokens.
- Soften borders and backgrounds.
- Add card shadows/tonal separation.
- Fix theme toggle copy/icon treatment.
- Add domain accent tokens inspired by ODE, mapped to AirTouch concepts.

Risk: low. Mostly CSS.

### Phase 2: Control Page Layout

- Refactor top-level control layout into app-bar plus section-grid rhythm.
- Modernize zone rows while preserving existing DOM actions and data attributes.
- Update AC panel hierarchy.
- Improve mobile layout and sticky navigation.
- Convert selected AC and key runtime/fault data into ODE-style large-value summary cards.

Risk: medium. CSS plus small HTML template changes.

### Phase 3: Interaction Polish

- Add pending-state microcopy/spinners consistently.
- Make plus/minus/power/fan controls icon-led.
- Introduce compact fault and runtime chips.
- Tune hover/focus-visible states.

Risk: medium. Needs careful command-button event compatibility.

### Phase 4: Optional Structural Cleanup

- Split inline CSS/JS from `ui.py` into static strings or package resources if the add-on packaging allows it.
- Add a local static preview fixture for UI regression screenshots.
- Consider WebSocket state updates later, but do not mix that with theme work.

Risk: higher. Worth doing only after visual direction settles.

## Concrete Recommendation

The best near-term modernization is not a full rewrite. Keep the current app architecture and data bindings, then apply a modern HA-inspired skin:

1. Adopt a richer token system with semantic surfaces, status colors, radius, and elevation.
2. Add ODE-inspired domain accents for AC, Zone, Sensor, Service, and Fault.
3. Replace the dark header with a sticky surface app bar and compact status chips.
4. Make the control page feel like a HA Sections / ODE dashboard hybrid: constrained width, section headings, responsive grids, repeated cards, less border weight.
5. Restyle zones as soft, dense control rows with clear state chips and touch-ready controls.
6. Give the selected AC and key metrics the ODE big-number treatment.
7. Keep diagnostics/service views calmer and more utilitarian than the daily control surface.

This should produce the biggest perceived upgrade while protecting the protocol/runtime work and avoiding a risky frontend rebuild.

## Open Questions

- Confirm whether the add-on ingress UI must remain dependency-free, or whether icon fonts / bundled SVG symbols / a tiny static asset are acceptable.
- Confirm whether future implementation should keep the full UI inline in `ui.py` or split CSS/JS into package resources.

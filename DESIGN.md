# Design System — NammaKural (*நம்ம குரல்*)

<!-- impeccable:design-schema 1 -->

## Visual World & Thesis

**Chennai Metro / Southern Railway Enameled Civic Wayfinding & Dispatch Ledger.**
Built for bright tropical daylight and congested 3G/4G street conditions, NammaKural rejects every trope of the 6 government portals it bridges (no multi-step grey Bootstrap forms, no hexagonal splash art, no floating social sidebars, no tiny cramped dropdowns).

## Color Tokens

- `--bg-paper`: `#EDF1F5` (Cool Mineral Slate Mist — page ground)
- `--bg-sheet`: `#FFFFFF` (Pure Enameled Ledger Sheet — active panels)
- `--bg-recessed`: `#DFE6ED` (Recessed Header / Control Well)
- `--bg-rail`: `#CFD9E3` (Inactive Tab / Divider Rail)
- `--ink-primary`: `#0F1722` (Deep Indigo-Slate Ink — primary copy & 1.5px structural borders)
- `--ink-secondary`: `#2E3D52` (Secondary label ink, contrast ≥ 8.5:1)
- `--ink-muted`: `#4E5F75` (DOM field IDs & metadata, contrast ≥ 5.2:1)
- `--rule-hairline`: `#C5D1DD` (1px inner table ledger lines)
- `--rule-strong`: `#7F91A6` (Control & chip borders)
- `--vermilion`: `#C43B1A` (Chola Terracotta Vermilion — reserved strictly for primary voice dictation & matched portal pills)
- `--kaveri-teal`: `#096356` (Kaveri Teal — verified ArcGIS jurisdiction locks & copy confirmations)
- `--turmeric-amber`: `#8F4F00` (Turmeric Amber — landmark disambiguation & OTP gate warnings)
- `--whatsapp-green`: `#11663E` (Zero-Copy-Paste Official WhatsApp Bot trigger)

## Typography

- **Primary UI & Latin Display:** `Atkinson Hyperlegible` (`400`, `700`) — engineered for high-glare legibility and elder/low-vision accessibility.
- **Tamil Script (*தமிழ்*):** `Noto Sans Tamil` (`500`, `600`, `700`) — balanced at equal optical cap-height alongside Latin headings.
- **Tabular Data, GIS Road IDs, Helplines & Character Counters:** `JetBrains Mono` (`500`, `600`) with `font-variant-numeric: tabular-nums`.

## Layout Architecture (Master · Mid · Inner)

1. **Master Layout (`.master-header` + `.master-shell`):** Sticky `1.5px`-bordered top wayfinding bar containing bilingual identity, task mode segmented switch (`New Street Grievance` vs `Closed Without Fix 1100`), and 2G/3G Lite Mode telemetry toggle (`14 KB · <5ms`).
2. **Mid Layout (`.mid-workbench`, switchable via `?variant=A|B|C`):**
   - **Variant A (`Split Civic Workbench`):** 12-column asymmetric split (`5fr` Voice & Evidence Intake Dock | `7fr` GIS Jurisdiction Strip + Zero-Copy Assisted Bar + Split Portal Schema Sheets).
   - **Variant B (`Single-Column Assisted Stream`):** Thumb-first vertical flow (`max-width: 760px`) for 1-handed mobile street use and elder/volunteer assisted filing.
   - **Variant C (`3-Pane Command Triage Matrix`):** High-density desktop dispatch grid (`Voice & Photo Dock` | `GIS Telemetry + Zero-Copy Assisted Bar` | `Split Portal Schema Inspector`).
3. **Inner Layout (`.ledger-panel`, `.gis-strip`, `.inclusive-bar`, `.portal-sheet`, `.field-row`):** Crisp `1.5px` structural borders (zero diffuse shadows on bordered cards), stepped portal filter tabs, 3-column field copy rows (`Label + DOM ID` | `Resolved Value + Character Counter` | `1-Tap Copy Button`), and an interactive HTML5 Canvas `<1 MB` Evidence Photo Stamper.

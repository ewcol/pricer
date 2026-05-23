<!-- SEED: re-run /impeccable document once there's code to capture the actual tokens and components. -->

---
name: eBay Seller Agent
description: AI-powered pricing and listing tool for resellers
colors:
  surface: "#f8f7f5"
  surface-raised: "#ffffff"
  ink: "#111110"
  ink-muted: "#6b6b67"
  ink-faint: "#a8a8a4"
  border: "#e4e3df"
  accent: "#1a56db"
  accent-hover: "#1447c2"
  accent-surface: "#eef3fd"
  success: "#1a7f4b"
  success-surface: "#edfaf3"
  warning: "#b45309"
  warning-surface: "#fef9ee"
typography:
  display:
    fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif"
    fontSize: "clamp(2rem, 4vw, 3rem)"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.01em"
  title:
    fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1.4
  body:
    fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "'Plus Jakarta Sans', system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "0.04em"
  mono:
    fontFamily: "'Geist Mono', 'JetBrains Mono', monospace"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.6
rounded:
  none: "0px"
  sm: "4px"
  md: "6px"
  lg: "10px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "40px"
  2xl: "64px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "#ffffff"
    rounded: "{rounded.md}"
    padding: "10px 20px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-secondary:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "10px 20px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ink-muted}"
    rounded: "{rounded.md}"
    padding: "10px 20px"
  input:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "10px 14px"
  card:
    backgroundColor: "{colors.surface-raised}"
    rounded: "{rounded.lg}"
    padding: "{spacing.lg}"
---

# Design System: eBay Seller Agent

## 1. Overview

**Creative North Star: "The Appraiser's Desk"**

A clean, light workspace where an expert has laid out evidence and reached a verdict. The UI surfaces agent intelligence with the same authority a Sotheby's appraiser uses to quote a price: no hesitation, no hedging, no decoration. The recommended price is the hero. The confidence score is the backing evidence. Everything else is context.

The surface is warm off-white — not clinical white, not dark. The ambient light metaphor: a well-lit office at midday, a professional using a real tool to do real work. The accent is a precise slate-blue, used only when something is interactive or confirmed. Data labels are small-caps monospaced. Prices are large, weight 700, no color.

This system rejects: rounded icon-grid cards from 2018 SaaS dashboards, teal+orange "helpful tool" palettes, tooltip-heavy dense tables, and anything that signals "I'm a demo." The agent has done serious work. The UI should be as confident as the agent.

**Key Characteristics:**
- Committed light surface: off-white base (`#f8f7f5`), pure white raised panels
- One accent, precisely used: slate-blue (`#1a56db`) on interactive elements and confirmed states only
- Choreographed output: agent results reveal progressively as each step completes
- Humanist sans throughout: Plus Jakarta Sans — warm but precise
- Mono for data: prices, IDs, drift percentages in Geist Mono
- Flat by default: no shadows at rest; elevation on hover/focus only

## 2. Colors: The Appraiser's Palette

The palette has one job: keep the agent's output readable and trustworthy. Warmth comes from the surface tint, not from color variety.

### Primary
- **Precision Blue** (`#1a56db`): The sole interactive accent. Buttons, active states, selected rows, links. Used on ≤15% of any screen. Its scarcity is its authority.

### Neutral
- **Warm Paper** (`#f8f7f5`): Page background. Tinted toward warm gray to avoid clinical white. Never pure white.
- **Raised Surface** (`#ffffff`): Cards, input backgrounds, panels that sit above the page.
- **Ink** (`#111110`): Primary text. Tinted warm to pair with the surface.
- **Muted Ink** (`#6b6b67`): Secondary labels, metadata, placeholder text.
- **Faint Ink** (`#a8a8a4`): Disabled states, dividers used as text.
- **Border** (`#e4e3df`): Dividers, input strokes, card borders when used. One consistent value.

### Semantic
- **Confirmed Green** (`#1a7f4b`) / surface `#edfaf3`: Price confirmed, item tracked, positive drift.
- **Caution Amber** (`#b45309`) / surface `#fef9ee`: Price drift warnings, low confidence signals.

### Named Rules
**The One Accent Rule.** Precision Blue is used for interactive elements and confirmed states only. It does not appear in headers, illustrations, backgrounds, or decorative elements. A screen with 85% neutrals and 15% blue is correct. A screen with 40% blue is broken.

**The No Warm-Cool Split Rule.** The palette is warm-neutral throughout. No cool grays, no blue-tinted surfaces, no competing temperature zones. Warmth is consistent from page background to border to text.

## 3. Typography

**Body + Label Font:** Plus Jakarta Sans (system-ui fallback)
**Mono Font:** Geist Mono (JetBrains Mono fallback)

**Character:** Plus Jakarta Sans has just enough warmth to feel like a professional tool rather than a developer console, without the softness that would undermine the tool's authority. The mono stack is reserved exclusively for data: prices, item IDs, percentages, timestamps.

### Hierarchy
- **Display** (700, clamp(2rem–3rem), lh 1.1, ls -0.02em): Reserved for the recommended price — the largest, most important output of any analysis run.
- **Headline** (600, 1.5rem, lh 1.25, ls -0.01em): Section titles, item name output, tab names.
- **Title** (600, 1rem, lh 1.4): Card headings, field labels above inputs.
- **Body** (400, 0.9375rem, lh 1.6): Description output, prose content, max 70ch line length.
- **Label** (500, 0.75rem, lh 1.4, ls 0.04em, uppercase): Form labels, metadata tags, confidence badges. All-caps.
- **Mono** (400, 0.875rem, lh 1.6): Prices, percentages, item IDs, timestamps, all numeric data.

### Named Rules
**The Price Is Display Rule.** The recommended price always renders at Display scale, weight 700, in Geist Mono. Nothing else on the screen uses Display. If you're tempted to use Display for a heading, use Headline instead.

**The Mono-For-Numbers Rule.** Every numeric value (price, confidence percentage, item ID, drift) renders in Geist Mono, not Plus Jakarta Sans. The visual distinction signals "this is a data point, not prose."

## 4. Elevation

This system is flat by default. Surfaces are distinguished by background color (`surface` vs `surface-raised`), not by shadow. Shadows appear only as interaction feedback.

### Shadow Vocabulary
- **Hover lift** (`0 2px 8px rgba(17,17,16,0.08), 0 1px 2px rgba(17,17,16,0.04)`): Applied to interactive cards on hover. Disappears on mouseout. Never present at rest.
- **Focus ring** (`0 0 0 3px rgba(26,86,219,0.25)`): The only blue glow in the system. Keyboard focus indicator only.
- **Dropdown/popover** (`0 8px 24px rgba(17,17,16,0.12), 0 2px 4px rgba(17,17,16,0.06)`): Floating layers that need to read above the page. Modals, tooltips if used.

### Named Rules
**The Flat-By-Default Rule.** No element has a shadow at rest. Elevation is earned by state change (hover, focus, open). A card that always has a shadow is using decoration to signal importance; importance should come from content hierarchy instead.

## 5. Components

### Buttons
Sharp, compact, unambiguous. Padding is generous enough to be tappable, tight enough to feel like a tool not a marketing page.
- **Shape:** Square corners (0px radius) — this is not a friendly app, it's a professional tool
- **Primary:** Precision Blue background (`#1a56db`), white text, 10px 20px padding, 500 weight, 0.875rem
- **Hover:** `#1447c2`, cursor pointer, no transform
- **Focus:** 3px blue focus ring (offset 2px)
- **Secondary:** White background, Ink text, Border stroke (1px `#e4e3df`), same padding
- **Ghost:** Transparent, Muted Ink text, no border — for cancel/dismiss actions only

### Input Fields
- **Style:** White background, Border stroke (1px `#e4e3df`), square corners (4px — the minimum, just to prevent clip), Ink text at Body scale
- **Placeholder:** Faint Ink (`#a8a8a4`)
- **Focus:** Border shifts to Precision Blue (1px → 1px, color change only, no glow), plus focus ring
- **Disabled:** Surface background, Faint Ink text, no interaction
- **Error:** Warning Amber border, warning surface background tint

### Output Panels (signature component)
The core pattern: a labeled section that populates progressively as the agent produces output.
- Structured as: Label (uppercase, Label scale, Muted Ink) above a Raised Surface panel
- Panel has 16px internal padding, 6px radius, 1px Border stroke
- Content fades in (`opacity 0 → 1`, 200ms ease-out) when the agent populates it
- Empty state: `—` in Faint Ink (never blank, never a spinner where content will be)

### Confidence Badge (signature component)
- Sits beneath the item name in analysis output
- Two states: **Signals agree** — success green surface, Confirmed Green text, checkmark icon; **Signals disagree** — warning amber surface, Caution Amber text, exclamation icon
- Percentage in Geist Mono, status text in Label scale uppercase, 8px gap between them
- No border. Color surface IS the affordance.

### Data Table (Tracked Items)
- Header row: Label scale, uppercase, Muted Ink, Border bottom, 12px 16px padding
- Data rows: Body scale, Ink, 14px 16px padding, Border bottom
- Hover state: `surface` background tint (the raised surface drops to page-level on hover to create a subtle inversion)
- Price column: Geist Mono
- Drift column: Geist Mono + semantic color (Confirmed Green for positive, Caution Amber for ≥10% negative)
- Selected row: `accent-surface` background (`#eef3fd`), 1px Precision Blue left rule — the one place a left-border is appropriate (it marks row selection state, not decoration)

### Navigation / Tabs
- Two tabs: "Price & List" and "Tracked Items"
- Tab bar: full-width, 1px Border bottom, no background
- Active tab: Ink text (weight 600), 2px Precision Blue bottom border
- Inactive tab: Muted Ink text, no border, hover transitions to Ink
- No filled tab backgrounds, no pill shapes

## 6. Do's and Don'ts

### Do:
- **Do** render the recommended price at Display scale (clamp 2–3rem, weight 700, Geist Mono). It's the primary output. It must dominate.
- **Do** use square corners (0–4px) for interactive elements. Sharp edges signal precision.
- **Do** use Plus Jakarta Sans for all prose and Geist Mono for all numeric data. The type split carries semantic meaning.
- **Do** reveal agent output progressively with fade-in (200ms ease-out) as each pipeline step completes. The process is the demo.
- **Do** show the confidence score and signal-agreement status prominently, directly below the item name. Transparency is a design value here.
- **Do** keep the accent blue (`#1a56db`) on ≤15% of any screen surface. Restraint is authority.
- **Do** use the warm off-white (`#f8f7f5`) as the page background. Never pure `#fff` or `#000`.
- **Do** label every output field with uppercase Label-scale text in Muted Ink above it.

### Don't:
- **Don't** use rounded icon-grid cards (icon + heading + paragraph × N). This is the 2018 HubSpot SaaS pattern. Prohibited.
- **Don't** use teal, orange, or any warm-cool palette split. The system is warm-neutral only.
- **Don't** use gradient text (`background-clip: text`). Ever. Single solid color only.
- **Don't** apply shadows at rest. Flat by default; elevation is earned by hover or focus state.
- **Don't** use `border-left` as a colored stripe on cards or list items for decoration. The one exception is selected-row state in the data table.
- **Don't** put the recommended price in body text. If it's not at Display scale, it's wrong.
- **Don't** use tooltips as the primary way to surface information. If the content is important, it's in the layout.
- **Don't** use animated spinners during agent analysis — use a skeleton/shimmer on the output panels instead.
- **Don't** use placeholder helper text that just repeats the field label ("Item name goes here"). Empty states show `—`.
- **Don't** make it look like a Gradio app, a Hugging Face Space, or any ML demo toy. This is a professional pricing tool.

---
name: product-encyclopedia
description: >
  Generate interactive, single-file HTML product comparison pages (product encyclopedia / buyer's guide).
  Use when asked to: (1) Compare products across brands/models with specs and prices,
  (2) Create buyer's guides or selection tools, (3) Build interactive product catalogs,
  (4) Make "which X should I buy" decision pages. Covers data collection, anti-AI-slop
  design, responsive mobile layout, interactive filtering/sorting/comparison, and
  tasteful Apple-inspired animations. Output is a self-contained HTML file that can be
  shared via any channel.
---

# Product Encyclopedia

Generate interactive single-file HTML product comparison pages. From data collection to polished output.

## Workflow

### 1. Collect Product Data

Use `web_search` to gather for each model:
- Official name, brand, series/tier
- Key category-specific attributes (the dimensions users compare on)
- Price from major e-commerce (JD/Taobao/Amazon) — note both list price and promo price
- Purchase link (use search URL if direct product URL unavailable: `https://search.jd.com/Search?keyword=ENCODED_QUERY`)

Structure data as a JS array in the HTML for client-side filtering. See [references/data-schema.md](references/data-schema.md).

### 2. Design — Anti-AI-Slop Rules

**MANDATORY.** Read [references/design-rules.md](references/design-rules.md) before writing any CSS.

Summary of bans:
- No purple-blue-pink gradients
- No emoji as icons
- No pill/badge overload
- No glassmorphism / grain texture
- No dark theme + neon accents
- No dot-matrix rating systems (●●●○○)
- No uniform 3-card symmetric grids

Use Apple.com as the reference: white bg, black type, one accent color, huge whitespace, restrained motion.

### 3. Page Structure

Build these sections in order. Each section uses a different layout rhythm — never repeat the same visual structure consecutively.

1. **Sticky nav** — scroll-aware, blur bg, section links with active highlight
2. **Hero** — massive title + subtitle, no image, animate on load
3. **Category explainer** — clickable cards (clicking filters the product list below), with purchase recommendation integrated at the bottom of each card (scenario + budget + recommended models)
4. **Comparison table** — column-highlight on hover, clean text (no progress bars)
5. **Product cards** — filterable grid with: type filter buttons, price range slider, sort toggle, compare checkboxes, product images from official CDN
6. **Compare drawer + modal** — bottom bar shows selected items, modal shows side-by-side table
7. **Footer** — data source disclaimer

### 4. Product Images

- Fetch product images from official brand websites (CDN URLs)
- Use browser tool to navigate brand product pages and extract `<img>` src URLs
- Prefer white/transparent background product shots
- Add `img` field to model data, render in cards with `loading="lazy"` and `onerror` fallback
- Style: `object-fit: contain`, max 200px wide, centered above card content
- Not all models need images — better to omit than use low-quality shots

### 5. Interactive Features (HTML's Advantage)

These are what make HTML better than PDF. Always include:

| Feature | Implementation |
|---------|---------------|
| **Category filter** | Toggle buttons + clickable type cards, `data-*` driven |
| **Price slider** | `<input type="range">` with live label update |
| **Sort** | 3-state toggle: default → asc → desc → default |
| **Compare** | Checkbox on each card (max 4), sticky bottom drawer, modal with `<table>` (NOT CSS Grid) |
| **Column highlight** | `onmouseenter` on `<th>` highlights entire column |
| **Scroll spy** | `IntersectionObserver` or scroll listener updates nav active state |
| **Scroll reveal** | `IntersectionObserver` adds `.visible` class for fade-up entrance |

All filtering/sorting happens client-side in JS — no framework needed.

### 6. Purchase Recommendations — Merge Into Category Cards

Do NOT create a separate "verdict" or "recommendation" section. Instead, integrate purchase advice directly into each category explainer card:

```html
<div class="type-verdict">
  <p class="type-verdict-title">场景名称 · 预算范围</p>
  <p class="type-verdict-desc">一句话说明为什么选这个方案</p>
  <p class="type-verdict-models">推荐：具体型号 · 具体型号 · 具体型号</p>
</div>
```

Style with a top border separator (`border-top: 1px solid var(--gray-border)`) inside the card. No colored backgrounds — keep it consistent with the card's white bg.

### 7. Animation — Tasteful Only

Read [references/animation-guide.md](references/animation-guide.md).

Rules:
- Hero title: `fadeUp 0.8s ease` on load
- Sections: scroll-triggered `fadeUp` via IntersectionObserver, `threshold: 0.12`
- Cards: `scaleIn` with staggered `animation-delay` (50ms increments, cap at 600ms)
- Hover: `translateY(-4px)` + shadow deepening, 300ms transition
- Modals: bg `fadeIn 0.2s` + content `scaleIn 0.3s`
- Nav: add shadow on scroll (`box-shadow` transition)
- **No bounce, no elastic, no shake, no rotate**

### 8. Mobile Responsiveness

- Cards → single column below 640px
- Tables → horizontal scroll with `-webkit-overflow-scrolling: touch`
- Font sizes: minimum 14px for body, 13px for labels
- Filter bar wraps naturally with `flex-wrap`
- Price row stacks vertically on narrow screens
- Compare drawer stays usable (items wrap, button stays accessible)
- Compare modal: mobile → bottom sheet (`align-items: flex-end`, `border-radius: 20px 20px 0 0`), desktop → centered
- Compare table: use `<table>` NOT CSS Grid (Grid rows have independent column widths = misalignment bug)
- Touch targets minimum 44px

### 9. Output

Single self-contained `.html` file. Everything inline:
- CSS in `<style>`
- JS in `<script>`
- Data as JS object literal
- Google Fonts via `@import` (only dependency)
- No external images, no framework CDN

File size target: < 50KB.

### 10. Color System

```css
:root {
  --black: #1d1d1f;
  --gray-dark: #424245;
  --gray: #6e6e73;
  --gray-light: #86868b;
  --gray-border: #d2d2d7;
  --bg: #fff;
  --bg-alt: #f5f5f7;
  --blue: #0071e3;       /* primary accent — links, best-in-class highlights */
  --green: #34c759;      /* secondary category color */
  --purple: #af52de;     /* tertiary category color */
  --orange: #ff9500;     /* quaternary category color */
  --red: #ff3b30;        /* negative/warning */
}
```

Assign each product category a color. Use it only for category labels and filter buttons — not backgrounds or gradients.

### 11. Typography

```css
font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif;
```

- Hero title: `clamp(36px, 7vw, 72px)`, weight 900
- Section title: `clamp(28px, 4.5vw, 48px)`, weight 700
- Body: 14-15px, weight 400
- Labels: 11-13px, weight 600, uppercase, letter-spacing 0.05-0.08em

**Best-in-class values** in comparison tables: `font-weight: 700; color: var(--blue)`.
Worst values: `color: var(--gray-light)` or `color: var(--red)`.
Middle values: `color: var(--gray-dark)`.

# Anti-AI-Slop Design Rules

These patterns scream "AI-generated." Avoid all of them.

## Banned Patterns

### Colors
- ❌ Purple-blue-pink gradients (`from-blue-400 via-purple-400 to-pink-400`)
- ❌ Gradient text on titles
- ❌ Dark background + neon/glowing accents
- ❌ Evenly-distributed rainbow palettes
- ✅ White/light bg + black text + ONE accent color (blue)
- ✅ Alternate sections with `#fff` and `#f5f5f7`

### Layout
- ❌ Three identical cards in a symmetric row
- ❌ Every section using the same structure (gradient bar title → cards → repeat)
- ❌ Centered, symmetrical, predictable everything
- ✅ Break symmetry: vary section layouts (table, cards, full-width, split)
- ✅ Use different rhythms between sections

### Visual Elements
- ❌ Emoji as icons (🪨🌀🏠🐳)
- ❌ Dot-matrix ratings (●●●●○)
- ❌ Pill/badge overload on every feature
- ❌ Glassmorphism / `backdrop-filter: blur` everywhere
- ❌ SVG noise/grain texture overlays
- ❌ Progress bars in comparison tables
- ✅ Plain text with weight/color hierarchy
- ✅ Use font-weight 700 + accent color for "best" values
- ✅ Use lighter gray for weaker values

### Animation
- ❌ Everything fading in from below on scroll
- ❌ Bouncy/elastic/springy effects
- ❌ Hover effects on every single element
- ✅ Hero loads with one subtle animation
- ✅ Sections reveal on scroll, but only once per element
- ✅ Card hover: slight lift + shadow, nothing more

### Typography
- ❌ Inter, Roboto, Arial as display fonts
- ❌ Uniform font sizes across all sections
- ✅ Large size jumps: hero 72px → section 48px → body 15px
- ✅ Use weight to create hierarchy, not color

### Comparison/Data Tables
- ✔️ Use `<table>` for multi-column data comparison (browser auto-aligns columns)
- ❌ Do NOT use CSS Grid with independent `.row` elements (each row is a separate grid → columns misalign)
- ❌ Do NOT use progress bars / dot-matrix in table cells
- ✔️ Use font-weight + color to distinguish best/mid/weak values

### Recommendation Cards
- ❌ Do NOT use colored backgrounds (pastel blue/green/purple) for recommendation cards — this is the #1 AI-slop tell
- ❌ Do NOT create a separate "verdict" section — merge purchase advice into category explainer cards
- ✔️ Use white bg + fine gray border, same as other cards
- ✔️ Separate with a subtle `border-top` inside the card
- ✔️ Keep accent colors for text only (labels, links), never backgrounds

### Product Images
- ✔️ Fetch from official brand CDN (Shopify, ecovacs.com, dji.com, etc.)
- ✔️ Add `onerror` handler to hide broken images gracefully
- ✔️ Use `loading="lazy"` and `object-fit: contain`
- ❌ Do NOT use AI-generated product images
- ❌ Do NOT force images on every card — omit if no clean official image available

## Reference: Apple.com Characteristics
- White background, no dark theme
- SF Pro / system font (we use Noto Sans SC for CJK)
- Massive whitespace — sections have 80-100px padding
- One blue accent color (#0071e3) for links and CTAs
- Typography does all the heavy lifting
- Animations are subtle and occur exactly once
- No decorative elements — content IS the design

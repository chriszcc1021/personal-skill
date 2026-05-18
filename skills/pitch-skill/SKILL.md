---
name: pitch-skill
description: Use when building, reviewing, or refining a data-backed pitch deck, market opportunity deck, game publishing forecast, business case, or PnL-linked revenue story. Especially useful for turning messy research, comparable products, Sensor Tower/API data, Excel/PnL assumptions, and browser slide comments into a clear narrative with scenarios, visual evidence, and versioned changes.
---

# Pitch Skill

Use this skill to turn scattered research and assumptions into a credible pitch. The goal is not to make a pretty slide dump; it is to make a decision easier.

## Core Mindset

Start with the decision question:

- Should we publish, invest, test, fund, launch, or change direction?
- What would make the audience believe this is worth doing?
- Which assumptions would break the case if they are wrong?

Build the pitch as a chain of claims:

1. Market/product opportunity.
2. Comparable evidence.
3. Forecast model.
4. Scenario range.
5. Risks and validation plan.
6. Business/PnL implication.

Every chart, table, image, and number should support one link in that chain.

## Workflow

### 1. Frame the Story

Before editing or creating slides, identify:

- Audience: investment, publishing, executive update, product review, partner negotiation, or internal alignment.
- Decision: what the pitch must help decide.
- Main thesis: one sentence that can survive pushback.
- Counter-thesis: the strongest reason the thesis may be wrong.

Prefer conclusion-style slide titles. Avoid vague titles such as "Market Analysis" when the title could say "Thailand and Mexico are the first-year RPD markets."

### 2. Split the Model Into Variables

Do not let one comparable product prove everything. Decompose the case:

- Downloads / reach.
- Monetization quality: RPD, ARPU, payer depth, skin/pass/IAP fit.
- Retention / engagement.
- Virality / social spread.
- Regional fit.
- Cost, channel, marketing, MG, royalty, and PnL impact.

Assign evidence to one variable at a time.

Example:

- Horror mobile games may validate local download appetite.
- Character/skin games may validate RPD.
- Party/social games may validate friend-invite spread.
- Domestic performance may validate product monetization design, but still needs country discounting.

### 3. Give Regions Clear Roles

Do not treat all markets as the same. Label each region/country by what it proves:

- Download market.
- RPD / payment-quality market.
- Social-spread market.
- Visual/aesthetic validation market.
- Small probe / risk-controlled market.

When changing revenue, decide whether the change comes from volume or price:

- Volume change: downloads, virality, channel reach, localization, short-video spread.
- Price change: RPD, payer mix, IAP depth, skin conversion, pass conversion.

Do not raise RPD just to hit a revenue target if the country is positioned as a low/mid-payment market.

### 4. Build Scenarios

Use at least two scenarios when uncertainty matters:

- Conservative: local comparable floor, higher deduplication, limited social boost.
- Optimistic: stronger product-market fit, lower friction, better spread, better monetization.

For each scenario, keep formulas readable:

```text
Downloads × RPD = Revenue
Region total = sum(country revenues)
Three-year total = Y1 + Y2 + Y3
```

If the user asks to change a number, update all dependent totals and explain which variable moved.

### 5. Make Comparables Useful

Comparable products are not decorations. For each comparable, state what it calibrates:

- Similar point.
- Dissimilar point.
- How it is used in the model.
- How it is not used.

Good comparable table columns:

- Product / genre.
- Data signal.
- Similarity.
- Difference.
- Model use.

For visual credibility, use real product screenshots or app images where possible. If adding product cards, make images clickable to gameplay videos or official pages.

### 6. Use Data With Proper Strength

Classify data by reliability:

- Hard input: official financials, first-party PnL, API result with clear endpoint and parameters.
- Model input: Sensor Tower estimates, comparable country baskets, inferred RPD.
- Directional evidence: overlap, social buzz, app-store media, gameplay similarity, genre popularity.

Do not convert directional evidence directly into revenue unless a clear formula is defensible. Use it as a correction, validation, or prioritization signal.

When using APIs or private data:

- Do not print or persist tokens.
- Record endpoint, app id, country, date range, platform, and caveats.
- Mention confidence/coverage issues when the source reports them.

### 7. Design the Deck for Scanning

Use visuals to guide attention:

- Big title: the conclusion.
- Table: model and numbers.
- Card wall: country/segment rationale.
- Product image grid: evidence and references.
- Appendix: dense sources, caveats, and raw references.

Make forecast numbers visually heavier than reference numbers. If a table has both reference RPDs and forecast outputs, enlarge or highlight the forecast columns.

Avoid slides that are "all text." If the slide is about product references, use images. If it is about country rationale, use country cards with proof chips/images. If it is about model mechanics, use a compact formula or step table.

### 8. Reconcile With PnL

When a deck also feeds a spreadsheet/PnL, always reconcile:

- Y1/Y2/Y3 revenue.
- Region split.
- Country split.
- Conservative/optimistic versions.
- Total rows and formulas.
- Only-country sheets versus all-region sheets.

If one tab is stale, say exactly which tab and which values are stale.

### 9. Version Every Meaningful Edit

For deck projects, keep versions like code:

- Create a snapshot for each meaningful change.
- Update a changelist with the version number, timestamp, and rollback file.
- Mention what changed and what was verified.

Suggested changelist items:

- Changed assumptions.
- Updated pages/slides.
- Updated dependent totals.
- Visual/layout changes.
- Data/source caveats.
- Verification checks.

### 10. Verification Checklist

Before finalizing:

- The thesis is clear in the first few slides.
- Every major number has a source or formula.
- Scenario totals add up.
- PnL and deck agree.
- Region roles do not contradict the model.
- Comparable products are not overclaimed.
- Visual evidence supports, not distracts.
- Private tokens are not in files or final answers.
- Version snapshot and changelist exist if files changed.

## Useful Phrases

- "This comparable calibrates one variable, not the whole forecast."
- "This market is a download market, not an RPD market."
- "This revenue change should be explained by volume, not price."
- "Overlap is directional evidence; it should not be directly converted into downloads."
- "The appendix can carry the messy proof; the main slide should carry the decision."


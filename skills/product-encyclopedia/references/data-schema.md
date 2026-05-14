# Data Schema

Structure product data as a flat JS array for client-side filtering.

## Required Fields

```javascript
const models = [
  {
    brand: "品牌中文名",       // string — for grouping and display
    brandEn: "BrandEnglish",   // string — subtitle
    tier: "旗舰",              // string — product tier/series label
    name: "型号名称",          // string — model name
    cat: "category-id",        // string — category slug for filtering (e.g. "disc", "roller")
    catLabel: "分类 · 特征描述", // string — human-readable category label
    features: "关键特性描述",   // string — 1-2 sentence feature summary
    price: 3999,               // number — price in local currency, for slider/sort
    priceText: "¥3,999",       // string — formatted display price
    priceNote: "活动低至 ¥3,200", // string|undefined — promo/subsidy note
    img: "https://cdn.example.com/product.png?width=400", // string|undefined — official CDN product image
    releaseDate: "2025-06", // string|undefined — release date (YYYY-MM format)
    jd: "https://search.jd.com/Search?keyword=..." // string — purchase linkned — optional promo/subsidy note
    link: "https://...",       // string — purchase/search URL
  },
];
```

## Category Definition

Define categories separately for filter buttons and type-explainer cards:

```javascript
const categories = [
  { id: "disc", name: "圆盘板", color: "blue", 
    pros: ["优势1", "优势2"], cons: ["劣势1", "劣势2"] },
  { id: "roller", name: "滚筒板", color: "green",
    pros: [...], cons: [...] },
];
```

## Comparison Dimensions

Define comparison table rows:

```javascript
const dimensions = [
  { label: "清洁力", disc: { text: "中等", rank: "weak" }, 
    roller: { text: "较强", rank: "mid" }, 
    track: { text: "最强", rank: "best" } },
];
```

`rank` values: `"best"` → blue bold, `"mid"` → dark gray, `"weak"` → light gray, `"bad"` → red.

## Price Sourcing

When scraping prices:
1. Search `web_search` for "京东 {品牌} {型号} 扫地机器人 价格"
2. Note both list price and lowest promo price
3. For purchase links, if direct product URL requires login, use search URL:
   `https://search.jd.com/Search?keyword={ENCODED_BRAND_MODEL}`
4. Always add a footer disclaimer: prices are reference only, check retailer for real-time pricing

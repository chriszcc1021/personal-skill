# Animation Guide

Tasteful, Apple-inspired animations. Less is more.

## CSS Keyframes

```css
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(32px) }
  to { opacity: 1; transform: translateY(0) }
}
@keyframes fadeIn {
  from { opacity: 0 }
  to { opacity: 1 }
}
@keyframes scaleIn {
  from { opacity: 0; transform: scale(0.95) }
  to { opacity: 1; transform: scale(1) }
}
@keyframes slideUp {
  from { transform: translateY(100%) }
  to { transform: translateY(0) }
}
```

## Where to Use What

| Element | Animation | Timing |
|---------|-----------|--------|
| Hero title | `fadeUp` | `0.8s ease` on load |
| Hero subtitle | `fadeUp` | `0.8s ease 0.15s` (delayed) |
| Section titles/content | scroll-triggered `.visible` class | `transition: 0.6s ease` |
| Product cards | `scaleIn` | `0.4s ease`, stagger `delay: i * 50ms` (cap 600ms) |
| Compare drawer | `slideUp` | `0.3s ease` |
| Modal backdrop | `fadeIn` | `0.2s ease` |
| Modal content | `scaleIn` | `0.3s ease` |
| Modal (mobile) | bottom sheet | `align-items:flex-end`, round top corners only |

## Scroll Reveal Pattern

```css
.animate-on-scroll {
  opacity: 0;
  transform: translateY(32px);
  transition: opacity 0.6s ease, transform 0.6s ease;
}
.animate-on-scroll.visible {
  opacity: 1;
  transform: translateY(0);
}
```

```javascript
const observer = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      e.target.classList.add('visible');
      observer.unobserve(e.target);
    }
  });
}, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

document.querySelectorAll('.section-label, .section-title, .type-grid, .table-scroll, .verdict-card')
  .forEach(el => {
    el.classList.add('animate-on-scroll');
    observer.observe(el);
  });
```

## Hover Effects

```css
/* Cards — subtle lift */
.model-card {
  transition: box-shadow 0.3s, transform 0.3s;
}
.model-card:hover {
  box-shadow: 0 8px 30px rgba(0,0,0,0.08);
  transform: translateY(-4px);
}

/* Buttons — scale feedback on click */
.filter-btn {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.filter-btn:active {
  transform: scale(0.95);
}

/* Nav — shadow appears on scroll */
.topnav { transition: box-shadow 0.3s }
.topnav.scrolled { box-shadow: 0 1px 8px rgba(0,0,0,0.06) }
```

## Card Stagger Pattern

```javascript
document.querySelectorAll('.model-card').forEach((card, i) => {
  card.style.animationDelay = `${Math.min(i * 0.05, 0.6)}s`;
});
```

## Rules

- Every animation plays **exactly once** (use `observer.unobserve`)
- Duration: 200-400ms for interactions, 600-800ms for reveals
- Easing: `ease` or `cubic-bezier(0.4, 0, 0.2, 1)` — never `linear`
- **No bounce, no elastic, no wiggle, no rotation**

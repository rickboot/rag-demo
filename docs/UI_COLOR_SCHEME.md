# UI Color Scheme — Phison Pascari

Color palette for the RAG-demo UI. Source: Phison Pascari enterprise hero (brand alignment).

---

## Palette

| Role | Hex | RGB | Usage |
|------|-----|-----|--------|
| **Primary accent / highlight** | `#FFDD00` | rgb(255, 221, 0) | Vibrant yellow — hero/background, secondary CTAs, play/icons, highlights |
| **Primary brand / text** | `#1C3051` | rgb(28, 48, 81) | Deep dark blue — headings, nav, primary buttons, key text |
| **Contrast / secondary** | `#FFFFFF` | rgb(255, 255, 255) | White — body text on yellow, button text on blue, secondary backgrounds |

---

## Usage

- **Primary CTA (e.g. “Run”, “Start session”):** Blue background (`#1C3051`), white text (`#FFFFFF`), optional yellow icon accent.
- **Secondary CTA (e.g. “Contact”, “Settings”):** Yellow background (`#FFDD00`), blue text and border (`#1C3051`).
- **Headings / nav:** Blue (`#1C3051`).
- **Body on yellow:** White (`#FFFFFF`) for readability.
- **Body on white/light:** Blue (`#1C3051`) for text.
- **Accents / badges / “live” indicators:** Yellow (`#FFDD00`).
- **Neutral / imagery:** Grayscale for photos or decorative elements to keep focus on yellow/blue.

---

## CSS variables (for implementation)

```css
:root {
  --pascari-yellow: #FFDD00;
  --pascari-blue: #1C3051;
  --pascari-white: #FFFFFF;
  /* Optional */
  --pascari-yellow-rgb: 255, 221, 0;
  --pascari-blue-rgb: 28, 48, 81;
}
```

---

## Contrast

- **Blue on yellow:** Strong contrast; use for borders, outlines, secondary button text.
- **White on blue:** Strong contrast; use for text and icons on blue buttons/headers.
- **White on yellow:** Strong contrast; use for body text on yellow backgrounds.

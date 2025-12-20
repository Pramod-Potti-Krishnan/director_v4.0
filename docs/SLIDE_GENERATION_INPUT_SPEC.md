# Slide Generation Input Specification

**Version**: 1.0
**Last Updated**: December 2024
**Status**: Canonical Reference

This document serves as the authoritative "bible" for all slide generation inputs across the Deckster presentation platform. It defines exact input requirements for Director Agent, Text Service, Analytics Service, Diagram Service, and Illustrator Service integrations.

---

## ⚠️ Important: HTML Content Support

**All text content fields accept inline HTML.** Content is rendered via `innerHTML`, meaning HTML tags are interpreted, not escaped.

### Fields That Accept HTML

| Field | HTML Support | Example |
|-------|--------------|---------|
| `slide_title` | ✅ Yes | `"<span style='color:#ff0000'>Red</span> Title"` |
| `subtitle` | ✅ Yes | `"Subtitle with <em>emphasis</em>"` |
| `body` | ✅ Yes | `"<ul><li>Point 1</li><li>Point 2</li></ul>"` |
| `rich_content` | ✅ Yes | Full HTML with styles |
| `hero_content` | ✅ Yes | Complete HTML document fragment |
| `contact_info` | ✅ Yes | `"<a href='mailto:...'>email</a>"` |
| `author_info` | ✅ Yes | `"John Doe <span style='opacity:0.7'>| Dec 2024</span>"` |
| `footer` | ✅ Yes | `"Company Name <span class='divider'>|</span> Page {num}"` |
| `section_number` | ✅ Yes | `"<span style='font-size:120px'>01</span>"` |

### Common HTML Patterns

```html
<!-- Styled text -->
<span style="color: #1e40af; font-weight: 600;">Highlighted Text</span>

<!-- Line breaks (recommended over \n) -->
Line 1<br>Line 2

<!-- Bullet lists -->
<ul style="list-style: disc; margin-left: 24px;">
  <li>First point</li>
  <li>Second point with <strong>emphasis</strong></li>
</ul>

<!-- Inline icons (emoji work too) -->
<span style="font-size: 1.2em;">🚀</span> Launch Status

<!-- Links (for contact_info) -->
<a href="mailto:team@company.com" style="color: #3b82f6;">team@company.com</a>
```

### Security Note

Script tags (`<script>`) are stripped during validation. Inline event handlers (`onclick`, etc.) should be avoided.

---

## Table of Contents

1. [Grid System Reference](#1-grid-system-reference)
2. [Slide Categories by Service](#2-slide-categories-by-service)
3. [Hero Slides (H-Series, L29)](#3-hero-slides-h-series-l29)
4. [Content Slides (C1, L25)](#4-content-slides-c1-l25)
5. [Image + Content (I-Series)](#5-image--content-i-series)
6. [Visual + Text (V-Series)](#6-visual--text-v-series)
7. [Chart Layouts (C3, V2, L02)](#7-chart-layouts-c3-v2-l02)
8. [Diagram Layouts (C5, V3)](#8-diagram-layouts-c5-v3)
9. [Infographic Layouts (C4, V4)](#9-infographic-layouts-c4-v4)
10. [Split Layouts (S-Series)](#10-split-layouts-s-series)
11. [X-Series Dynamic Layouts](#11-x-series-dynamic-layouts)
12. [Director Strawman Format](#12-director-strawman-format)
13. [Text Service Request Formats](#13-text-service-request-formats)
14. [Pydantic Model Reference](#14-pydantic-model-reference)
15. [Validation Rules](#15-validation-rules)

---

## 1. Grid System Reference

### Core Constants

| Property | Value |
|----------|-------|
| **Slide Resolution** | 1920 x 1080 px |
| **Grid Columns** | 32 |
| **Grid Rows** | 18 |
| **Cell Width** | 60 px |
| **Cell Height** | 60 px |

### Grid Notation

Grid positions use CSS-style `"start/end"` format (1-indexed):

```
grid_row: "4/18"     → rows 4-17 (14 rows)
grid_column: "2/32"  → cols 2-31 (30 cols)
```

### Conversion Formulas

```python
# Grid to Pixels
x = (col_start - 1) * 60
y = (row_start - 1) * 60
width = (col_end - col_start) * 60
height = (row_end - row_start) * 60

# Example: grid_row="4/18", grid_column="2/32"
x = (2 - 1) * 60 = 60px
y = (4 - 1) * 60 = 180px
width = (32 - 2) * 60 = 1800px
height = (18 - 4) * 60 = 840px
```

### Standard Content Area

Most content slides use rows 4-18, cols 2-32:

```
┌──────────────────────────────────────────┐
│  Title (rows 1-3)                        │
├──────────────────────────────────────────┤
│                                          │
│  Content Area                            │
│  rows 4-18, cols 2-32                    │
│  1800 x 840 px                           │
│                                          │
├──────────────────────────────────────────┤
│  Footer (row 18-19)                      │
└──────────────────────────────────────────┘
```

---

## 2. Slide Categories by Service

| Category | Layouts | Service Owner | Use Case |
|----------|---------|---------------|----------|
| **Hero/Title** | H1-generated, H1-structured, H2-section, H3-closing, L29 | Text Service | Title, Section, Closing slides |
| **Content** | C1-text, L25 | Text Service | Bullets, paragraphs, rich text |
| **Image+Content** | I1, I2, I3, I4, V1 | Text Service | Photo + text combinations |
| **Chart** | C3-chart, V2-chart-text, L02 | Analytics Service | Data visualization |
| **Diagram** | C5-diagram, V3-diagram-text | Diagram Service | Flowcharts, processes |
| **Infographic** | C4-infographic, V4-infographic-text | Illustrator Service | Visual summaries |
| **Split** | S3-two-visuals, S4-comparison | Multiple | Side-by-side content |
| **Dynamic** | X1-X5 | Text Service | Multi-zone layouts |
| **Blank** | B1-blank | None | Free-form canvas |

---

## 3. Hero Slides (H-Series, L29)

### H1-generated (AI-Generated Title Slide)

Full-bleed title slide where AI generates entire design.

**Grid Coordinates:**
- `hero`: rows 1-19, cols 1-33 (1920 x 1080 px - full slide)

**Input:**
```json
{
  "layout": "H1-generated",
  "content": {
    "hero_content": "<div style='width:100%; height:100%; background: linear-gradient(135deg, #1e3a5f, #3b82f6); display:flex; align-items:center; justify-content:center;'><h1 style='color:white; font-size:72px;'>Welcome</h1></div>"
  }
}
```

**Content Fields** (inside `content`):

| Field | Type | Required | Max Length | Description |
|-------|------|----------|------------|-------------|
| `hero_content` | string (HTML) | **Yes** | 100KB | Full-slide HTML with embedded styling |

> **Note:** `background_color` and `background_image` slide-level fields are **not typically needed** for H1-generated. The `hero_content` covers the entire slide (1920x1080px), so any background should be included directly in the `hero_content` HTML.

**Format Owner:** `text_service` (complete control over entire slide)

---

### H1-structured (Manual Title Slide)

Structured title slide with editable title, subtitle, and customizable background.

**Grid Coordinates:**
- `title`: rows 7-10, cols 3-17
- `subtitle`: rows 10-12, cols 3-17
- `author_info`: rows 16-18, cols 3-17
- `logo`: rows 16-18, cols 28-31
- `background`: rows 1-19, cols 1-33 (full slide)

**Input:**
```json
{
  "layout": "H1-structured",
  "content": {
    "slide_title": "Presentation Title",
    "subtitle": "Your tagline here",
    "author_info": "Author Name <span style='opacity: 0.7'>| December 2024</span>"
  },
  "background_color": "#1e3a5f",
  "background_image": "https://example.com/hero-background.jpg"
}
```

**With HTML Styling Example:**
```json
{
  "layout": "H1-structured",
  "content": {
    "slide_title": "<span style='color: #fbbf24'>Q4 2024</span> Strategy Review",
    "subtitle": "Driving Growth Through <em>Innovation</em>",
    "author_info": "Executive Team <br><span style='font-size: 0.8em; opacity: 0.7'>December 18, 2024</span>"
  },
  "background_color": "#1e3a5f",
  "background_image": "https://example.com/hero-background.jpg"
}
```

**Content Fields** (inside `content`) - All accept HTML:

| Field | Type | Required | Max Length | Description |
|-------|------|----------|------------|-------------|
| `slide_title` | string/HTML | **Yes** | 80 chars | Main presentation title |
| `subtitle` | string/HTML | No | 120 chars | Tagline or subtitle |
| `author_info` | string/HTML | No | 100 chars | Author name, date, etc. |

**Slide-Level Fields** (outside `content`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `background_color` | string (hex) | No | Default: `#1e3a5f` |
| `background_image` | string (URL) | No | Background image URL or data URI |

---

### H2-section (Section Divider)

Chapter/section break slide.

**Grid Coordinates:**
- `section_number`: rows 6-11, cols 11-17
- `title`: rows 6-11, cols 17-31
- `background`: rows 1-19, cols 1-33 (full slide)

**Input:**
```json
{
  "layout": "H2-section",
  "content": {
    "section_number": "01",
    "slide_title": "Section Title"
  },
  "background_color": "#374151",
  "background_image": "https://example.com/section-background.jpg"
}
```

**Content Fields** (inside `content`):

| Field | Type | Required | Max Length | Description |
|-------|------|----------|------------|-------------|
| `section_number` | string | No | 10 chars | Section number (e.g., "01", "#") |
| `slide_title` | string | **Yes** | 60 chars | Section title |

**Slide-Level Fields** (outside `content`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `background_color` | string (hex) | No | Default: `#374151` |
| `background_image` | string (URL) | No | Background image URL or data URI |

---

### H3-closing (Closing Slide)

Thank you / closing slide with contact info.

**Grid Coordinates:**
- `title`: rows 6-9, cols 3-31
- `subtitle`: rows 9-11, cols 5-29
- `contact_info`: rows 12-15, cols 8-26
- `logo`: rows 16-18, cols 26-32
- `background`: rows 1-19, cols 1-33

**Input:**
```json
{
  "layout": "H3-closing",
  "content": {
    "slide_title": "Thank You",
    "subtitle": "Questions & Discussion",
    "contact_info": "email@company.com | www.company.com"
  },
  "background_color": "#1e3a5f",
  "background_image": "https://example.com/closing-background.jpg"
}
```

**With HTML Styling Example:**
```json
{
  "layout": "H3-closing",
  "content": {
    "slide_title": "Thank You <span style='font-size: 0.6em'>🙏</span>",
    "subtitle": "Questions & <span style='color: #fbbf24'>Discussion</span>",
    "contact_info": "<a href='mailto:team@company.com' style='color: #93c5fd'>team@company.com</a><br><span style='opacity: 0.8'>www.company.com</span>"
  },
  "background_color": "#1e3a5f",
  "background_image": "https://example.com/closing-background.jpg"
}
```

**Content Fields** (inside `content`) - All accept HTML:

| Field | Type | Required | Max Length | Description |
|-------|------|----------|------------|-------------|
| `slide_title` | string/HTML | **Yes** | 80 chars | Closing message |
| `subtitle` | string/HTML | No | 120 chars | Additional message or CTA |
| `contact_info` | string/HTML | No | 200 chars | Contact details, website, social |

**Slide-Level Fields** (outside `content`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `background_color` | string (hex) | No | Default: `#1e3a5f` |
| `background_image` | string (URL) | No | Background image URL or data URI |

---

### L29 (Hero Full-Bleed)

Full-bleed hero layout for maximum creative impact. Text Service has complete control.

**Grid Coordinates:**
- `hero`: rows 1-19, cols 1-33 (1920 x 1080 px - entire slide)

**Input:**
```json
{
  "layout": "L29",
  "content": {
    "hero_content": "<div style='width:100%; height:100%; background:url(https://example.com/hero.jpg) center/cover; display:flex; flex-direction:column; align-items:center; justify-content:center;'><h1 style='color:white; font-size:84px; text-shadow: 2px 2px 8px rgba(0,0,0,0.5);'>Bold Statement</h1><p style='color:white; font-size:32px; opacity:0.9;'>Supporting tagline here</p></div>"
  }
}
```

**Content Fields** (inside `content`):

| Field | Type | Required | Max Length | Description |
|-------|------|----------|------------|-------------|
| `hero_content` | string (HTML) | **Yes** | 100KB | Full-slide HTML with embedded styling |

> **Note:** `background_color` and `background_image` slide-level fields are **not typically needed** for L29. The `hero_content` covers the entire slide (1920x1080px), so backgrounds, images, and gradients should be included directly in the `hero_content` HTML via inline styles.

**Format Owner:** `text_service` (complete control over entire slide)

**Use Cases:**
- Opening hero images with overlaid text
- Full-screen calls to action
- Immersive brand experiences
- Video backgrounds with text overlays

---

## 4. Content Slides (C1, L25)

### C1-text (Text Content)

Standard slide with body text (paragraphs, bullets).

**Grid Coordinates:**
- `title`: rows 1-3, cols 2-32
- `subtitle`: rows 3-4, cols 2-32
- `content`: rows 4-18, cols 2-32 (1800 x 840 px)
- `footer`: rows 18-19, cols 2-7
- `logo`: rows 17-19, cols 30-32

**Input:**
```json
{
  "layout": "C1-text",
  "content": {
    "slide_title": "Key Benefits",
    "subtitle": "Why choose our solution",
    "body": "<ul>\n  <li>Benefit one with explanation</li>\n  <li>Benefit two with details</li>\n  <li>Benefit three with impact</li>\n</ul>",
    "footer_text": "Confidential",
    "company_logo": "https://example.com/logo.png"
  },
  "background_color": "#ffffff",
  "background_image": "https://example.com/subtle-pattern.png"
}
```

**Content Fields** - All accept HTML:

| Field | Type | Required | Max Length | Description |
|-------|------|----------|------------|-------------|
| `slide_title` | string/HTML | **Yes** | 80 chars | Slide title |
| `subtitle` | string/HTML | No | 120 chars | Subtitle |
| `body` | string/HTML | **Yes** | 100KB | Main content (bullets, paragraphs) |
| `footer_text` | string/HTML | No | 50 chars | Footer text |
| `company_logo` | string (URL) | No | - | Logo image URL |

**Slide-Level Fields** (outside `content`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `background_color` | string (hex) | No | Default: `#ffffff` |
| `background_image` | string (URL) | No | Background image URL or data URI |

**Content Area:** 1800 x 840 px (30 cols x 14 rows)

---

### L25 (Main Content Shell)

Standard content slide with title, subtitle, and rich content area for Text Service.

**Grid Coordinates:**
- `title`: rows 2-3, cols 2-32
- `subtitle`: rows 3-4, cols 2-32
- `content`: rows 5-17, cols 2-32 (1800 x 720 px)
- `footer`: rows 18-19, cols 2-7
- `logo`: rows 17-19, cols 30-32

**Input:**
```json
{
  "layout": "L25",
  "content": {
    "slide_title": "Market Analysis",
    "subtitle": "Q4 2024 Results",
    "rich_content": "<div class=\"content-grid\">\n  <div class=\"metric-card\">...</div>\n</div>",
    "presentation_name": "Quarterly Review",
    "company_logo": "https://example.com/logo.png"
  },
  "background_color": "#f8fafc",
  "background_image": "https://example.com/subtle-grid.png"
}
```

**Content Fields** - All accept HTML:

| Field | Type | Required | Max Length | Description |
|-------|------|----------|------------|-------------|
| `slide_title` | string/HTML | **Yes** | 80 chars | Slide title |
| `subtitle` | string/HTML | No | 120 chars | Subtitle |
| `rich_content` | string/HTML | **Yes** | 100KB | Rich HTML content from Text Service |
| `presentation_name` | string/HTML | No | 100 chars | Footer presentation name |
| `company_logo` | string (URL/HTML) | No | - | Logo for footer |

**Slide-Level Fields** (outside `content`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `background_color` | string (hex) | No | Default: `#ffffff` |
| `background_image` | string (URL) | No | Background image URL or data URI |

**Content Area:** 1800 x 720 px (30 cols x 12 rows)
**Format Owner:** `text_service` (owns `rich_content`, full styling control)

---

## 5. Image + Content (I-Series)

> **Background Note:** I-series layouts already include prominent image slots. `background_color` is supported but `background_image` is **not recommended** as it would conflict with the layout's primary image.

### I1-image-left (Image Left Wide)

Full-height image on left (12 cols), content on right.

**Grid Coordinates:**
- `image`: rows 1-19, cols 1-12 (660 x 1080 px)
- `title`: rows 1-3, cols 12-32
- `subtitle`: rows 3-4, cols 12-32
- `content`: rows 4-18, cols 12-32 (1200 x 840 px)
- `footer`: rows 18-19, cols 12-17
- `logo`: rows 17-19, cols 30-32

**Input:**
```json
{
  "layout": "I1-image-left",
  "content": {
    "slide_title": "Our Team",
    "subtitle": "Leadership Profile",
    "image_url": "https://example.com/team-photo.jpg",
    "body": "<p>John leads our engineering team...</p>\n<ul><li>15+ years experience</li></ul>"
  },
  "background_color": "#f8fafc"
}
```

**Content Fields** - All accept HTML:

| Field | Type | Required | Max Length | Description |
|-------|------|----------|------------|-------------|
| `slide_title` | string/HTML | **Yes** | 80 chars | Slide title |
| `subtitle` | string/HTML | No | 120 chars | Subtitle |
| `image_url` | string (URL) | No | - | Image URL (placeholder if empty) |
| `body` | string/HTML | No | 100KB | Right-side content |

**Slide-Level Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `background_color` | string (hex) | No | Default: `#ffffff` |

**Image Area:** 660 x 1080 px (11 cols x 18 rows)
**Content Area:** 1200 x 840 px (20 cols x 14 rows)

---

### I2-image-right (Image Right Wide)

Full-height image on right (12 cols), content on left.

**Grid Coordinates:**
- `image`: rows 1-19, cols 21-33 (660 x 1080 px)
- `title`: rows 1-3, cols 2-21
- `subtitle`: rows 3-4, cols 2-21
- `content`: rows 4-18, cols 2-21 (1140 x 840 px)
- `footer`: rows 18-19, cols 2-7
- `logo`: rows 17-19, cols 18-20

**Input:**
```json
{
  "layout": "I2-image-right",
  "content": {
    "slide_title": "Product Showcase",
    "subtitle": "New Features",
    "image_url": "https://example.com/product.jpg",
    "body": "<ul><li>Feature highlights...</li></ul>"
  },
  "background_color": "#ffffff"
}
```

**Slide-Level Fields:** Same as I1 (`background_color` supported, `background_image` not recommended)

---

### I3-image-left-narrow (Image Left Narrow)

Full-height narrow image on left (6 cols), content on right.

**Grid Coordinates:**
- `image`: rows 1-19, cols 1-7 (360 x 1080 px)
- `title`: rows 1-3, cols 7-32
- `subtitle`: rows 3-4, cols 7-32
- `content`: rows 4-18, cols 7-32 (1500 x 840 px)
- `footer`: rows 18-19, cols 7-12
- `logo`: rows 17-19, cols 30-32

**Input:**
```json
{
  "layout": "I3-image-left-narrow",
  "content": {
    "slide_title": "Case Study",
    "subtitle": "Client Success",
    "image_url": "https://example.com/client-logo.jpg",
    "body": "<p>Detailed case study content...</p>"
  },
  "background_color": "#f9fafb"
}
```

**Slide-Level Fields:** Same as I1 (`background_color` supported, `background_image` not recommended)

**Image Area:** 360 x 1080 px (6 cols x 18 rows)
**Content Area:** 1500 x 840 px (25 cols x 14 rows)

---

### I4-image-right-narrow (Image Right Narrow)

Full-height narrow image on right (6 cols), content on left.

**Grid Coordinates:**
- `image`: rows 1-19, cols 26-33 (360 x 1080 px)
- `title`: rows 1-3, cols 2-26
- `subtitle`: rows 3-4, cols 2-26
- `content`: rows 4-18, cols 2-26 (1440 x 840 px)
- `footer`: rows 18-19, cols 2-7
- `logo`: rows 17-19, cols 23-25

**Input:**
```json
{
  "layout": "I4-image-right-narrow",
  "content": {
    "slide_title": "Partner Profile",
    "subtitle": "Strategic Alliance",
    "image_url": "https://example.com/partner-logo.jpg",
    "body": "<p>Partnership details...</p>"
  },
  "background_color": "#ffffff"
}
```

**Slide-Level Fields:** Same as I1 (`background_color` supported, `background_image` not recommended)

**Image Area:** 360 x 1080 px (7 cols x 18 rows)
**Content Area:** 1440 x 840 px (24 cols x 14 rows)

---

## 6. Visual + Text (V-Series)

### V1-image-text

Image on left, text insights on right.

**Grid Coordinates:**
- `title`: rows 1-3, cols 2-32
- `subtitle`: rows 3-4, cols 2-32
- `content_left`: rows 4-18, cols 2-20 (1080 x 840 px) - Image
- `content_right`: rows 4-18, cols 20-32 (720 x 840 px) - Text
- `footer`: rows 18-19, cols 2-7
- `logo`: rows 17-19, cols 30-32

**Input:**
```json
{
  "layout": "V1-image-text",
  "content": {
    "slide_title": "Visual Analysis",
    "subtitle": "Key Observations",
    "image_url": "https://example.com/analysis.jpg",
    "body": "<ul>\n  <li>Key insight 1</li>\n  <li>Key insight 2</li>\n</ul>"
  },
  "background_color": "#ffffff",
  "background_image": "https://example.com/subtle-pattern.png"
}
```

**Content Fields** - All accept HTML:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slide_title` | string/HTML | **Yes** | Slide title |
| `subtitle` | string/HTML | No | Subtitle |
| `image_url` | string (URL) | No | Left-side image |
| `body` | string/HTML | No | Right-side text insights |

**Slide-Level Fields** (outside `content`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `background_color` | string (hex) | No | Default: `#ffffff` |
| `background_image` | string (URL) | No | Background image URL |

---

## 7. Chart Layouts (C3, V2, L02)

> **Recommended Approach:** Use the **HTML content method** - Analytics Service generates complete HTML which is placed in `chart_html`. This is simpler and more reliable than the Chart.js configuration approach.

### C3-chart (Single Chart)

Slide with one chart visualization.

**Grid Coordinates:**
- `title`: rows 1-3, cols 2-32
- `subtitle`: rows 3-4, cols 2-32
- `content`: rows 4-18, cols 2-32 (1800 x 840 px) - Chart area
- `footer`: rows 18-19, cols 2-7
- `logo`: rows 17-19, cols 30-32

**Input:**
```json
{
  "layout": "C3-chart",
  "content": {
    "slide_title": "Revenue Growth",
    "subtitle": "FY 2024 vs FY 2023",
    "chart_html": "<div class='chart-container' style='width:100%;height:100%'><canvas id='chart1'>...</canvas></div>"
  },
  "background_color": "#ffffff",
  "background_image": "https://example.com/subtle-grid.png"
}
```

**Content Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slide_title` | string/HTML | **Yes** | Slide title (max 80 chars) |
| `subtitle` | string/HTML | No | Subtitle (max 120 chars) |
| `chart_html` | string/HTML | **Yes** | Complete HTML from Analytics Service |

**Slide-Level Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `background_color` | string (hex) | No | Default: `#ffffff` |
| `background_image` | string (URL) | No | Background image URL |

**Chart Area:** 1800 x 840 px
**Format Owner:** `analytics_service`

---

### V2-chart-text

Chart on left, text insights on right.

**Grid Coordinates:**
- `title`: rows 1-3, cols 2-32
- `subtitle`: rows 3-4, cols 2-32
- `content_left`: rows 4-18, cols 2-20 (1080 x 840 px) - Chart
- `content_right`: rows 4-18, cols 20-32 (720 x 840 px) - Text
- `footer`: rows 18-19, cols 2-7
- `logo`: rows 17-19, cols 30-32

**Input:**
```json
{
  "layout": "V2-chart-text",
  "content": {
    "slide_title": "Performance Analysis",
    "subtitle": "Q4 Metrics",
    "chart_html": "<div class='chart-container'>...</div>",
    "body": "<ul>\n  <li><strong>+25%</strong> revenue growth</li>\n  <li><strong>-10%</strong> cost reduction</li>\n</ul>"
  },
  "background_color": "#f8fafc"
}
```

**Content Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slide_title` | string/HTML | **Yes** | Slide title |
| `subtitle` | string/HTML | No | Subtitle |
| `chart_html` | string/HTML | **Yes** | Complete HTML for left chart area |
| `body` | string/HTML | No | Right-side text insights |

**Slide-Level Fields:** Same as C3-chart

**Left (Chart):** 1080 x 840 px
**Right (Text):** 720 x 840 px

---

### L02 (Left Diagram with Text Right)

Diagram/chart on left, observations/text on right. Backend layout used by Analytics Service.

**Grid Coordinates:**
- `title`: rows 2-3, cols 2-32
- `subtitle`: rows 3-4, cols 2-32
- `diagram`: rows 5-17, cols 2-23 (1260 x 720 px) - Diagram/chart area
- `text`: rows 5-17, cols 23-32 (540 x 720 px) - Text area
- `footer`: rows 18-19, cols 2-7
- `logo`: rows 17-19, cols 30-32

**Input:**
```json
{
  "layout": "L02",
  "content": {
    "slide_title": "System Architecture",
    "element_1": "Architecture Overview",
    "element_4": "<div class='diagram-container'>...</div>",
    "element_2": "<ul><li>Component A</li><li>Component B</li></ul>"
  },
  "background_color": "#ffffff"
}
```

**Slide-Level Fields:** Same as C3-chart (`background_color`, `background_image` supported)

**Format Owner (diagram slot):** `analytics_service`

---

## 8. Diagram Layouts (C5, V3)

> **Recommended Approach:** Use the **HTML content method** - Diagram Service generates complete HTML which is placed in `diagram_html`. This is simpler and more reliable than the Mermaid code approach.

### C5-diagram (Single Diagram)

Slide with one diagram.

**Grid Coordinates:**
- `title`: rows 1-3, cols 2-32
- `subtitle`: rows 3-4, cols 2-32
- `content`: rows 4-18, cols 2-32 (1800 x 840 px) - Diagram area
- `footer`: rows 18-19, cols 2-7
- `logo`: rows 17-19, cols 30-32

**Input:**
```json
{
  "layout": "C5-diagram",
  "content": {
    "slide_title": "Process Flow",
    "subtitle": "Order Fulfillment Pipeline",
    "diagram_html": "<div class='diagram-container' style='width:100%;height:100%'><svg viewBox='0 0 1800 840'>...</svg></div>"
  },
  "background_color": "#ffffff",
  "background_image": "https://example.com/subtle-pattern.png"
}
```

**Content Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slide_title` | string/HTML | **Yes** | Slide title (max 80 chars) |
| `subtitle` | string/HTML | No | Subtitle (max 120 chars) |
| `diagram_html` | string/HTML | **Yes** | Complete HTML from Diagram Service |

**Slide-Level Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `background_color` | string (hex) | No | Default: `#ffffff` |
| `background_image` | string (URL) | No | Background image URL |

**Diagram Area:** 1800 x 840 px
**Format Owner:** `diagram_service`

---

### V3-diagram-text

Diagram on left, text insights on right.

**Grid Coordinates:**
- `title`: rows 1-3, cols 2-32
- `subtitle`: rows 3-4, cols 2-32
- `content_left`: rows 4-18, cols 2-20 (1080 x 840 px) - Diagram
- `content_right`: rows 4-18, cols 20-32 (720 x 840 px) - Text
- `footer`: rows 18-19, cols 2-7
- `logo`: rows 17-19, cols 30-32

**Input:**
```json
{
  "layout": "V3-diagram-text",
  "content": {
    "slide_title": "System Architecture",
    "subtitle": "High-Level Overview",
    "diagram_html": "<div class='diagram-container'>...</div>",
    "body": "<ul>\n  <li>Frontend: React SPA</li>\n  <li>Backend: FastAPI</li>\n  <li>Database: PostgreSQL</li>\n</ul>"
  },
  "background_color": "#f8fafc"
}
```

**Content Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slide_title` | string/HTML | **Yes** | Slide title |
| `subtitle` | string/HTML | No | Subtitle |
| `diagram_html` | string/HTML | **Yes** | Complete HTML for left diagram area |
| `body` | string/HTML | No | Right-side text insights |

**Slide-Level Fields:** Same as C5-diagram

**Left (Diagram):** 1080 x 840 px
**Right (Text):** 720 x 840 px

---

## 9. Infographic Layouts (C4, V4)

> **Recommended Approach:** Use the **HTML content method** - Illustrator Service generates complete HTML which is placed in `infographic_html`. This is simpler and more reliable than complex array methods.

### C4-infographic (Single Infographic)

Slide with one infographic.

**Grid Coordinates:**
- `title`: rows 1-3, cols 2-32
- `subtitle`: rows 3-4, cols 2-32
- `content`: rows 4-18, cols 2-32 (1800 x 840 px) - Infographic area
- `footer`: rows 18-19, cols 2-7
- `logo`: rows 17-19, cols 30-32

**Input:**
```json
{
  "layout": "C4-infographic",
  "content": {
    "slide_title": "Company Timeline",
    "subtitle": "Our Journey Since 2015",
    "infographic_html": "<div class='infographic-container' style='width:100%;height:100%'>...</div>"
  },
  "background_color": "#ffffff",
  "background_image": "https://example.com/subtle-pattern.png"
}
```

**Content Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slide_title` | string/HTML | **Yes** | Slide title (max 80 chars) |
| `subtitle` | string/HTML | No | Subtitle (max 120 chars) |
| `infographic_html` | string/HTML | **Yes** | Complete HTML from Illustrator Service |

**Slide-Level Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `background_color` | string (hex) | No | Default: `#ffffff` |
| `background_image` | string (URL) | No | Background image URL |

**Infographic Area:** 1800 x 840 px
**Format Owner:** `illustrator_service`

---

### V4-infographic-text

Infographic on left, text insights on right.

**Grid Coordinates:**
- `title`: rows 1-3, cols 2-32
- `subtitle`: rows 3-4, cols 2-32
- `content_left`: rows 4-18, cols 2-20 (1080 x 840 px) - Infographic
- `content_right`: rows 4-18, cols 20-32 (720 x 840 px) - Text
- `footer`: rows 18-19, cols 2-7
- `logo`: rows 17-19, cols 30-32

**Input:**
```json
{
  "layout": "V4-infographic-text",
  "content": {
    "slide_title": "Key Metrics",
    "subtitle": "2024 Performance Summary",
    "infographic_html": "<div class='infographic-container'>...</div>",
    "body": "<ul>\n  <li><strong>$10M</strong> ARR achieved</li>\n  <li><strong>50K</strong> active users</li>\n</ul>"
  },
  "background_color": "#f8fafc"
}
```

**Content Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slide_title` | string/HTML | **Yes** | Slide title |
| `subtitle` | string/HTML | No | Subtitle |
| `infographic_html` | string/HTML | **Yes** | Complete HTML for left infographic area |
| `body` | string/HTML | No | Right-side text insights |

**Slide-Level Fields:** Same as C4-infographic

**Left (Infographic):** 1080 x 840 px
**Right (Text):** 720 x 840 px

---

## 10. Split Layouts (S-Series)

### S3-two-visuals

Two charts/diagrams/infographics side by side.

**Grid Coordinates:**
- `title`: rows 1-3, cols 2-32
- `subtitle`: rows 3-4, cols 2-32
- `content_left`: rows 4-14, cols 2-17 (900 x 600 px) - Left visual
- `content_right`: rows 4-14, cols 17-32 (900 x 600 px) - Right visual
- `caption_left`: rows 14-18, cols 2-17 - Left caption
- `caption_right`: rows 14-18, cols 17-32 - Right caption
- `footer`: rows 18-19, cols 2-7
- `logo`: rows 17-19, cols 30-32

**Input:**
```json
{
  "layout": "S3-two-visuals",
  "content": {
    "slide_title": "Comparison View",
    "subtitle": "Before vs After",
    "visual_left_html": "<div class='chart-container'>...</div>",
    "visual_right_html": "<div class='chart-container'>...</div>",
    "caption_left": "Q1 Performance",
    "caption_right": "Q4 Performance"
  },
  "background_color": "#ffffff",
  "background_image": "https://example.com/subtle-pattern.png"
}
```

**Content Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slide_title` | string/HTML | **Yes** | Slide title |
| `subtitle` | string/HTML | No | Subtitle |
| `visual_left_html` | string/HTML | **Yes** | Left visual (chart/diagram/infographic HTML) |
| `visual_right_html` | string/HTML | **Yes** | Right visual (chart/diagram/infographic HTML) |
| `caption_left` | string/HTML | No | Left caption |
| `caption_right` | string/HTML | No | Right caption |

**Slide-Level Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `background_color` | string (hex) | No | Default: `#ffffff` |
| `background_image` | string (URL) | No | Background image URL |

**Left Visual:** 900 x 600 px
**Right Visual:** 900 x 600 px
**Accepts:** `chart`, `infographic`, `diagram`, `image` (as HTML)

---

### S4-comparison

Two columns for comparing items (before/after, pros/cons).

**Grid Coordinates:**
- `title`: rows 1-3, cols 2-32
- `subtitle`: rows 3-4, cols 2-32
- `header_left`: rows 4-5, cols 2-17 - Left column header
- `header_right`: rows 4-5, cols 17-32 - Right column header
- `content_left`: rows 5-18, cols 2-17 (900 x 780 px) - Left content
- `content_right`: rows 5-18, cols 17-32 (900 x 780 px) - Right content
- `footer`: rows 18-19, cols 2-7
- `logo`: rows 17-19, cols 30-32

**Input:**
```json
{
  "layout": "S4-comparison",
  "content": {
    "slide_title": "Solution Comparison",
    "subtitle": "Option A vs Option B",
    "header_left": "Option A",
    "header_right": "Option B",
    "content_left": "<ul>\n  <li>Feature 1</li>\n  <li>Feature 2</li>\n</ul>",
    "content_right": "<ul>\n  <li>Feature 1</li>\n  <li>Feature 2</li>\n</ul>"
  },
  "background_color": "#f8fafc"
}
```

**Content Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slide_title` | string/HTML | **Yes** | Slide title |
| `subtitle` | string/HTML | No | Subtitle |
| `header_left` | string/HTML | No | Left column header |
| `header_right` | string/HTML | No | Right column header |
| `content_left` | string/HTML | **Yes** | Left column content |
| `content_right` | string/HTML | **Yes** | Right column content |

**Slide-Level Fields:** Same as S3-two-visuals

**Left Column:** 900 x 780 px
**Right Column:** 900 x 780 px
**Accepts:** `body`, `table`, `html`, `image`, `chart`

---

## 11. X-Series Dynamic Layouts

X-series layouts dynamically split the content area of base templates into sub-zones based on content analysis.

### X-Series Mapping

| X-Series | Base Layout | Content Area |
|----------|-------------|--------------|
| **X1** | C1-text | 1800 x 840 px (rows 4-18, cols 2-32) |
| **X2** | I1-image-left | 1200 x 840 px (rows 4-18, cols 12-32) |
| **X3** | I2-image-right | 1140 x 840 px (rows 4-18, cols 2-21) |
| **X4** | I3-image-left-narrow | 1500 x 840 px (rows 4-18, cols 7-32) |
| **X5** | I4-image-right-narrow | 1440 x 840 px (rows 4-18, cols 2-26) |

### Layout ID Format

```
X{series_number}-{pattern_hash}
Example: X1-a3f7e8c2
```

### Split Patterns

Common patterns available for zone splitting:

| Pattern | Zones | Description |
|---------|-------|-------------|
| `agenda-3-item` | 3 horizontal | Three equal rows |
| `agenda-4-item` | 4 horizontal | Four equal rows |
| `2col-equal` | 2 vertical | Two equal columns |
| `3col-equal` | 3 vertical | Three equal columns |
| `1-2-split` | 3 mixed | One large + two small |

**Input:**
```json
{
  "layout": "X1-a3f7e8c2",
  "base_layout": "C1-text",
  "split_pattern": "agenda-3-item",
  "content": {
    "slide_title": "Our Agenda",
    "subtitle": "Today's Discussion Topics"
  },
  "zones": [
    {
      "zone_id": "zone_1",
      "grid_row": "4/9",
      "grid_column": "2/32",
      "content_html": "<div class='agenda-item'>Topic 1: Introduction</div>"
    },
    {
      "zone_id": "zone_2",
      "grid_row": "9/14",
      "grid_column": "2/32",
      "content_html": "<div class='agenda-item'>Topic 2: Main Discussion</div>"
    },
    {
      "zone_id": "zone_3",
      "grid_row": "14/18",
      "grid_column": "2/32",
      "content_html": "<div class='agenda-item'>Topic 3: Next Steps</div>"
    }
  ]
}
```

### Get Available Patterns

```
GET /api/x-series/patterns
```

### Generate X-Series Layout

```
POST /api/x-series/generate
{
  "base_layout": "C1-text",
  "split_pattern": "agenda-3-item",
  "zone_count": 3,
  "direction": "horizontal"
}
```

---

## 12. Director Strawman Format

The Director Agent generates a "strawman" outline before content generation. Each slide in the strawman contains:

### StrawmanSlide Model

```json
{
  "slide_id": "slide_001",
  "slide_number": 1,
  "title": "Market Analysis Q4",
  "layout": "V2-chart-text",
  "topics": ["Revenue growth", "Market share", "Projections"],
  "variant_id": "metrics_3col",
  "slide_type_hint": "chart",
  "purpose": "Show quarterly performance trends",
  "service": "analytics",
  "is_hero": false,
  "hero_type": null,
  "notes": "Include year-over-year comparison",
  "content_hints": {
    "has_numbers": true,
    "is_comparison": true,
    "is_time_based": true
  }
}
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slide_id` | string | **Yes** | Unique identifier (format: `slide_{number}`) |
| `slide_number` | int | **Yes** | Position in presentation (1-indexed) |
| `title` | string | **Yes** | Topic-specific slide title |
| `layout` | string | **Yes** | Layout ID (L25, V2-chart-text, etc.) |
| `topics` | array[string] | **Yes** | 3-5 key points to cover |
| `variant_id` | string | No | Text Service variant (e.g., `metrics_3col`) |
| `slide_type_hint` | string | No | `hero`, `text`, `chart`, `diagram`, `infographic` |
| `purpose` | string | No | What story this slide tells |
| `service` | string | No | `text`, `analytics`, `diagram`, `illustrator` |
| `is_hero` | bool | No | True for title/section/closing slides |
| `hero_type` | string | No | `title_slide`, `section_divider`, `closing_slide` |
| `notes` | string | No | Generation hints/instructions |
| `content_hints` | object | No | Detected content characteristics |

### Service Routing Decision

```
┌─────────────────────────────────────────┐
│           Slide Purpose                  │
└───────────────┬─────────────────────────┘
                │
    ┌───────────┼───────────────┐
    │           │               │
    ▼           ▼               ▼
┌───────┐  ┌─────────┐    ┌──────────┐
│ Hero  │  │ Content │    │ Visual   │
└───┬───┘  └────┬────┘    └────┬─────┘
    │           │              │
    ▼           │     ┌────────┼────────┐
  Text          │     │        │        │
 Service        │     ▼        ▼        ▼
                │   Chart   Diagram  Infographic
                │     │        │        │
                │     ▼        ▼        ▼
                │  Analytics Diagram Illustrator
                │  Service   Service  Service
                │
                ▼
         ┌──────┴──────┐
         │ Has Data?   │
         └──────┬──────┘
                │
        Yes ────┴──── No
         │            │
         ▼            ▼
     Analytics    Text Service
      Service
```

---

## 13. Text Service Request Formats

### HeroGenerationRequest

For generating hero/title slides (H1-generated, L29).

```json
{
  "slide_number": 1,
  "slide_type": "title_slide",
  "narrative": "Opening presentation about AI trends in enterprise",
  "topics": ["AI", "Machine Learning", "Digital Transformation"],
  "context": {
    "theme": "corporate-blue",
    "audience": "executives",
    "presentation_title": "AI Strategy 2025"
  },
  "visual_style": "professional"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slide_number` | int | **Yes** | Position in presentation |
| `slide_type` | string | **Yes** | `title_slide`, `section_divider`, `closing_slide` |
| `narrative` | string | **Yes** | Purpose/narrative of this slide |
| `topics` | array[string] | No | Key topics (default: `[]`) |
| `context` | object | No | Presentation context |
| `context.theme` | string | No | Theme ID for styling |
| `context.audience` | string | No | Target audience |
| `context.presentation_title` | string | No | Overall presentation title |
| `visual_style` | string | No | `illustrated`, `professional`, `kids` |

**Endpoints:**
- `POST /v1.2/hero/title` - Title/opening slides
- `POST /v1.2/hero/section` - Section divider slides
- `POST /v1.2/hero/closing` - Closing slides
- `POST /v1.2/hero/title-with-image` - Title with AI background
- `POST /v1.2/hero/section-with-image` - Section with AI background
- `POST /v1.2/hero/closing-with-image` - Closing with AI background

---

### TextGenerationRequest

For generating content slides (C1, L25, I-series, V-series).

```json
{
  "presentation_id": "pres_abc123",
  "slide_id": "slide_002",
  "slide_number": 2,
  "topics": ["Point 1: Key benefit", "Point 2: Technical detail", "Point 3: Business impact"],
  "narrative": "Explaining the core benefits of our solution",
  "layout_id": "L25",
  "slide_purpose": "content",
  "constraints": {
    "max_characters": 500,
    "style": "professional",
    "tone": "informative"
  },
  "theme_config": {
    "theme_id": "corporate-blue",
    "char_multiplier": 1.0,
    "max_bullets": 5
  },
  "previous_slides_context": [
    {"slide_number": 1, "title": "Introduction", "topics": ["Overview"]}
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `presentation_id` | string | **Yes** | Unique presentation identifier |
| `slide_id` | string | **Yes** | Slide identifier |
| `slide_number` | int | **Yes** | Position in presentation |
| `topics` | array[string] | **Yes** | Key points to expand |
| `narrative` | string | No | Overall narrative context |
| `layout_id` | string | No | Target layout (L25, C1, etc.) |
| `slide_purpose` | string | No | `title_slide`, `content`, etc. |
| `constraints` | object | No | Generation constraints |
| `constraints.max_characters` | int | No | Maximum character count |
| `constraints.style` | string | No | Writing style |
| `constraints.tone` | string | No | Writing tone |
| `theme_config` | object | No | Theme configuration |
| `theme_config.theme_id` | string | No | Theme ID |
| `theme_config.char_multiplier` | float | No | Character density (0.5-1.0) |
| `theme_config.max_bullets` | int | No | Maximum bullets per section |
| `previous_slides_context` | array | No | Context from previous slides |

**Endpoint:** `POST /v1.2/generate`

---

### GridConstraints

For precise text fitting within grid-based elements.

```json
{
  "gridWidth": 30,
  "gridHeight": 14,
  "outerPadding": 10,
  "innerPadding": 16,
  "maxCharacters": 800,
  "minCharacters": 100
}
```

| Field | Type | Description |
|-------|------|-------------|
| `gridWidth` | int | Number of columns (1-32) |
| `gridHeight` | int | Number of rows (1-18) |
| `outerPadding` | int | Grid edge to element border (px) |
| `innerPadding` | int | Element border to text (px) |
| `maxCharacters` | int | Override calculated max chars |
| `minCharacters` | int | Minimum characters required |

---

## 14. Pydantic Model Reference

### Slide Model

```python
class Slide(BaseModel):
    slide_id: str = Field(default_factory=lambda: f"slide_{uuid4().hex[:12]}")
    layout: str  # REQUIRED - predefined or X-series
    content: Union[L25Content, L29Content, Dict[str, Any]]  # REQUIRED
    background_color: Optional[str] = None  # Hex format
    background_image: Optional[str] = None  # URL or data URI

    # Element arrays
    text_boxes: List[TextBox] = []      # Max 20
    images: List[ImageElement] = []      # Max 20
    charts: List[ChartElement] = []      # Max 10
    infographics: List[InfographicElement] = []  # Max 10
    diagrams: List[DiagramElement] = []  # Max 10
    contents: List[ContentElement] = []  # Max 5
```

### L25Content Model

```python
class L25Content(BaseModel):
    slide_title: str = Field(..., max_length=80)  # REQUIRED
    subtitle: Optional[str] = Field(None, max_length=120)
    rich_content: str  # REQUIRED - HTML from Text Service
    presentation_name: Optional[str] = Field(None, max_length=100)
    company_logo: Optional[str] = None  # URL or HTML
```

### L29Content Model

```python
class L29Content(BaseModel):
    hero_content: str  # REQUIRED - Full-bleed HTML
```

### TextBox Model

```python
class TextBox(BaseModel):
    id: str = Field(default_factory=lambda: f"textbox_{uuid4().hex[:8]}")
    parent_slide_id: Optional[str] = None
    position: TextBoxPosition  # REQUIRED
    z_index: int = 1000  # Range: 1-10000
    content: str = ""  # HTML content
    style: TextBoxStyle = TextBoxStyle()
    text_style: Optional[TextContentStyle] = None
    css_classes: Optional[List[str]] = None
    locked: bool = False
    visible: bool = True
```

### TextBoxPosition Model

```python
class TextBoxPosition(BaseModel):
    grid_row: str  # Format: "5/10" (1-indexed, start < end)
    grid_column: str  # Format: "3/15" (1-indexed, start < end)
```

### ImageElement Model

```python
class ImageElement(BaseModel):
    id: str = Field(default_factory=lambda: f"image_{uuid4().hex[:8]}")
    parent_slide_id: Optional[str] = None
    position: TextBoxPosition  # REQUIRED
    z_index: int = 100
    image_url: Optional[str] = None  # URL (null = placeholder)
    alt_text: Optional[str] = Field(None, max_length=500)
    object_fit: str = "cover"  # cover, contain, fill, none, scale-down
    locked: bool = False
    visible: bool = True
```

### ChartElement Model

```python
class ChartElement(BaseModel):
    id: str = Field(default_factory=lambda: f"chart_{uuid4().hex[:8]}")
    parent_slide_id: Optional[str] = None
    position: TextBoxPosition  # REQUIRED
    z_index: int = 100
    chart_type: Optional[str] = None  # bar, line, pie, doughnut, radar, scatter, bubble
    chart_config: Optional[Dict[str, Any]] = None  # Chart.js config
    chart_html: Optional[str] = None  # Pre-rendered HTML
    locked: bool = False
    visible: bool = True
```

### DiagramElement Model

```python
class DiagramElement(BaseModel):
    id: str = Field(default_factory=lambda: f"diagram_{uuid4().hex[:8]}")
    parent_slide_id: Optional[str] = None
    position: TextBoxPosition  # REQUIRED
    z_index: int = 100
    diagram_type: Optional[str] = None  # flowchart, sequence, class, state, entity, gantt, pie, mindmap
    mermaid_code: Optional[str] = None
    svg_content: Optional[str] = None  # Pre-rendered SVG
    direction: str = "TB"  # TB, LR, BT, RL
    theme: str = "default"  # default, dark, forest, neutral
    locked: bool = False
    visible: bool = True
```

### InfographicElement Model

```python
class InfographicElement(BaseModel):
    id: str = Field(default_factory=lambda: f"infographic_{uuid4().hex[:8]}")
    parent_slide_id: Optional[str] = None
    position: TextBoxPosition  # REQUIRED
    z_index: int = 100
    infographic_type: Optional[str] = None  # timeline, process, comparison, hierarchy, statistics
    svg_content: Optional[str] = None  # From Illustrator Service
    items: Optional[List[Dict[str, Any]]] = None  # Data items
    locked: bool = False
    visible: bool = True
```

---

## 15. Validation Rules

### Character Limits

| Element | Max Characters | Notes |
|---------|----------------|-------|
| `slide_title` | 80 | Plain text |
| `subtitle` | 120 | Plain text |
| `hero_content` | 100KB | HTML |
| `rich_content` | 100KB | HTML |
| `body` | 100KB | HTML |
| `alt_text` | 500 | Plain text |
| `footer_text` | 50 | Plain text |
| `contact_info` | 200 | Plain text or HTML |

### Element Limits per Slide

| Element Type | Max Count |
|--------------|-----------|
| `text_boxes` | 20 |
| `images` | 20 |
| `charts` | 10 |
| `diagrams` | 10 |
| `infographics` | 10 |
| `contents` | 5 |

### Grid Position Validation

```python
# Position format: "start/end"
# - Both values must be integers
# - start < end
# - start >= 1
# - Rows: 1-19 (18 actual rows)
# - Cols: 1-33 (32 actual cols)

# Valid examples:
"4/18"   # rows 4-17
"2/32"   # cols 2-31
"1/19"   # full height
"1/33"   # full width

# Invalid examples:
"18/4"   # start > end
"0/10"   # start < 1
"4-18"   # wrong format
```

### Background Color Validation

```python
# Must be valid hex format
# Valid: "#FF5733", "#1a1a1a", "#fff"
# Invalid: "red", "rgb(255,0,0)"
```

### Layout ID Validation

```python
# Predefined layouts:
VALID_LAYOUTS = [
    # Backend
    "L02", "L25", "L29",
    # Hero
    "H1-generated", "H1-structured", "H2-section", "H3-closing",
    # Content
    "C1-text", "C3-chart", "C4-infographic", "C5-diagram",
    # Visual
    "V1-image-text", "V2-chart-text", "V3-diagram-text", "V4-infographic-text",
    # Image
    "I1-image-left", "I2-image-right", "I3-image-left-narrow", "I4-image-right-narrow",
    # Split
    "S3-two-visuals", "S4-comparison",
    # Blank
    "B1-blank"
]

# X-series pattern: X{1-5}-{8-char-hash}
# Valid: "X1-a3f7e8c2", "X2-b4c8d9e1"
```

---

## Quick Reference Tables

### Content Area Dimensions by Layout

| Layout | Content Grid | Content Pixels | Format Owner |
|--------|--------------|----------------|--------------|
| L29, H1-generated | 1-19 / 1-33 | 1920 x 1080 | text_service |
| L25 | 5-17 / 2-32 | 1800 x 720 | text_service |
| C1, C3, C4, C5 | 4-18 / 2-32 | 1800 x 840 | varies |
| V-series (left) | 4-18 / 2-20 | 1080 x 840 | varies |
| V-series (right) | 4-18 / 20-32 | 720 x 840 | text_service |
| I1 content | 4-18 / 12-32 | 1200 x 840 | text_service |
| I2 content | 4-18 / 2-21 | 1140 x 840 | text_service |
| I3 content | 4-18 / 7-32 | 1500 x 840 | text_service |
| I4 content | 4-18 / 2-26 | 1440 x 840 | text_service |
| L02 diagram | 5-17 / 2-23 | 1260 x 720 | analytics_service |
| S3 visuals | 4-14 / 2-17, 17-32 | 900 x 600 each | varies |
| S4 columns | 5-18 / 2-17, 17-32 | 900 x 780 each | text_service |

### Service Routing by Layout

| Layout | Primary Service | Secondary Service |
|--------|----------------|-------------------|
| H1, H2, H3, L29 | Text Service | - |
| C1-text, L25 | Text Service | - |
| I1-I4, V1 | Text Service | - |
| C3-chart, V2 | Analytics Service | Text Service |
| C5-diagram, V3 | Diagram Service | Text Service |
| C4-infographic, V4 | Illustrator Service | Text Service |
| L02 | Analytics Service | Text Service |
| S3-two-visuals | Multiple | Multiple |
| S4-comparison | Text Service | - |
| X1-X5 | Text Service | - |
| B1-blank | None | - |

---

## Source Files

| File | Content |
|------|---------|
| `layout_builder_main/v7.5-main/models.py` | Pydantic models |
| `layout_builder_main/v7.5-main/src/layout_registry.py` | Grid coordinates |
| `text_table_builder/v1.2/app/models/requests.py` | Text Service models |
| `text_table_builder/v1.2/app/core/hero/base_hero_generator.py` | Hero request format |
| `director_agent/v4.0/docs/SERVICE_COORDINATION_REQUIREMENTS.md` | Orchestration flow |

---

*This document is the canonical reference for slide generation inputs. For questions or updates, consult the source files listed above.*

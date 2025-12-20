# Layout Classification by Service

**Version**: 1.1
**Last Updated**: December 2024

This document classifies all available layouts by their primary service owner for Director routing decisions.

---

## Grid System Reference

**Slide Resolution**: 1920 x 1080 pixels
**Grid**: 32 columns x 18 rows
**Cell Size**: 60px x 60px

```
Grid Notation: "start/end" (1-indexed)
Example: grid_row="4/18", grid_column="2/32"
         → rows 4-17 (14 rows), cols 2-31 (30 cols)
         → y=180px, height=840px, x=60px, width=1800px
```

**Conversion Formula**:
- `x = (col_start - 1) * 60`
- `y = (row_start - 1) * 60`
- `width = (col_end - col_start) * 60`
- `height = (row_end - row_start) * 60`

---

## Quick Reference

| Service | Layouts | Count |
|---------|---------|-------|
| **Analytics Service** | C3, V2, S3, L02 | 4 |
| **Illustrator Service** | C4, V4 | 2 |
| **Diagram Service** | C5, V3 | 2 |
| **Text Service** | H1-H3, L29, C1, L25, I1-I4, V1, S4, X1-X5 | 16+ |
| **Blank** | B1 | 1 |

**Total**: 25+ layouts (22 static + X-series dynamic)

---

## 1. Analytics Service Layouts (Charts & Data)

Layouts with dedicated chart/data visualization zones. Owned by Analytics Service.

| Layout | Content Zone Grid | Content Zone Pixels | Use Case |
|--------|-------------------|---------------------|----------|
| **C3-chart** | rows 4-18, cols 2-32 | 1800 x 840 px | Full-width chart |
| **V2-chart-text** | rows 4-18, cols 2-20 | 1080 x 840 px (chart) | Chart + insights |
| **S3-two-visuals** | rows 4-14, cols 2-17 / 17-32 | 900 x 600 px each | Side-by-side charts |
| **L02** | rows 5-17, cols 2-23 | 1260 x 720 px | Backend chart layout |

### C3-chart (Single Chart)
```
┌──────────────────────────────────────────────────────────┐
│ Title        rows 1-3, cols 2-32    (1800 x 120 px)      │
├──────────────────────────────────────────────────────────┤
│ Subtitle     rows 3-4, cols 2-32    (1800 x 60 px)       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│    CHART AREA                                            │
│    rows 4-18, cols 2-32                                  │
│    1800 x 840 px (30 cols x 14 rows)                     │
│                                                          │
├──────────────────────────────────────────────────────────┤
│ Footer (2-7) │                              │ Logo 30-32 │
└──────────────────────────────────────────────────────────┘
```

### V2-chart-text (Chart + Insights)
```
┌──────────────────────────────────────────────────────────┐
│ Title        rows 1-3, cols 2-32                         │
├──────────────────────────────────────────────────────────┤
│ Subtitle     rows 3-4, cols 2-32                         │
├────────────────────────────────┬─────────────────────────┤
│                                │                         │
│    CHART AREA                  │    TEXT AREA            │
│    rows 4-18, cols 2-20        │    rows 4-18, cols 20-32│
│    1080 x 840 px               │    720 x 840 px         │
│    (18 cols x 14 rows)         │    (12 cols x 14 rows)  │
│                                │                         │
├────────────────────────────────┴─────────────────────────┤
│ Footer                                          │ Logo   │
└──────────────────────────────────────────────────────────┘
```

### When to Route to Analytics
- Keywords: "chart", "graph", "data", "metrics", "percentage", "trend", "comparison"
- Content has numerical data or time-series
- Visualization of KPIs, sales, performance metrics

---

## 2. Illustrator/Infographic Layouts

Layouts with dedicated infographic zones. Owned by Illustrator Service.

| Layout | Content Zone Grid | Content Zone Pixels | Use Case |
|--------|-------------------|---------------------|----------|
| **C4-infographic** | rows 4-18, cols 2-32 | 1800 x 840 px | Full-width infographic |
| **V4-infographic-text** | rows 4-18, cols 2-20 | 1080 x 840 px | Infographic + explanation |

### When to Route to Illustrator
- Keywords: "infographic", "visual summary", "icon-based", "illustration"
- Content suitable for SVG templates (pyramids, cycles, funnels, matrices)
- Conceptual information better shown visually

---

## 3. Diagram Service Layouts

Layouts with dedicated diagram zones. Owned by Diagram Service.

| Layout | Content Zone Grid | Content Zone Pixels | Use Case |
|--------|-------------------|---------------------|----------|
| **C5-diagram** | rows 4-18, cols 2-32 | 1800 x 840 px | Full-width Mermaid diagram |
| **V3-diagram-text** | rows 4-18, cols 2-20 | 1080 x 840 px | Diagram + explanation |

### When to Route to Diagram Service
- Keywords: "flowchart", "process", "workflow", "architecture", "entity", "journey"
- Content describes sequences, relationships, or system components
- Suitable for Mermaid diagrams (flowchart, erDiagram, gantt, timeline, kanban)

---

## 4. Text Service Layouts

All text-centric layouts. Owned by Text Service (Elementor).

---

### 4A. Hero Layouts (Title/Section/Closing)

Full-bleed slides for presentation structure. Uses `h1` token (72px), hero colors.

| Layout | Grid | Pixels | Use Case |
|--------|------|--------|----------|
| **H1-generated** | rows 1-19, cols 1-33 | 1920 x 1080 px | AI-generated full-bleed |
| **H1-structured** | Title: rows 7-10, cols 3-17 | 840 x 180 px | Editable title slide |
| **H2-section** | Title: rows 6-11, cols 17-31 | 840 x 300 px | Section divider |
| **H3-closing** | Title: rows 6-9, cols 3-31 | 1680 x 180 px | Thank you/contact |
| **L29** | rows 1-19, cols 1-33 | 1920 x 1080 px | Backend hero template |

### H1-structured (Title Slide)
```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  BACKGROUND        rows 1-19, cols 1-33                  │
│                    1920 x 1080 px (full-bleed)           │
│                                                          │
│    ┌────────────────────────┐                            │
│    │ TITLE                  │       rows 7-10, cols 3-17 │
│    │ 840 x 180 px           │       (14 cols x 3 rows)   │
│    ├────────────────────────┤                            │
│    │ SUBTITLE               │       rows 10-12, cols 3-17│
│    │ 840 x 120 px           │       (14 cols x 2 rows)   │
│    └────────────────────────┘                            │
│                                                          │
│    AUTHOR INFO    rows 16-18, cols 3-17     │ LOGO 28-31 │
└──────────────────────────────────────────────────────────┘
```

### H2-section (Section Divider)
```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  BACKGROUND        rows 1-19, cols 1-33                  │
│                                                          │
│         ┌───────┬─────────────────────────┐              │
│         │  #    │     SECTION TITLE       │              │
│         │ 11-17 │     rows 6-11, cols 17-31              │
│         │       │     840 x 300 px        │              │
│         └───────┴─────────────────────────┘              │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

### 4B. Content Layouts (Pure Text)

Standard content slides. Uses `h2` (title), `body` (content), `h3` (subheadings) tokens.

| Layout | Content Grid | Content Pixels | Use Case |
|--------|--------------|----------------|----------|
| **C1-text** | rows 4-18, cols 2-32 | 1800 x 840 px | Paragraphs, bullets |
| **L25** | rows 5-17, cols 2-32 | 1800 x 720 px | Backend content shell |

### C1-text (Text Content)
```
┌──────────────────────────────────────────────────────────┐
│ Title        rows 1-3, cols 2-32    (1800 x 120 px)      │
├──────────────────────────────────────────────────────────┤
│ Subtitle     rows 3-4, cols 2-32    (1800 x 60 px)       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│    CONTENT AREA                                          │
│    rows 4-18, cols 2-32                                  │
│    1800 x 840 px (30 cols x 14 rows)                     │
│                                                          │
│    Accepts: body, html                                   │
│                                                          │
├──────────────────────────────────────────────────────────┤
│ Footer (2-7)                                    │ Logo   │
└──────────────────────────────────────────────────────────┘
```

### L25 (Backend Content Shell)
```
┌──────────────────────────────────────────────────────────┐
│ Title        rows 2-3, cols 2-32    (1800 x 60 px)       │
├──────────────────────────────────────────────────────────┤
│ Subtitle     rows 3-4, cols 2-32    (1800 x 60 px)       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│    CONTENT AREA                                          │
│    rows 5-17, cols 2-32                                  │
│    1800 x 720 px (30 cols x 12 rows)                     │
│                                                          │
│    format_owner: text_service                            │
│                                                          │
├──────────────────────────────────────────────────────────┤
│ Footer (2-7)                                    │ Logo   │
└──────────────────────────────────────────────────────────┘
```

---

### 4C. Image + Content Layouts (I-Series)

Slides combining image with text content.

| Layout | Image Grid | Image Pixels | Content Grid | Content Pixels |
|--------|------------|--------------|--------------|----------------|
| **I1-image-left** | rows 1-19, cols 1-12 | 660 x 1080 px | rows 4-18, cols 12-32 | 1200 x 840 px |
| **I2-image-right** | rows 1-19, cols 21-33 | 720 x 1080 px | rows 4-18, cols 2-21 | 1140 x 840 px |
| **I3-image-left-narrow** | rows 1-19, cols 1-7 | 360 x 1080 px | rows 4-18, cols 7-32 | 1500 x 840 px |
| **I4-image-right-narrow** | rows 1-19, cols 26-33 | 420 x 1080 px | rows 4-18, cols 2-26 | 1440 x 840 px |

### I1-image-left (Wide Image Left)
```
┌───────────────┬──────────────────────────────────────────┐
│               │ Title      rows 1-3, cols 12-32          │
│    IMAGE      ├──────────────────────────────────────────┤
│               │ Subtitle   rows 3-4, cols 12-32          │
│  rows 1-19    ├──────────────────────────────────────────┤
│  cols 1-12    │                                          │
│               │    CONTENT AREA                          │
│  660 x 1080   │    rows 4-18, cols 12-32                 │
│  (11 cols     │    1200 x 840 px                         │
│   x 18 rows)  │    (20 cols x 14 rows)                   │
│               │                                          │
│               ├──────────────────────────────────────────┤
│               │ Footer                          │ Logo   │
└───────────────┴──────────────────────────────────────────┘
```

### I3-image-left-narrow (Narrow Image Left)
```
┌─────────┬────────────────────────────────────────────────┐
│         │ Title      rows 1-3, cols 7-32                 │
│  IMAGE  ├────────────────────────────────────────────────┤
│         │ Subtitle   rows 3-4, cols 7-32                 │
│ rows    ├────────────────────────────────────────────────┤
│ 1-19    │                                                │
│ cols    │    CONTENT AREA                                │
│ 1-7     │    rows 4-18, cols 7-32                        │
│         │    1500 x 840 px                               │
│ 360 x   │    (25 cols x 14 rows)                         │
│ 1080    │                                                │
│         ├────────────────────────────────────────────────┤
│         │ Footer                                │ Logo   │
└─────────┴────────────────────────────────────────────────┘
```

**Use for**: Photo-driven content, product showcases, team bios, case studies.

---

### 4D. V1 Image + Text Layout

| Layout | Image Grid | Image Pixels | Text Grid | Text Pixels |
|--------|------------|--------------|-----------|-------------|
| **V1-image-text** | rows 4-18, cols 2-20 | 1080 x 840 px | rows 4-18, cols 20-32 | 720 x 840 px |

---

### 4E. S4 Comparison Layout

| Layout | Left Column Grid | Left Pixels | Right Column Grid | Right Pixels |
|--------|------------------|-------------|-------------------|--------------|
| **S4-comparison** | rows 5-18, cols 2-17 | 900 x 780 px | rows 5-18, cols 17-32 | 900 x 780 px |

### S4-comparison
```
┌──────────────────────────────────────────────────────────┐
│ Title        rows 1-3, cols 2-32                         │
├──────────────────────────────────────────────────────────┤
│ Subtitle     rows 3-4, cols 2-32                         │
├────────────────────────────┬─────────────────────────────┤
│ Header A   rows 4-5, cols 2-17 │ Header B  cols 17-32   │
├────────────────────────────┼─────────────────────────────┤
│                            │                             │
│    CONTENT LEFT            │    CONTENT RIGHT            │
│    rows 5-18, cols 2-17    │    rows 5-18, cols 17-32    │
│    900 x 780 px            │    900 x 780 px             │
│    (15 cols x 13 rows)     │    (15 cols x 13 rows)      │
│                            │                             │
├────────────────────────────┴─────────────────────────────┤
│ Footer                                          │ Logo   │
└──────────────────────────────────────────────────────────┘
```

---

### 4F. X-Series Dynamic Layouts

Dynamically generated sub-zone layouts. Built on base templates by splitting content areas.

| X-Series | Base Layout | Content Grid | Content Pixels |
|----------|-------------|--------------|----------------|
| **X1** | C1-text | rows 4-18, cols 2-32 | 1800 x 840 px |
| **X2** | I1-image-left | rows 4-18, cols 12-32 | 1200 x 840 px |
| **X3** | I2-image-right | rows 4-18, cols 2-21 | 1140 x 840 px |
| **X4** | I3-image-left-narrow | rows 4-18, cols 7-32 | 1500 x 840 px |
| **X5** | I4-image-right-narrow | rows 4-18, cols 2-26 | 1440 x 840 px |

### Split Patterns Available

| Pattern | Direction | Zones | Use Case |
|---------|-----------|-------|----------|
| `agenda-3-item` | horizontal | 3 | Agenda slides |
| `agenda-5-item` | horizontal | 5 | Detailed agenda |
| `use-case-3row` | horizontal | 3 | Problem-Solution-Benefits |
| `timeline-4row` | horizontal | 4 | Timeline/process |
| `comparison-2col` | vertical | 2 | Side-by-side comparison |
| `feature-3col` | vertical | 3 | Feature showcase |
| `grid-2x2` | grid | 4 | 2x2 quadrant |
| `grid-2x3` | grid | 6 | 2x3 grid |
| `image-split-2row` | horizontal | 2 | Image + 2 text sections |
| `image-split-3row` | horizontal | 3 | Image + 3 text sections |

### X1 with agenda-3-item Pattern
```
┌──────────────────────────────────────────────────────────┐
│ Title        rows 1-3, cols 2-32                         │
├──────────────────────────────────────────────────────────┤
│ Subtitle     rows 3-4, cols 2-32                         │
├──────────────────────────────────────────────────────────┤
│    ZONE 1 (35%)    rows 4-9, cols 2-32                   │
│    Main Goal       630 x 294 px                          │
├──────────────────────────────────────────────────────────┤
│    ZONE 2 (35%)    rows 9-14, cols 2-32                  │
│    Key Point 1     630 x 294 px                          │
├──────────────────────────────────────────────────────────┤
│    ZONE 3 (30%)    rows 14-18, cols 2-32                 │
│    Key Point 2     540 x 252 px                          │
├──────────────────────────────────────────────────────────┤
│ Footer                                          │ Logo   │
└──────────────────────────────────────────────────────────┘
```

---

## 5. Blank Layout

| Layout | Description |
|--------|-------------|
| **B1-blank** | Empty canvas - no pre-defined slots |

---

## Content Zone Summary Table

### Full-Width Layouts

| Layout | Content Grid | Content Pixels | Rows x Cols |
|--------|--------------|----------------|-------------|
| L29 (Hero) | 1-19, 1-33 | 1920 x 1080 px | 18 x 32 |
| C1, C3, C4, C5 | 4-18, 2-32 | 1800 x 840 px | 14 x 30 |
| L25 | 5-17, 2-32 | 1800 x 720 px | 12 x 30 |

### Split Layouts (Left + Right)

| Layout | Left Grid | Left Pixels | Right Grid | Right Pixels |
|--------|-----------|-------------|------------|--------------|
| V1, V2, V3, V4 | 4-18, 2-20 | 1080 x 840 px | 4-18, 20-32 | 720 x 840 px |
| S3-two-visuals | 4-14, 2-17 | 900 x 600 px | 4-14, 17-32 | 900 x 600 px |
| S4-comparison | 5-18, 2-17 | 900 x 780 px | 5-18, 17-32 | 900 x 780 px |
| L02 | 5-17, 2-23 | 1260 x 720 px | 5-17, 23-32 | 540 x 720 px |

### Image + Content Layouts

| Layout | Image Grid | Image Pixels | Content Grid | Content Pixels |
|--------|------------|--------------|--------------|----------------|
| I1-image-left | 1-19, 1-12 | 660 x 1080 px | 4-18, 12-32 | 1200 x 840 px |
| I2-image-right | 1-19, 21-33 | 720 x 1080 px | 4-18, 2-21 | 1140 x 840 px |
| I3-left-narrow | 1-19, 1-7 | 360 x 1080 px | 4-18, 7-32 | 1500 x 840 px |
| I4-right-narrow | 1-19, 26-33 | 420 x 1080 px | 4-18, 2-26 | 1440 x 840 px |

---

## Service Routing Decision Matrix

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONTENT ANALYSIS                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
    ┌────────────────────┼────────────────────┐
    │                    │                    │
    ▼                    ▼                    ▼
┌─────────┐      ┌─────────────┐      ┌─────────────┐
│ Numbers │      │   Process   │      │    Text     │
│  Data   │      │  Workflow   │      │  Bullets    │
│ Metrics │      │ Relationships│      │  Content   │
└────┬────┘      └──────┬──────┘      └──────┬──────┘
     │                  │                    │
     ▼                  ▼                    ▼
┌─────────┐      ┌─────────────┐      ┌─────────────┐
│Analytics│      │   Diagram   │      │    Text     │
│ Service │      │   Service   │      │   Service   │
└────┬────┘      └──────┬──────┘      └──────┬──────┘
     │                  │                    │
     ▼                  ▼                    ▼
  C3, V2,           C5, V3              H1-H3, L29
  S3, L02                               C1, L25
                                        I1-I4, V1
                                        S4, X1-X5
```

---

## Layout Selection by Slide Intent

| Slide Intent | Primary Layout | Content Grid | Content Pixels |
|--------------|----------------|--------------|----------------|
| **Title Slide** | H1-structured | 7-10, 3-17 | 840 x 180 px |
| **Section Divider** | H2-section | 6-11, 17-31 | 840 x 300 px |
| **Closing** | H3-closing | 6-9, 3-31 | 1680 x 180 px |
| **Bullet Points** | C1-text | 4-18, 2-32 | 1800 x 840 px |
| **Agenda (3+ items)** | X1 + agenda | 4-18, 2-32 | 1800 x 840 px |
| **Single Chart** | C3-chart | 4-18, 2-32 | 1800 x 840 px |
| **Chart + Analysis** | V2-chart-text | 4-18, 2-20 | 1080 x 840 px |
| **Two Charts** | S3-two-visuals | 4-14, 2-17 | 900 x 600 px each |
| **Process Flow** | C5-diagram | 4-18, 2-32 | 1800 x 840 px |
| **Photo + Content** | I1-image-left | 4-18, 12-32 | 1200 x 840 px |
| **Comparison** | S4-comparison | 5-18, 2-17 | 900 x 780 px each |

---

## Related Documents

| Document | Description |
|----------|-------------|
| [LAYOUT_SERVICE_CAPABILITIES.md](./LAYOUT_SERVICE_CAPABILITIES.md) | Full API documentation |
| [TEXT_SERVICE_CAPABILITIES.md](./TEXT_SERVICE_CAPABILITIES.md) | Text generation endpoints |
| [DIAGRAM_SERVICE_CAPABILITIES.md](./DIAGRAM_SERVICE_CAPABILITIES.md) | Diagram types and generation |
| [ANALYTICS_SERVICE_CAPABILITIES.md](./ANALYTICS_SERVICE_CAPABILITIES.md) | Chart generation |
| `layout_builder_main/.../THEME_SERVICE_CAPABILITIES.md` | Typography tokens |

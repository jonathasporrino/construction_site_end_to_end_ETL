---
name: pbir-editing
description: Edit Power BI reports stored as PBIP (PBIR report JSON + TMDL semantic model) with the power-viz MCP tools — read the report outline, bind fields, add or restyle visuals, add measures, validate, render pages to check the result and diff revisions. Use whenever the task touches a .pbip project, a *.Report / *.SemanticModel folder or a .pbix file.
---

# Editing Power BI reports with power_viz

You edit Power BI projects stored as files (PBIP): the report is a PBIR folder of small JSON files, the
semantic model is TMDL. The power_viz tools read, edit, validate, render and diff them offline —
no Power BI Desktop needed. Always work through the tools; they write valid PBIR, keep file layout,
resolve fields against the model and validate every change.

## 1. Concepts

**Project layout (PBIP)**
- `Sales.pbip` — entry file. `Sales.Report/` — the report (PBIR). `Sales.SemanticModel/` — the model (TMDL).
- `Sales.Report/definition/report.json` (report settings, theme), `pages/pages.json` (page order, active page),
  `pages/<page>/page.json` (one page), `pages/<page>/visuals/<visual>/visual.json` (one visual).
- Page and visual **names** are ids (folder names such as `ReportSection1a2b…` or 20 hex characters). Pages
  also have a **display name** (the tab caption). Tools accept either for pages, and a visual's id or its
  unique title for visuals.
- A `.pbix` is a zipped, read-only snapshot: convert it with `convert_pbix` before editing.
  Reports in the legacy layout (report.json / PBIR-Legacy) are read-only too: convert them with
  `legacy_to_pbir: true` (experimental) or save as PBIR in Power BI Desktop.

**Visuals**
- `visualType` (e.g. `clusteredBarChart`), a `position` (x, y, width, height, z in page pixels) and a query:
  **data roles** (field wells) such as `Category`, `Y`, `Series`, `Values`, `Rows`, `Columns`, `Tooltips`,
  each holding fields. `describe_visual_type` lists the roles of a type with their kind and limits:
  - *Grouping* roles take columns (things you group or slice by: product, store, date).
  - *Measure* roles take measures or aggregated columns (numbers: sales, count, margin).
- **Formatting objects** (`visual.objects`) are type specific: `legend`, `categoryAxis`, `valueAxis`, `labels`,
  `dataPoint`, `columnHeaders`, … (`set_formatting` target "visual").
- **Container objects** (`visualContainerObjects`) exist on every visual: `title`, `subTitle`, `background`,
  `border`, `dropShadow`, `padding`, `visualHeader` (`set_formatting` target "container").
- Visual groups hold other visuals (children are positioned relative to the group).

**Themes** — a base theme (Microsoft's, e.g. CY24SU10) plus an optional custom theme with the data colors,
background and foreground colors, text classes and visual defaults. Prefer `set_theme_colors` over coloring
visuals one by one.

**Filters** — report-, page- and visual-level filters; slicers filter the page interactively.

**Semantic model** — tables with columns (data type, format string, hidden, sort-by column), measures
(DAX with a format string and display folder), hierarchies and relationships. Report visuals bind to
model fields; local data for previews comes from the source .pbix.

## 2. Workflow

1. **Orient**: `get_report_outline` (pages, visuals, positions, bound fields). If several projects exist,
   `list_projects` and pass `project`.
2. **Find fields**: `search_fields` (fuzzy) or `list_model`. Use existing measures; check a measure's logic
   with `get_measure`; test new DAX with `evaluate_dax`.
3. **Pick visuals and roles**: `list_visual_types`, `describe_visual_type` (roles), `describe_formatting_object`
   (property names, types, enum values).
4. **Edit with tools**: `add_page`, `add_visual`, `update_visual`, `bind_fields`, `set_formatting`,
   `duplicate_visual`, `delete_visual`, `set_theme_colors`, `add_measure` / `update_measure` /
   `delete_measure`, or `apply_report_edits` for an atomic batch. Never hand-edit JSON when a tool fits; if
   nothing fits, read the file with `get_visual`, change the minimum, keep `$schema` and ids, then validate.
5. **Validate**: `validate_project` — fix every error; read warnings (fields missing from the model,
   visuals outside the page, unknown roles).
6. **Look**: `render_page` (or `render_after: true` on edit tools) and actually inspect the image: overlaps,
   alignment, empty or placeholder visuals, cut-off titles and labels, unreadable colors. `query_visual_data`
   shows the numbers behind a visual.
7. **Iterate** until the page is clean, then summarise with `diff_revisions` (base `HEAD`, head `WORKTREE`).

## 3. Field syntax

| You want | Write |
|---|---|
| a column | `Store[City]`, `'Fiscal calendar'[Month]` (quote names with spaces / symbols) |
| a measure | `[Total Sales]` (or `Sales[Total Sales]`) |
| an aggregated column | `Sum(Sales[Amount])`, `Avg(…)`, `Count(…)`, `DistinctCount(…)`, `Min(…)`, `Max(…)` |
| a hierarchy level | `Date[Fiscal Hierarchy].Fiscal Month` |
| an auto date/time level | `Sales[OrderDate].Date Hierarchy.Year` |

`search_fields` returns ready-to-use strings. Measures go into value roles (Y, Values), text and date
columns into grouping roles (Category, Rows, Legend/Series, slicer Values), numeric columns into value roles
as an aggregation.

## 4. Choosing visuals

| Question | Visual (type id) |
|---|---|
| Headline number / KPI | `cardVisual` (one or several measures; the legacy `card` is deprecated) |
| KPI vs target / trend | `kpi`, `gauge` |
| Compare categories, ranked | `clusteredBarChart` (horizontal, long labels, sort descending) |
| Few categories or time buckets | `clusteredColumnChart` |
| Trend over time | `lineChart` (dates / months on Category); `areaChart` for volume |
| Two measures, different scales, over time | `lineClusteredColumnComboChart` |
| Part of a whole (2-5 parts) | `donutChart` / `pieChart`; many parts: `treemap` or a bar chart |
| Contribution / bridge | `waterfallChart` |
| Correlation | `scatterChart` |
| Detail rows | `tableEx` (table); cross-tab with subtotals: `pivotTable` (matrix) |
| Filtering | `slicer` (list / dropdown / date range), `listSlicer`, `textSlicer` |
| Headings and notes | `textbox`; shapes: `shape`; images: `image` |
| Navigation | `actionButton`, `pageNavigator`, `bookmarkNavigator` |

Keep one message per visual, sort bars by value, avoid 3D-like clutter, and do not use pie charts with many slices.

## 5. Layout rules

- **Page size**: 1280×720 (16:9, the default) or 1920×1080 for dense pages. Keep the report's existing size.
- **Margins**: 16-24 px from the page edges (24-32 px on 1920×1080). **Gutters**: the same 16 px (or 24 px)
  between all visuals. Align edges to a grid; equal heights within a row; equal widths for repeated cards.
- **Reading order**: title / header at the top, KPI cards in a row below it, main chart(s) in the middle,
  detail table at the bottom; filters (slicers) in a consistent strip (top or left). Most important
  content top-left.
- **No overlaps** (unless intentionally layering a shape behind visuals with a lower z), nothing outside
  the page. Use `get_page` to read positions before placing, and omit x / y in `add_visual` to auto-place.
- **Sizes**: cards ≥ 200×100, charts ≥ 400×250, tables tall enough for ~8 rows; don't cram more than
  ~8 visuals on a 1280×720 page.
- Worked example (1280×720, margin 24, gutter 16): header textbox (24, 16, 1232×48); four cards at y=80,
  h=112, w=296, x = 24 / 336 / 648 / 960; two charts at y=208, h=240, w=608, x = 24 / 648; table at
  (24, 464, 1232×232). On 1920×1080 scale by 1.5.

## 6. Formatting examples

- Show a legend on top: `set_formatting` {object: "legend", properties: {show: true, position: "Top"}}.
- Data labels: {object: "labels", properties: {show: true}}.
- Title text and size: `update_visual` {title: "Sales by region"}; {object: "title", target: "container",
  properties: {fontSize: 14, bold: true}}.
- Background / border: {object: "background", properties: {show: true, color: "#FFFFFF", transparency: 0}},
  {object: "border", properties: {show: true, color: "#E1E1E1", radius: 8}}.
- Axis: {object: "valueAxis", properties: {show: true, labelDisplayUnits: 1000000}} (check enum and type
  names with `describe_formatting_object`).
- Colors are "#RRGGBB"; switches true/false; sizes numbers; enumerations exactly one of the listed values.
- Remove a property with null: {properties: {fontSize: null}}.

## 7. Measures (DAX)

- Reuse existing measures (`[Total Sales]`) instead of re-aggregating columns; build ratios from measures.
- Use `DIVIDE(numerator, denominator)` (never `/` on measures that can be 0 or blank).
- Use variables for readability: `VAR s = [Sales] VAR p = [Sales LY] RETURN DIVIDE(s - p, p)`.
- Time intelligence needs a date table: `CALCULATE([Sales], SAMEPERIODLASTYEAR('Date'[Date]))`.
- Always set a format string: `#,0`, `\$#,0.00`, `0.0%`; group measures with `display_folder`; add a
  description for non-obvious logic; put measures on the fact table they describe.
- Test first: `evaluate_dax` with `DEFINE MEASURE Sales[Test] = … EVALUATE SUMMARIZECOLUMNS(Store[Chain], "v", [Test])`.
- Renaming or deleting a measure does not update visuals; rebind them (the edit result lists them).

## 8. What NOT to do

- Do not delete or change `$schema`, and never rename page / visual ids or folders.
- Do not hand-edit JSON when a tool exists; never edit files under `.pbi/`.
- Do not edit a `.pbix` or a legacy (report.json) report — convert first.
- Do not invent field names: search the model; a field missing from the model breaks the visual.
- Do not bind columns to measure roles without an aggregation, or measures to grouping roles.
- Do not deploy (`deploy_project` with dry_run false) unless the user explicitly asked.
- Do not leave validation errors behind, and do not report success without rendering the page.

## 9. Verify

- `validate_project` — no errors.
- `render_page` — look at the image; confirm every visual shows data (no placeholder, no "approximate"
  surprises), titles are readable, the grid is consistent.
- `query_visual_data` / `evaluate_dax` — the numbers make sense.
- `diff_revisions` (base HEAD) — the change set contains only what you intended; use its markdown in
  summaries and pull requests.

## 10. Troubleshooting

- *PAGE_NOT_FOUND / VISUAL_NOT_FOUND*: take names from `get_report_outline` / `get_page`.
- *FIELD_NOT_FOUND*: `search_fields`; quote table names with spaces.
- *UNKNOWN_ROLE / UNKNOWN_FORMAT_OBJECT / UNKNOWN_FORMAT_PROPERTY*: `describe_visual_type`,
  `describe_formatting_object`.
- *REPORT_LEGACY_READONLY / PROJECT_READ_ONLY*: convert (`convert_pbix`).
- Visual renders as a placeholder or with sample values: a field is missing, the DAX uses a function the
  local engine lacks, or there is no local data — check the render notes.

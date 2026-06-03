# Categorize products and group the list by category

**Date:** 2026-06-03

## Goal

Let users assign a category when adding a product, and display the shopping
list grouped under category headings in a fixed, sensible order.

## Category set

A shared frontend constant defines the categories and their display/sort order:

1. Fruit & Vegetables
2. Dairy & Eggs
3. Meat & Fish
4. Bakery
5. Pantry
6. Frozen
7. Drinks
8. Household
9. Other

`Other` is the default and the catch-all for items whose category is null or
unrecognized.

## Scope

Frontend only. The backend already accepts and returns `category`
(`ItemCreate`/`ItemUpdate`/`ItemOut`, `ListItem.category` `String(80)` nullable).
The enum is **not** enforced server-side; the dropdown constrains input and the
grouping logic maps anything unknown to `Other`.

## Design

### New file: `frontend/src/constants/categories.js`

Exports `CATEGORIES` — the ordered array above — so the dropdown and the
grouping logic share one source of truth. Also exports `DEFAULT_CATEGORY =
'Other'`.

### Add form (`ListView.jsx`)

- Add a `category` `<select>` (`aria-label="category"`) to the "Add an item"
  row, options from `CATEGORIES`, defaulting to `DEFAULT_CATEGORY`.
- POST body becomes `{ name, quantity: quantity.trim() || undefined, category }`.
- After a successful add, reset name and quantity (as today) and reset category
  to `DEFAULT_CATEGORY`.

### Grouping helper (`frontend/src/lib/groupByCategory.js`)

A pure function `groupByCategory(items)` returning an array of
`{ category, items }` in the fixed `CATEGORIES` order:

- Items are bucketed by `category`; null/unrecognized values go to `Other`.
- Within a group, the original item order is preserved.
- Empty categories are omitted from the result.

Extracted to its own module so it can be unit-tested in isolation.

### Render (`ListView.jsx`)

- Replace the single flat `items.map(...)` with `groupByCategory(items).map(...)`,
  rendering each group as a section with a heading (the category name) followed
  by its `ItemRow`s.
- The empty-list message and the "X to gather" counter are unchanged.
- Real-time socket updates need no special handling: grouping is recomputed from
  `items` on each render.

### `ItemRow.jsx`

Unchanged. Category is conveyed by the group heading, so no per-row category
badge is added (avoids redundancy). The quantity badge stays.

## Testing

- `groupByCategory` unit tests: fixed order; uncategorized → Other; empty groups
  omitted; within-group order preserved.
- `ListView` test: selecting a category includes it in the POST body; items
  render under the correct headings.

## Out of scope

- Editing an existing item's category from the list (the schema supports it; no
  UI added here).
- Server-side validation of the category value.
- Per-user or per-household custom category sets.

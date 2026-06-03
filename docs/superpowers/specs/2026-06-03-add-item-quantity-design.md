# Add quantity when adding a product

**Date:** 2026-06-03

## Goal

Let a user set a quantity when adding an item to a shopping list.

## Scope

Frontend only. The backend already supports it end to end:

- `ItemCreate.quantity: str | None` — accepted on `POST /lists/{id}/items`.
- `ListItem.quantity` — `String(50)`, nullable, persisted.
- `ItemRow` already renders `item.quantity` as a `.qty` badge.

No backend or model changes required.

## Design

In `frontend/src/pages/ListView.jsx`:

- Add a `quantity` state alongside `name`.
- In the "Add an item" form, add a narrow free-text input
  (`aria-label="quantity"`, placeholder `"2 · 500g · 1 dozen"`) before the Add
  button. The name input keeps the `grow` class; the quantity input stays
  narrow.
- On submit, send `{ name: name.trim(), quantity: quantity.trim() || undefined }`.
  Quantity is optional: an empty value is omitted from the body (sent as
  `undefined`, not `""`).
- After a successful add, clear both `name` and `quantity`.

## Testing

Add cases to a `ListView` test:

- Typing a name and a quantity then submitting calls `api` with
  `POST /lists/{id}/items` and a body containing both `name` and `quantity`.
- Submitting with an empty quantity omits the `quantity` key from the body.

## Out of scope

- Editing the quantity of an existing item (the `ItemUpdate` schema already
  supports it, but no UI is added here).
- Validating quantity format — it is intentionally free text.

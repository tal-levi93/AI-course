# Remove member from a household (owner only)

**Date:** 2026-06-03

## Goal

Let a household owner remove another member from the household, from the
household detail page.

## Scope

Frontend only. The backend endpoint already exists:

```
DELETE /households/{household_id}/members/{user_id}   -> 204
```

It is gated by `require_owner`, returns 400 if the target is the owner, and
404 if the target is not a member. No backend changes required.

## Design

In `frontend/src/pages/HouseholdDetail.jsx`:

- Read the current user via `useAuth()`.
- Compute `isOwner = household?.owner_id === user?.id`.
- Extract a `loadMembers()` helper (mirroring the existing `loadLists()`).
- In the Members list, when `isOwner`, render a small "Remove" button next to
  each member whose `role !== 'owner'`. The owner's own row never shows a button
  (this also honors the backend's "cannot remove the owner" rule).
- On click: `window.confirm('Remove <display_name>?')`. If confirmed, call
  `api('/households/${id}/members/${m.user_id}', { method: 'DELETE' })`, then
  `loadMembers()`.
- A per-row busy flag (`removingId`) disables the button during the request to
  prevent double-clicks.
- Errors surface through the existing `setError` / `role="alert"` banner.

### Layout

Each member row is a `.between` flex row (name ↔ role badge). The badge and the
new button are grouped in a `row` container on the right so the badge stays put
and the button sits beside it.

## Testing

Add `frontend/src/__tests__/HouseholdDetail.test.jsx`:

- Mock `useAuth` to return the owner, mock `api` for the initial loads and the
  delete, and stub `window.confirm`.
- Assert the Remove button appears for a non-owner member and not for the owner.
- Click Remove, confirm the delete API is called with the right path, and assert
  the member disappears after the refresh.

## Out of scope

- A member removing themselves (leaving a household).
- Real-time broadcast of membership changes over WebSocket.

# Household Shopping Management — Design Spec

**Date:** 2026-06-03
**Status:** Approved

## Purpose

A web app for managing home shopping collaboratively. A user creates a shopping
group ("household"), invites other users (e.g. a spouse), and members share
shopping lists in real time.

## Stack

- **Backend:** Python, FastAPI, SQLAlchemy ORM, Alembic migrations, JWT auth
  (access token only), bcrypt/passlib password hashing, native WebSockets.
- **Frontend:** React + Vite, React Router, auth context, thin REST client,
  WebSocket hook.
- **Database:** SQLAlchemy against SQLite for development; connection string
  swappable to PostgreSQL with no code change.
- **Email (dev):** invite links/tokens printed to backend console; real SMTP
  wired later via config.

## Architecture

```
React (Vite)  <-- REST + WebSocket (JWT in Authorization header) -->  FastAPI
                                                                          |
                                                              SQLite (dev) / Postgres
```

- REST is the source of truth. WebSockets push deltas only.
- Backend keeps an in-memory per-household connection registry for broadcasts.

## Data Model

| Table | Key fields |
|---|---|
| **users** | id, email (unique), password_hash, display_name, created_at |
| **households** | id, name, owner_id → users, created_at |
| **memberships** | id, household_id, user_id, role (`owner`/`member`), joined_at — unique(household_id, user_id) |
| **invitations** | id, household_id, email (locked), token_hash, status (`pending`/`accepted`/`revoked`/`expired`), invited_by, expires_at, created_at, accepted_at |
| **shopping_lists** | id, household_id, name, created_by, created_at |
| **list_items** | id, list_id, name, quantity, category, note, is_checked, added_by, checked_by, created_at, updated_at |

Only a **hash** of the invite token is stored. The raw token exists only in the
link/QR/clipboard given to the invitee.

## Authentication

- Email + password, self-managed. Passwords hashed with bcrypt.
- Login issues a JWT access token (no refresh token for this project).
- FastAPI dependency resolves `current_user` from the token on protected routes.

## Invitation Flow (email-locked)

The invite is bound to a specific email address. Email, QR, and raw token are
three deliveries of **one** token.

1. Owner creates an invite for a target email. Backend generates a random token,
   stores its hash + `expires_at` (default **7 days**), and returns the raw token
   and accept URL **once**.
2. Delivery options (same token):
   - **Email:** link `https://app/accept?token=…` (dev: printed to console).
   - **QR:** frontend renders a QR encoding that accept URL.
   - **Token:** raw string the invitee pastes into an "Enter invite code" field.
3. To accept, the invitee must be **logged in with the matching email**. Backend
   verifies: token hash matches, status is `pending`, not expired, and
   `current_user.email == invitation.email`. On success it creates a `member`
   membership and marks the invite `accepted`.
4. Revoked or expired invites are rejected with a clear error.

## Roles

- **Owner** (creator): invite, revoke invites, remove members, rename/delete
  household, manage lists/items.
- **Member:** manage lists and items only; cannot change membership.
- Enforced by a FastAPI dependency that checks the caller's role for the
  household.

## Real-time Sync

- One WebSocket endpoint per household: `/ws/households/{id}`, authenticated and
  membership-checked.
- Mutations broadcast typed events (`item.added`, `item.checked`,
  `item.updated`, `item.deleted`, `list.created`, `list.deleted`, …) to all
  connected members of that household.

## API Surface

```
POST /auth/register        POST /auth/login        GET /auth/me
GET/POST /households        GET/PATCH/DELETE /households/{id}
GET /households/{id}/members          DELETE /households/{id}/members/{uid}
POST /households/{id}/invitations     GET .../invitations    DELETE .../invitations/{iid}
POST /invitations/accept              (body: token)
GET/POST /households/{id}/lists       PATCH/DELETE /lists/{id}
GET/POST /lists/{id}/items            PATCH/DELETE /items/{id}
WS   /ws/households/{id}
```

## Frontend Pages

- **Auth:** Register, Login.
- **Dashboard:** my households + create household.
- **Household detail:** members list, invite panel (email field + generated QR +
  copyable token), shopping lists.
- **List view:** items with add/check/edit/delete, live-updating via WebSocket.
- **Accept invite:** reads `?token=`, prompts login/register if needed, then
  accepts.

## Testing

- **Backend (pytest, TDD):** auth, role enforcement, full invite lifecycle
  (create → deliver → email-match accept → expiry/revoke rejection), list/item
  CRUD, WebSocket broadcast.
- **Frontend (Vitest + React Testing Library):** invite panel and list
  interaction components.

## Out of Scope (YAGNI)

- Refresh tokens / OAuth / magic links.
- Three-tier admin roles.
- Open/shareable join links (invites are strictly email-locked).
- Real email delivery in development (console only; SMTP wired later).
- Mobile native apps; price tracking; budgets; store integrations.

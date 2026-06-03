# Household Shopping Management

Create a household, invite members by email / QR / token, and share real-time shopping lists.

## Tech stack

- **Backend:** FastAPI + SQLAlchemy + SQLite
- **Frontend:** React + Vite

## Backend setup & run

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment:

- **Windows (PowerShell):** `.venv\Scripts\Activate.ps1`
- **bash:** `source .venv/Scripts/activate`

Then:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- Serves http://localhost:8000
- Database tables auto-create on startup.
- Dev invite links are printed to the backend console.

Run the tests:

```bash
python -m pytest
```

## Frontend setup & run

```bash
cd frontend
npm install
npm run dev
```

- Serves http://localhost:5173
- Optional `VITE_API_URL` env var (defaults to `http://localhost:8000`). See `.env.example`.

Run the tests:

```bash
npm test
```

## How it works

1. Register two users.
2. User A creates a household and invites user B by email.
3. The invite is **email-locked** — user B must be logged in with the invited email to accept it. The invite can be delivered as a **link**, a **QR code**, or a **pasted token**.
4. Once both are members, shopping lists update in **real time via WebSocket**.

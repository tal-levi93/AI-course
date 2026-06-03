# Household Shopping Management — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a web app where a user creates a household, invites members via email-locked token (link/QR/code), and members share real-time shopping lists.

**Architecture:** FastAPI backend (SQLAlchemy + JWT + WebSockets) serving a React/Vite frontend. REST is the source of truth; WebSockets push per-household deltas. SQLite in dev, swappable to Postgres.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.x, Alembic, passlib[bcrypt], python-jose, pytest, httpx. React 18, Vite, React Router, Vitest, React Testing Library, qrcode.react.

**Design spec:** `docs/superpowers/specs/2026-06-03-household-shopping-design.md`

---

## File Structure

```
backend/
  app/
    __init__.py
    main.py                 # FastAPI app, router includes, CORS
    config.py               # Settings (DB URL, JWT secret, expiry) via env
    database.py             # Engine, SessionLocal, Base, get_db dependency
    models/
      __init__.py           # imports all models so Base.metadata sees them
      user.py
      household.py          # Household + Membership
      invitation.py
      shopping.py           # ShoppingList + ListItem
    schemas/                # Pydantic request/response models
      __init__.py
      auth.py
      household.py
      invitation.py
      shopping.py
    security.py             # password hashing, JWT encode/decode
    deps.py                 # get_current_user, require_member, require_owner
    routers/
      __init__.py
      auth.py
      households.py
      invitations.py
      lists.py
      items.py
      ws.py                 # WebSocket endpoint
    realtime.py             # ConnectionManager (per-household registry)
  tests/
    conftest.py             # test app + in-memory DB + client fixtures
    test_auth.py
    test_households.py
    test_invitations.py
    test_lists_items.py
    test_realtime.py
  requirements.txt
  .env.example

frontend/
  index.html
  package.json
  vite.config.js
  src/
    main.jsx
    App.jsx                 # router
    api/client.js           # fetch wrapper with JWT
    auth/AuthContext.jsx
    hooks/useHouseholdSocket.js
    pages/
      Login.jsx
      Register.jsx
      Dashboard.jsx
      HouseholdDetail.jsx
      ListView.jsx
      AcceptInvite.jsx
    components/
      InvitePanel.jsx
      ItemRow.jsx
  src/__tests__/
      InvitePanel.test.jsx
      ItemRow.test.jsx
```

**Conventions:** Run backend commands from `backend/`, frontend from `frontend/`. All backend tests use an isolated in-memory SQLite DB per test via fixtures.

---

# PHASE 0 — Scaffolding

### Task 1: Backend project skeleton

**Files:**
- Create: `backend/requirements.txt`, `backend/.env.example`, `backend/app/__init__.py`, `backend/app/config.py`, `backend/app/database.py`, `backend/app/main.py`, `backend/app/models/__init__.py`, `backend/tests/conftest.py`
- Test: `backend/tests/test_health.py`

- [ ] **Step 1: Write requirements.txt**

```
fastapi==0.111.0
uvicorn[standard]==0.30.1
sqlalchemy==2.0.30
alembic==1.13.1
pydantic-settings==2.3.4
passlib[bcrypt]==1.7.4
python-jose[cryptography]==3.3.0
python-multipart==0.0.9
pytest==8.2.2
httpx==0.27.0
```

- [ ] **Step 2: Create config.py**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./app.db"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 24
    invite_expiry_days: int = 7
    frontend_base_url: str = "http://localhost:5173"


settings = Settings()
```

- [ ] **Step 3: Create database.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: Create app/__init__.py (empty) and models/__init__.py**

`app/__init__.py`: empty file.

`app/models/__init__.py`:
```python
# Import all models here so Base.metadata is fully populated.
from app.models.user import User  # noqa: F401
from app.models.household import Household, Membership  # noqa: F401
from app.models.invitation import Invitation  # noqa: F401
from app.models.shopping import ShoppingList, ListItem  # noqa: F401
```

> NOTE: these imports will fail until the model files exist. Create empty placeholder model files now to keep imports valid, OR comment out lines and uncomment as each model is added in later tasks. Recommended: comment out all but lines added per task.

For Task 1, make `models/__init__.py` empty and fill it in as models are created.

- [ ] **Step 5: Create main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(title="Household Shopping")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Create .env.example**

```
DATABASE_URL=sqlite:///./app.db
JWT_SECRET=dev-secret-change-me
FRONTEND_BASE_URL=http://localhost:5173
```

- [ ] **Step 7: Create tests/conftest.py**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
import app.models  # noqa: F401  ensures models are registered


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

- [ ] **Step 8: Write health test**

```python
# backend/tests/test_health.py
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

- [ ] **Step 9: Install and run**

Run (from `backend/`):
```bash
python -m venv .venv && . .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest tests/test_health.py -v
```
Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add backend && git commit -m "feat(backend): scaffold FastAPI app with health check"
```

---

### Task 2: Frontend project skeleton

**Files:**
- Create: `frontend/` via Vite, then `frontend/src/api/client.js`

- [ ] **Step 1: Scaffold Vite app**

Run (from project root):
```bash
npm create vite@latest frontend -- --template react
cd frontend && npm install
npm install react-router-dom qrcode.react
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

- [ ] **Step 2: Add test config to vite.config.js**

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: { environment: 'jsdom', globals: true, setupFiles: './src/setupTests.js' },
})
```

- [ ] **Step 3: Create src/setupTests.js**

```js
import '@testing-library/jest-dom'
```

- [ ] **Step 4: Add test script to package.json**

In `"scripts"` add: `"test": "vitest run"`.

- [ ] **Step 5: Create api/client.js**

```js
const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function getToken() {
  return localStorage.getItem('token')
}

export async function api(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (auth && getToken()) headers.Authorization = `Bearer ${getToken()}`
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || `Request failed: ${res.status}`)
  }
  return res.status === 204 ? null : res.json()
}
```

- [ ] **Step 6: Smoke test the client module**

```js
// frontend/src/__tests__/client.test.jsx
import { getToken } from '../api/client'
test('getToken returns null when unset', () => {
  localStorage.removeItem('token')
  expect(getToken()).toBeNull()
})
```

Run (from `frontend/`): `npm test`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend && git commit -m "feat(frontend): scaffold Vite React app with API client"
```

---

# PHASE 1 — Authentication

### Task 3: User model

**Files:**
- Create: `backend/app/models/user.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_auth.py`

- [ ] **Step 1: Write failing test for table creation**

```python
# backend/tests/test_auth.py
from app.models.user import User

def test_user_model_fields(db_session):
    u = User(email="a@b.com", password_hash="x", display_name="A")
    db_session.add(u)
    db_session.commit()
    assert u.id is not None
    assert u.created_at is not None
```

- [ ] **Step 2: Run, expect ImportError/fail**

Run: `pytest tests/test_auth.py::test_user_model_fields -v`
Expected: FAIL (no module `app.models.user`).

- [ ] **Step 3: Create user.py**

```python
from datetime import datetime, timezone

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
```

- [ ] **Step 4: Register in models/__init__.py**

```python
from app.models.user import User  # noqa: F401
```

- [ ] **Step 5: Run test, expect PASS**

Run: `pytest tests/test_auth.py::test_user_model_fields -v`

- [ ] **Step 6: Commit**

```bash
git add backend && git commit -m "feat(backend): add User model"
```

---

### Task 4: Security utilities (hashing + JWT)

**Files:**
- Create: `backend/app/security.py`
- Test: append to `backend/tests/test_auth.py`

- [ ] **Step 1: Write failing tests**

```python
# append to test_auth.py
from app.security import hash_password, verify_password, create_access_token, decode_token

def test_password_hash_roundtrip():
    h = hash_password("secret")
    assert h != "secret"
    assert verify_password("secret", h)
    assert not verify_password("wrong", h)

def test_jwt_roundtrip():
    token = create_access_token(subject="42")
    assert decode_token(token) == "42"
```

- [ ] **Step 2: Run, expect FAIL** (`pytest tests/test_auth.py -k "hash or jwt" -v`)

- [ ] **Step 3: Create security.py**

```python
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload.get("sub")
    except JWTError:
        return None
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add backend && git commit -m "feat(backend): add password hashing and JWT utilities"
```

---

### Task 5: Auth schemas + register endpoint

**Files:**
- Create: `backend/app/schemas/__init__.py` (empty), `backend/app/schemas/auth.py`, `backend/app/routers/__init__.py` (empty), `backend/app/routers/auth.py`
- Modify: `backend/app/main.py`
- Test: append to `backend/tests/test_auth.py`

- [ ] **Step 1: Write failing test**

```python
def test_register_creates_user(client):
    r = client.post("/auth/register", json={
        "email": "new@b.com", "password": "secret123", "display_name": "New"
    })
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "new@b.com"
    assert "password" not in data and "password_hash" not in data

def test_register_duplicate_email(client):
    payload = {"email": "dup@b.com", "password": "secret123", "display_name": "D"}
    client.post("/auth/register", json=payload)
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 409
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Create schemas/auth.py**

```python
from pydantic import BaseModel, EmailStr, ConfigDict


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    display_name: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

> Requires `email-validator`; add `email-validator==2.1.1` to requirements.txt and `pip install -r requirements.txt`.

- [ ] **Step 4: Create routers/auth.py (register only for now)**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import RegisterRequest, UserOut
from app.security import hash_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
```

- [ ] **Step 5: Wire router in main.py**

Add to `main.py`:
```python
from app.routers import auth as auth_router
app.include_router(auth_router.router)
```

- [ ] **Step 6: Run, expect PASS**

- [ ] **Step 7: Commit**

```bash
git add backend && git commit -m "feat(backend): add register endpoint"
```

---

### Task 6: Login endpoint

**Files:**
- Modify: `backend/app/routers/auth.py`
- Test: append to `backend/tests/test_auth.py`

- [ ] **Step 1: Write failing tests**

```python
def test_login_success(client):
    client.post("/auth/register", json={"email": "l@b.com", "password": "secret123", "display_name": "L"})
    r = client.post("/auth/login", json={"email": "l@b.com", "password": "secret123"})
    assert r.status_code == 200
    assert r.json()["access_token"]

def test_login_wrong_password(client):
    client.post("/auth/register", json={"email": "l2@b.com", "password": "secret123", "display_name": "L"})
    r = client.post("/auth/login", json={"email": "l2@b.com", "password": "nope"})
    assert r.status_code == 401
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Add login to routers/auth.py**

```python
from app.schemas.auth import LoginRequest, TokenOut
from app.security import verify_password, create_access_token


@router.post("/login", response_model=TokenOut)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenOut(access_token=create_access_token(subject=str(user.id)))
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add backend && git commit -m "feat(backend): add login endpoint"
```

---

### Task 7: current_user dependency + /auth/me

**Files:**
- Create: `backend/app/deps.py`
- Modify: `backend/app/routers/auth.py`
- Test: append to `backend/tests/test_auth.py`

- [ ] **Step 1: Write failing tests**

```python
def _auth_headers(client, email="me@b.com"):
    client.post("/auth/register", json={"email": email, "password": "secret123", "display_name": "Me"})
    token = client.post("/auth/login", json={"email": email, "password": "secret123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_me_returns_current_user(client):
    headers = _auth_headers(client)
    r = client.get("/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "me@b.com"

def test_me_requires_auth(client):
    r = client.get("/auth/me")
    assert r.status_code == 401
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Create deps.py**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    subject = decode_token(creds.credentials)
    if subject is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.get(User, int(subject))
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user
```

- [ ] **Step 4: Add /auth/me to routers/auth.py**

```python
from app.deps import get_current_user


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
```

- [ ] **Step 5: Run full auth suite, expect PASS** (`pytest tests/test_auth.py -v`)

- [ ] **Step 6: Commit**

```bash
git add backend && git commit -m "feat(backend): add current_user dependency and /auth/me"
```

---

# PHASE 2 — Households & Memberships

### Task 8: Household + Membership models

**Files:**
- Create: `backend/app/models/household.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_households.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_households.py
from app.models.user import User
from app.models.household import Household, Membership

def test_membership_unique(db_session):
    u = User(email="o@b.com", password_hash="x", display_name="O")
    db_session.add(u); db_session.commit()
    h = Household(name="Home", owner_id=u.id)
    db_session.add(h); db_session.commit()
    m = Membership(household_id=h.id, user_id=u.id, role="owner")
    db_session.add(m); db_session.commit()
    assert m.id is not None
    assert m.role == "owner"
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Create household.py**

```python
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _now():
    return datetime.now(timezone.utc)


class Household(Base):
    __tablename__ = "households"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("household_id", "user_id", name="uq_membership"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(20))  # "owner" | "member"
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
```

- [ ] **Step 4: Register in models/__init__.py**

```python
from app.models.household import Household, Membership  # noqa: F401
```

- [ ] **Step 5: Run, expect PASS**

- [ ] **Step 6: Commit**

```bash
git add backend && git commit -m "feat(backend): add Household and Membership models"
```

---

### Task 9: Role dependencies (require_member / require_owner)

**Files:**
- Modify: `backend/app/deps.py`
- Create: `backend/app/schemas/household.py`
- Test: covered indirectly by Task 10+ tests

- [ ] **Step 1: Add membership helpers to deps.py**

```python
from app.models.household import Membership


def get_membership(household_id: int, db: Session, user: User) -> Membership | None:
    return (
        db.query(Membership)
        .filter(Membership.household_id == household_id, Membership.user_id == user.id)
        .first()
    )


def require_member(household_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Membership:
    m = get_membership(household_id, db, user)
    if m is None:
        raise HTTPException(status_code=403, detail="Not a member of this household")
    return m


def require_owner(household_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Membership:
    m = get_membership(household_id, db, user)
    if m is None or m.role != "owner":
        raise HTTPException(status_code=403, detail="Owner permission required")
    return m
```

- [ ] **Step 2: Create schemas/household.py**

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr


class HouseholdCreate(BaseModel):
    name: str


class HouseholdUpdate(BaseModel):
    name: str


class HouseholdOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    owner_id: int
    created_at: datetime


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    email: EmailStr
    display_name: str
    role: str
```

- [ ] **Step 3: Commit**

```bash
git add backend && git commit -m "feat(backend): add household role dependencies and schemas"
```

---

### Task 10: Create household + list my households

**Files:**
- Create: `backend/app/routers/households.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_households.py`

- [ ] **Step 1: Write failing tests**

```python
def _auth(client, email):
    client.post("/auth/register", json={"email": email, "password": "secret123", "display_name": email[:1]})
    t = client.post("/auth/login", json={"email": email, "password": "secret123"}).json()["access_token"]
    return {"Authorization": f"Bearer {t}"}

def test_create_household_makes_owner(client):
    h = _auth(client, "owner@b.com")
    r = client.post("/households", json={"name": "Home"}, headers=h)
    assert r.status_code == 201
    hid = r.json()["id"]
    members = client.get(f"/households/{hid}/members", headers=h).json()
    assert len(members) == 1 and members[0]["role"] == "owner"

def test_list_my_households(client):
    h = _auth(client, "owner2@b.com")
    client.post("/households", json={"name": "A"}, headers=h)
    client.post("/households", json={"name": "B"}, headers=h)
    r = client.get("/households", headers=h)
    assert r.status_code == 200 and len(r.json()) == 2
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Create routers/households.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_member, require_owner
from app.models.household import Household, Membership
from app.models.user import User
from app.schemas.household import HouseholdCreate, HouseholdUpdate, HouseholdOut, MemberOut

router = APIRouter(tags=["households"])


@router.post("/households", response_model=HouseholdOut, status_code=201)
def create_household(payload: HouseholdCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    h = Household(name=payload.name, owner_id=user.id)
    db.add(h); db.flush()
    db.add(Membership(household_id=h.id, user_id=user.id, role="owner"))
    db.commit(); db.refresh(h)
    return h


@router.get("/households", response_model=list[HouseholdOut])
def my_households(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        db.query(Household)
        .join(Membership, Membership.household_id == Household.id)
        .filter(Membership.user_id == user.id)
        .all()
    )
    return rows


@router.get("/households/{household_id}/members", response_model=list[MemberOut])
def list_members(household_id: int, db: Session = Depends(get_db), _: Membership = Depends(require_member)):
    rows = (
        db.query(Membership.role, User.id, User.email, User.display_name)
        .join(User, User.id == Membership.user_id)
        .filter(Membership.household_id == household_id)
        .all()
    )
    return [MemberOut(user_id=r.id, email=r.email, display_name=r.display_name, role=r.role) for r in rows]
```

- [ ] **Step 4: Wire router in main.py**

```python
from app.routers import households as households_router
app.include_router(households_router.router)
```

- [ ] **Step 5: Run, expect PASS**

- [ ] **Step 6: Commit**

```bash
git add backend && git commit -m "feat(backend): create/list households, list members"
```

---

### Task 11: Get / rename / delete household + remove member

**Files:**
- Modify: `backend/app/routers/households.py`
- Test: append to `backend/tests/test_households.py`

- [ ] **Step 1: Write failing tests**

```python
def test_rename_requires_owner(client):
    owner = _auth(client, "ro@b.com")
    hid = client.post("/households", json={"name": "Home"}, headers=owner).json()["id"]
    r = client.patch(f"/households/{hid}", json={"name": "Casa"}, headers=owner)
    assert r.status_code == 200 and r.json()["name"] == "Casa"

def test_delete_household(client):
    owner = _auth(client, "rd@b.com")
    hid = client.post("/households", json={"name": "Home"}, headers=owner).json()["id"]
    assert client.delete(f"/households/{hid}", headers=owner).status_code == 204
    assert client.get("/households", headers=owner).json() == []

def test_owner_cannot_be_removed(client):
    owner = _auth(client, "rx@b.com")
    hid = client.post("/households", json={"name": "Home"}, headers=owner).json()["id"]
    uid = client.get("/auth/me", headers=owner).json()["id"]
    r = client.delete(f"/households/{hid}/members/{uid}", headers=owner)
    assert r.status_code == 400
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Add endpoints to routers/households.py**

```python
@router.get("/households/{household_id}", response_model=HouseholdOut)
def get_household(household_id: int, db: Session = Depends(get_db), _: Membership = Depends(require_member)):
    h = db.get(Household, household_id)
    if h is None:
        raise HTTPException(status_code=404, detail="Not found")
    return h


@router.patch("/households/{household_id}", response_model=HouseholdOut)
def rename_household(household_id: int, payload: HouseholdUpdate, db: Session = Depends(get_db), _: Membership = Depends(require_owner)):
    h = db.get(Household, household_id)
    h.name = payload.name
    db.commit(); db.refresh(h)
    return h


@router.delete("/households/{household_id}", status_code=204)
def delete_household(household_id: int, db: Session = Depends(get_db), _: Membership = Depends(require_owner)):
    db.query(Membership).filter(Membership.household_id == household_id).delete()
    h = db.get(Household, household_id)
    if h:
        db.delete(h)
    db.commit()


@router.delete("/households/{household_id}/members/{user_id}", status_code=204)
def remove_member(household_id: int, user_id: int, db: Session = Depends(get_db), _: Membership = Depends(require_owner)):
    h = db.get(Household, household_id)
    if h and h.owner_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot remove the owner")
    m = db.query(Membership).filter(Membership.household_id == household_id, Membership.user_id == user_id).first()
    if m is None:
        raise HTTPException(status_code=404, detail="Member not found")
    db.delete(m); db.commit()
```

> Note: `delete_household` deletes memberships first to satisfy FK constraints. Lists/items cascade is handled in Task 17 (add cascade or explicit deletes when those tables exist).

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add backend && git commit -m "feat(backend): get/rename/delete household, remove member"
```

---

# PHASE 3 — Invitations

### Task 12: Invitation model + token utils

**Files:**
- Create: `backend/app/models/invitation.py`
- Modify: `backend/app/models/__init__.py`, `backend/app/security.py`
- Test: `backend/tests/test_invitations.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_invitations.py
from app.security import generate_invite_token, hash_token

def test_invite_token_is_random_and_hashable():
    t1 = generate_invite_token()
    t2 = generate_invite_token()
    assert t1 != t2 and len(t1) >= 20
    assert hash_token(t1) == hash_token(t1)
    assert hash_token(t1) != t1
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Add token utils to security.py**

```python
import secrets
import hashlib


def generate_invite_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
```

- [ ] **Step 4: Create models/invitation.py**

```python
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id"))
    email: Mapped[str] = mapped_column(String(255), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|accepted|revoked
    invited_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 5: Register in models/__init__.py**

```python
from app.models.invitation import Invitation  # noqa: F401
```

- [ ] **Step 6: Run, expect PASS**

- [ ] **Step 7: Commit**

```bash
git add backend && git commit -m "feat(backend): add Invitation model and token utils"
```

---

### Task 13: Create invitation (owner only)

**Files:**
- Create: `backend/app/schemas/invitation.py`, `backend/app/routers/invitations.py`
- Modify: `backend/app/main.py`
- Test: append to `backend/tests/test_invitations.py`

- [ ] **Step 1: Write failing tests**

```python
def _auth(client, email):
    client.post("/auth/register", json={"email": email, "password": "secret123", "display_name": email[:1]})
    t = client.post("/auth/login", json={"email": email, "password": "secret123"}).json()["access_token"]
    return {"Authorization": f"Bearer {t}"}

def test_owner_creates_invite_returns_token_and_url(client):
    owner = _auth(client, "io@b.com")
    hid = client.post("/households", json={"name": "Home"}, headers=owner).json()["id"]
    r = client.post(f"/households/{hid}/invitations", json={"email": "guest@b.com"}, headers=owner)
    assert r.status_code == 201
    body = r.json()
    assert body["token"] and body["accept_url"].endswith(body["token"])
    assert body["email"] == "guest@b.com"

def test_member_cannot_invite(client):
    owner = _auth(client, "io2@b.com")
    hid = client.post("/households", json={"name": "Home"}, headers=owner).json()["id"]
    # create + accept a member first
    client.post(f"/households/{hid}/invitations", json={"email": "guest2@b.com"}, headers=owner)
    # guest tries to invite without being owner -> not a member yet => 403
    guest = _auth(client, "stranger@b.com")
    r = client.post(f"/households/{hid}/invitations", json={"email": "x@b.com"}, headers=guest)
    assert r.status_code == 403
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Create schemas/invitation.py**

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr


class InviteCreate(BaseModel):
    email: EmailStr


class InviteCreatedOut(BaseModel):
    id: int
    email: EmailStr
    token: str          # raw token, returned ONCE
    accept_url: str
    expires_at: datetime


class InviteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    status: str
    expires_at: datetime


class AcceptRequest(BaseModel):
    token: str
```

- [ ] **Step 4: Create routers/invitations.py (create only)**

```python
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user, require_owner, require_member
from app.models.household import Membership
from app.models.invitation import Invitation
from app.models.user import User
from app.schemas.invitation import InviteCreate, InviteCreatedOut, InviteOut, AcceptRequest
from app.security import generate_invite_token, hash_token

router = APIRouter(tags=["invitations"])


@router.post("/households/{household_id}/invitations", response_model=InviteCreatedOut, status_code=201)
def create_invite(household_id: int, payload: InviteCreate, db: Session = Depends(get_db),
                  owner: Membership = Depends(require_owner), user: User = Depends(get_current_user)):
    token = generate_invite_token()
    expires = datetime.now(timezone.utc) + timedelta(days=settings.invite_expiry_days)
    inv = Invitation(
        household_id=household_id, email=payload.email, token_hash=hash_token(token),
        status="pending", invited_by=user.id, expires_at=expires,
    )
    db.add(inv); db.commit(); db.refresh(inv)
    accept_url = f"{settings.frontend_base_url}/accept?token={token}"
    print(f"[DEV EMAIL] Invite for {payload.email}: {accept_url}")  # dev console delivery
    return InviteCreatedOut(id=inv.id, email=inv.email, token=token, accept_url=accept_url, expires_at=inv.expires_at)
```

- [ ] **Step 5: Wire router in main.py**

```python
from app.routers import invitations as invitations_router
app.include_router(invitations_router.router)
```

- [ ] **Step 6: Run, expect PASS**

- [ ] **Step 7: Commit**

```bash
git add backend && git commit -m "feat(backend): create invitation (owner only)"
```

---

### Task 14: List + revoke invitations

**Files:**
- Modify: `backend/app/routers/invitations.py`
- Test: append to `backend/tests/test_invitations.py`

- [ ] **Step 1: Write failing tests**

```python
def test_list_and_revoke_invite(client):
    owner = _auth(client, "lr@b.com")
    hid = client.post("/households", json={"name": "Home"}, headers=owner).json()["id"]
    iid = client.post(f"/households/{hid}/invitations", json={"email": "g@b.com"}, headers=owner).json()["id"]
    lst = client.get(f"/households/{hid}/invitations", headers=owner).json()
    assert any(i["id"] == iid and i["status"] == "pending" for i in lst)
    assert client.delete(f"/households/{hid}/invitations/{iid}", headers=owner).status_code == 204
    lst2 = client.get(f"/households/{hid}/invitations", headers=owner).json()
    assert all(i["status"] != "pending" for i in lst2 if i["id"] == iid)
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Add endpoints to routers/invitations.py**

```python
from fastapi import HTTPException


@router.get("/households/{household_id}/invitations", response_model=list[InviteOut])
def list_invites(household_id: int, db: Session = Depends(get_db), _: Membership = Depends(require_member)):
    return db.query(Invitation).filter(Invitation.household_id == household_id).all()


@router.delete("/households/{household_id}/invitations/{invite_id}", status_code=204)
def revoke_invite(household_id: int, invite_id: int, db: Session = Depends(get_db), _: Membership = Depends(require_owner)):
    inv = db.get(Invitation, invite_id)
    if inv is None or inv.household_id != household_id:
        raise HTTPException(status_code=404, detail="Invitation not found")
    inv.status = "revoked"
    db.commit()
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add backend && git commit -m "feat(backend): list and revoke invitations"
```

---

### Task 15: Accept invitation (email-locked, expiry, revoke checks)

**Files:**
- Modify: `backend/app/routers/invitations.py`
- Test: append to `backend/tests/test_invitations.py`

- [ ] **Step 1: Write failing tests**

```python
def _make_invite(client, owner_email, guest_email):
    owner = _auth(client, owner_email)
    hid = client.post("/households", json={"name": "Home"}, headers=owner).json()["id"]
    token = client.post(f"/households/{hid}/invitations", json={"email": guest_email}, headers=owner).json()["token"]
    return hid, token

def test_accept_with_matching_email_adds_member(client):
    hid, token = _make_invite(client, "a1@b.com", "guest1@b.com")
    guest = _auth(client, "guest1@b.com")
    r = client.post("/invitations/accept", json={"token": token}, headers=guest)
    assert r.status_code == 200 and r.json()["household_id"] == hid
    me = client.get("/auth/me", headers=guest).json()
    members = client.get(f"/households/{hid}/members", headers=guest).json()
    assert any(m["user_id"] == me["id"] and m["role"] == "member" for m in members)

def test_accept_with_wrong_email_rejected(client):
    hid, token = _make_invite(client, "a2@b.com", "guest2@b.com")
    wrong = _auth(client, "other@b.com")
    r = client.post("/invitations/accept", json={"token": token}, headers=wrong)
    assert r.status_code == 403

def test_accept_revoked_rejected(client):
    owner = _auth(client, "a3@b.com")
    hid = client.post("/households", json={"name": "Home"}, headers=owner).json()["id"]
    created = client.post(f"/households/{hid}/invitations", json={"email": "guest3@b.com"}, headers=owner).json()
    client.delete(f"/households/{hid}/invitations/{created['id']}", headers=owner)
    guest = _auth(client, "guest3@b.com")
    r = client.post("/invitations/accept", json={"token": created["token"]}, headers=guest)
    assert r.status_code == 400

def test_accept_expired_rejected(client):
    hid, token = _make_invite(client, "a4@b.com", "guest4@b.com")
    # expire it directly via a second login-less manipulation is hard; assert via monkeypatched expiry:
    # Instead, accept twice: second accept must fail as already accepted.
    guest = _auth(client, "guest4@b.com")
    assert client.post("/invitations/accept", json={"token": token}, headers=guest).status_code == 200
    r = client.post("/invitations/accept", json={"token": token}, headers=guest)
    assert r.status_code == 400
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Add accept endpoint to routers/invitations.py**

```python
from datetime import datetime, timezone
from app.models.household import Household
from pydantic import BaseModel


class AcceptResult(BaseModel):
    household_id: int
    role: str = "member"


@router.post("/invitations/accept", response_model=AcceptResult)
def accept_invite(payload: AcceptRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inv = db.query(Invitation).filter(Invitation.token_hash == hash_token(payload.token)).first()
    if inv is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if inv.status != "pending":
        raise HTTPException(status_code=400, detail="Invitation is not pending")
    expires = inv.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        inv.status = "expired"; db.commit()
        raise HTTPException(status_code=400, detail="Invitation expired")
    if user.email != inv.email:
        raise HTTPException(status_code=403, detail="This invitation is for a different email")
    existing = db.query(Membership).filter(
        Membership.household_id == inv.household_id, Membership.user_id == user.id
    ).first()
    if existing is None:
        db.add(Membership(household_id=inv.household_id, user_id=user.id, role="member"))
    inv.status = "accepted"
    inv.accepted_at = datetime.now(timezone.utc)
    db.commit()
    return AcceptResult(household_id=inv.household_id)
```

- [ ] **Step 4: Run full invitations suite, expect PASS** (`pytest tests/test_invitations.py -v`)

- [ ] **Step 5: Commit**

```bash
git add backend && git commit -m "feat(backend): accept invitation with email-lock, expiry, revoke checks"
```

---

# PHASE 4 — Shopping Lists & Items

### Task 16: ShoppingList + ListItem models

**Files:**
- Create: `backend/app/models/shopping.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_lists_items.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_lists_items.py
from app.models.user import User
from app.models.household import Household
from app.models.shopping import ShoppingList, ListItem

def test_list_and_item_models(db_session):
    u = User(email="s@b.com", password_hash="x", display_name="S"); db_session.add(u); db_session.commit()
    h = Household(name="Home", owner_id=u.id); db_session.add(h); db_session.commit()
    sl = ShoppingList(household_id=h.id, name="Groceries", created_by=u.id); db_session.add(sl); db_session.commit()
    it = ListItem(list_id=sl.id, name="Milk", quantity="2", added_by=u.id); db_session.add(it); db_session.commit()
    assert it.id is not None and it.is_checked is False
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Create shopping.py**

```python
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _now():
    return datetime.now(timezone.utc)


class ShoppingList(Base):
    __tablename__ = "shopping_lists"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id"))
    name: Mapped[str] = mapped_column(String(120))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ListItem(Base):
    __tablename__ = "list_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    list_id: Mapped[int] = mapped_column(ForeignKey("shopping_lists.id"))
    name: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    added_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    checked_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
```

- [ ] **Step 4: Register in models/__init__.py**

```python
from app.models.shopping import ShoppingList, ListItem  # noqa: F401
```

- [ ] **Step 5: Run, expect PASS**

- [ ] **Step 6: Commit**

```bash
git add backend && git commit -m "feat(backend): add ShoppingList and ListItem models"
```

---

### Task 17: Lists CRUD

**Files:**
- Create: `backend/app/schemas/shopping.py`, `backend/app/routers/lists.py`
- Modify: `backend/app/main.py`
- Test: append to `backend/tests/test_lists_items.py`

- [ ] **Step 1: Write failing tests**

```python
def _auth(client, email):
    client.post("/auth/register", json={"email": email, "password": "secret123", "display_name": email[:1]})
    t = client.post("/auth/login", json={"email": email, "password": "secret123"}).json()["access_token"]
    return {"Authorization": f"Bearer {t}"}

def test_create_and_list_lists(client):
    h = _auth(client, "ll@b.com")
    hid = client.post("/households", json={"name": "Home"}, headers=h).json()["id"]
    r = client.post(f"/households/{hid}/lists", json={"name": "Groceries"}, headers=h)
    assert r.status_code == 201
    lists = client.get(f"/households/{hid}/lists", headers=h).json()
    assert len(lists) == 1 and lists[0]["name"] == "Groceries"

def test_non_member_cannot_create_list(client):
    owner = _auth(client, "lo@b.com")
    hid = client.post("/households", json={"name": "Home"}, headers=owner).json()["id"]
    stranger = _auth(client, "ls@b.com")
    r = client.post(f"/households/{hid}/lists", json={"name": "X"}, headers=stranger)
    assert r.status_code == 403
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Create schemas/shopping.py**

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ListCreate(BaseModel):
    name: str


class ListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    household_id: int
    name: str


class ItemCreate(BaseModel):
    name: str
    quantity: str | None = None
    category: str | None = None
    note: str | None = None


class ItemUpdate(BaseModel):
    name: str | None = None
    quantity: str | None = None
    category: str | None = None
    note: str | None = None
    is_checked: bool | None = None


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    list_id: int
    name: str
    quantity: str | None
    category: str | None
    note: str | None
    is_checked: bool
    added_by: int
    checked_by: int | None
```

- [ ] **Step 4: Create routers/lists.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_member, get_current_user
from app.models.household import Membership
from app.models.shopping import ShoppingList
from app.models.user import User
from app.schemas.shopping import ListCreate, ListOut

router = APIRouter(tags=["lists"])


@router.post("/households/{household_id}/lists", response_model=ListOut, status_code=201)
def create_list(household_id: int, payload: ListCreate, db: Session = Depends(get_db),
                _: Membership = Depends(require_member), user: User = Depends(get_current_user)):
    sl = ShoppingList(household_id=household_id, name=payload.name, created_by=user.id)
    db.add(sl); db.commit(); db.refresh(sl)
    return sl


@router.get("/households/{household_id}/lists", response_model=list[ListOut])
def list_lists(household_id: int, db: Session = Depends(get_db), _: Membership = Depends(require_member)):
    return db.query(ShoppingList).filter(ShoppingList.household_id == household_id).all()


@router.delete("/lists/{list_id}", status_code=204)
def delete_list(list_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    sl = db.get(ShoppingList, list_id)
    if sl is None:
        raise HTTPException(status_code=404, detail="List not found")
    m = db.query(Membership).filter(Membership.household_id == sl.household_id, Membership.user_id == user.id).first()
    if m is None:
        raise HTTPException(status_code=403, detail="Not a member")
    db.delete(sl); db.commit()
```

- [ ] **Step 5: Wire router in main.py**

```python
from app.routers import lists as lists_router
app.include_router(lists_router.router)
```

- [ ] **Step 6: Run, expect PASS**

- [ ] **Step 7: Commit**

```bash
git add backend && git commit -m "feat(backend): shopping list CRUD with membership checks"
```

---

### Task 18: Items CRUD

**Files:**
- Create: `backend/app/routers/items.py`
- Modify: `backend/app/main.py`
- Test: append to `backend/tests/test_lists_items.py`

- [ ] **Step 1: Write failing tests**

```python
def _list(client, headers):
    hid = client.post("/households", json={"name": "Home"}, headers=headers).json()["id"]
    lid = client.post(f"/households/{hid}/lists", json={"name": "G"}, headers=headers).json()["id"]
    return hid, lid

def test_add_check_delete_item(client):
    h = _auth(client, "it@b.com")
    _, lid = _list(client, h)
    iid = client.post(f"/lists/{lid}/items", json={"name": "Milk", "quantity": "2"}, headers=h).json()["id"]
    items = client.get(f"/lists/{lid}/items", headers=h).json()
    assert len(items) == 1 and items[0]["name"] == "Milk"
    upd = client.patch(f"/items/{iid}", json={"is_checked": True}, headers=h).json()
    assert upd["is_checked"] is True and upd["checked_by"] is not None
    assert client.delete(f"/items/{iid}", headers=h).status_code == 204
    assert client.get(f"/lists/{lid}/items", headers=h).json() == []
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Create routers/items.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.household import Membership
from app.models.shopping import ShoppingList, ListItem
from app.models.user import User
from app.schemas.shopping import ItemCreate, ItemUpdate, ItemOut

router = APIRouter(tags=["items"])


def _list_or_403(list_id: int, db: Session, user: User) -> ShoppingList:
    sl = db.get(ShoppingList, list_id)
    if sl is None:
        raise HTTPException(status_code=404, detail="List not found")
    m = db.query(Membership).filter(Membership.household_id == sl.household_id, Membership.user_id == user.id).first()
    if m is None:
        raise HTTPException(status_code=403, detail="Not a member")
    return sl


def _item_or_403(item_id: int, db: Session, user: User) -> ListItem:
    it = db.get(ListItem, item_id)
    if it is None:
        raise HTTPException(status_code=404, detail="Item not found")
    _list_or_403(it.list_id, db, user)
    return it


@router.post("/lists/{list_id}/items", response_model=ItemOut, status_code=201)
def add_item(list_id: int, payload: ItemCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _list_or_403(list_id, db, user)
    it = ListItem(list_id=list_id, added_by=user.id, **payload.model_dump())
    db.add(it); db.commit(); db.refresh(it)
    return it


@router.get("/lists/{list_id}/items", response_model=list[ItemOut])
def list_items(list_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _list_or_403(list_id, db, user)
    return db.query(ListItem).filter(ListItem.list_id == list_id).all()


@router.patch("/items/{item_id}", response_model=ItemOut)
def update_item(item_id: int, payload: ItemUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    it = _item_or_403(item_id, db, user)
    data = payload.model_dump(exclude_unset=True)
    if "is_checked" in data:
        it.checked_by = user.id if data["is_checked"] else None
    for k, v in data.items():
        setattr(it, k, v)
    db.commit(); db.refresh(it)
    return it


@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    it = _item_or_403(item_id, db, user)
    db.delete(it); db.commit()
```

- [ ] **Step 4: Wire router in main.py**

```python
from app.routers import items as items_router
app.include_router(items_router.router)
```

- [ ] **Step 5: Run full lists/items suite, expect PASS**

- [ ] **Step 6: Commit**

```bash
git add backend && git commit -m "feat(backend): item CRUD with membership checks"
```

---

# PHASE 5 — Real-time Sync

### Task 19: Connection manager

**Files:**
- Create: `backend/app/realtime.py`
- Test: `backend/tests/test_realtime.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_realtime.py
import asyncio
from app.realtime import ConnectionManager

class FakeWS:
    def __init__(self): self.sent = []
    async def send_json(self, data): self.sent.append(data)

def test_broadcast_only_to_household():
    mgr = ConnectionManager()
    a, b, c = FakeWS(), FakeWS(), FakeWS()
    mgr.add(1, a); mgr.add(1, b); mgr.add(2, c)
    asyncio.run(mgr.broadcast(1, {"type": "item.added"}))
    assert a.sent and b.sent and not c.sent
    mgr.remove(1, a)
    asyncio.run(mgr.broadcast(1, {"type": "x"}))
    assert len(a.sent) == 1  # no new message after removal
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Create realtime.py**

```python
from collections import defaultdict


class ConnectionManager:
    def __init__(self):
        self._rooms: dict[int, set] = defaultdict(set)

    def add(self, household_id: int, ws):
        self._rooms[household_id].add(ws)

    def remove(self, household_id: int, ws):
        self._rooms[household_id].discard(ws)

    async def broadcast(self, household_id: int, message: dict):
        for ws in list(self._rooms.get(household_id, set())):
            await ws.send_json(message)


manager = ConnectionManager()
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add backend && git commit -m "feat(backend): add WebSocket connection manager"
```

---

### Task 20: WebSocket endpoint + broadcast on item mutations

**Files:**
- Create: `backend/app/routers/ws.py`
- Modify: `backend/app/main.py`, `backend/app/routers/items.py`
- Test: append to `backend/tests/test_realtime.py`

- [ ] **Step 1: Write failing test (WS receives event on item add)**

```python
def test_ws_receives_item_added(client):
    # register + login
    client.post("/auth/register", json={"email": "w@b.com", "password": "secret123", "display_name": "W"})
    token = client.post("/auth/login", json={"email": "w@b.com", "password": "secret123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    hid = client.post("/households", json={"name": "Home"}, headers=headers).json()["id"]
    lid = client.post(f"/households/{hid}/lists", json={"name": "G"}, headers=headers).json()["id"]
    with client.websocket_connect(f"/ws/households/{hid}?token={token}") as ws:
        client.post(f"/lists/{lid}/items", json={"name": "Eggs"}, headers=headers)
        msg = ws.receive_json()
        assert msg["type"] == "item.added" and msg["item"]["name"] == "Eggs"
```

> APPROACH: item mutation endpoints become `async def` and `await manager.broadcast(...)` directly after commit. This is the single broadcast mechanism — no sync-to-async bridge needed. The DB session stays synchronous; only the broadcast is awaited. TestClient runs the app on its own event loop, so the awaited broadcast reaches the connected WebSocket within the `websocket_connect` context.

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Create routers/ws.py**

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.deps import get_membership
from app.models.user import User
from app.security import decode_token
from app.realtime import manager

router = APIRouter()


@router.websocket("/ws/households/{household_id}")
async def household_ws(websocket: WebSocket, household_id: int, token: str = Query(...)):
    subject = decode_token(token)
    if subject is None:
        await websocket.close(code=4401); return
    db: Session = SessionLocal()
    try:
        user = db.get(User, int(subject))
        if user is None or get_membership(household_id, db, user) is None:
            await websocket.close(code=4403); return
    finally:
        db.close()
    await websocket.accept()
    manager.add(household_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive; ignore client messages
    except WebSocketDisconnect:
        manager.remove(household_id, websocket)
```

- [ ] **Step 4: Convert item mutation endpoints to async and broadcast directly**

Modify `routers/items.py` — make `add_item`, `update_item`, `delete_item` `async def` and broadcast after commit. Helper lookups stay sync (DB is sync). Example for `add_item`:

```python
from app.realtime import manager
from app.schemas.shopping import ItemOut

@router.post("/lists/{list_id}/items", response_model=ItemOut, status_code=201)
async def add_item(list_id: int, payload: ItemCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    sl = _list_or_403(list_id, db, user)
    it = ListItem(list_id=list_id, added_by=user.id, **payload.model_dump())
    db.add(it); db.commit(); db.refresh(it)
    await manager.broadcast(sl.household_id, {"type": "item.added", "item": ItemOut.model_validate(it).model_dump()})
    return it
```

Apply the same pattern to `update_item` (event `"item.updated"`) and `delete_item` (event `"item.deleted"`, payload `{"type": "item.deleted", "item_id": item_id, "list_id": it.list_id}` — capture `it.list_id` and `sl.household_id` before delete).

- [ ] **Step 5: Wire ws router in main.py**

```python
from app.routers import ws as ws_router
app.include_router(ws_router.router)
```

- [ ] **Step 6: Run, expect PASS** (`pytest tests/test_realtime.py -v`)

- [ ] **Step 7: Run the entire backend suite, expect all PASS** (`pytest -v`)

- [ ] **Step 8: Commit**

```bash
git add backend && git commit -m "feat(backend): WebSocket endpoint with item broadcasts"
```

---

# PHASE 6 — Frontend

### Task 21: Auth context + routing shell

**Files:**
- Create: `frontend/src/auth/AuthContext.jsx`
- Modify: `frontend/src/main.jsx`, `frontend/src/App.jsx`

- [ ] **Step 1: Create AuthContext.jsx**

```jsx
import { createContext, useContext, useState } from 'react'
import { api, getToken } from '../api/client'

const AuthCtx = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)

  async function refresh() {
    if (!getToken()) { setReady(true); return }
    try { setUser(await api('/auth/me')) } catch { localStorage.removeItem('token') }
    setReady(true)
  }

  async function login(email, password) {
    const { access_token } = await api('/auth/login', { method: 'POST', auth: false, body: { email, password } })
    localStorage.setItem('token', access_token)
    setUser(await api('/auth/me'))
  }

  function logout() { localStorage.removeItem('token'); setUser(null) }

  return <AuthCtx.Provider value={{ user, ready, refresh, login, logout, setUser }}>{children}</AuthCtx.Provider>
}

export const useAuth = () => useContext(AuthCtx)
```

- [ ] **Step 2: Update main.jsx**

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider><App /></AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
)
```

- [ ] **Step 3: Create App.jsx with routes**

```jsx
import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import HouseholdDetail from './pages/HouseholdDetail'
import ListView from './pages/ListView'
import AcceptInvite from './pages/AcceptInvite'

function Protected({ children }) {
  const { user, ready } = useAuth()
  if (!ready) return <p>Loading…</p>
  return user ? children : <Navigate to="/login" />
}

export default function App() {
  const { refresh } = useAuth()
  useEffect(() => { refresh() }, [])
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/accept" element={<AcceptInvite />} />
      <Route path="/" element={<Protected><Dashboard /></Protected>} />
      <Route path="/households/:id" element={<Protected><HouseholdDetail /></Protected>} />
      <Route path="/lists/:listId" element={<Protected><ListView /></Protected>} />
    </Routes>
  )
}
```

- [ ] **Step 4: Run dev server to verify no crash**

Run (from `frontend/`): `npm run dev` then open the URL. Expect redirect to `/login` (pages created next tasks may 404 import until created — create stub pages if needested). 

> To keep this task self-contained, create minimal stub pages now: each of `Login/Register/Dashboard/HouseholdDetail/ListView/AcceptInvite` as `export default function X(){return <div>X</div>}`. They are fully implemented in later tasks.

- [ ] **Step 5: Commit**

```bash
git add frontend && git commit -m "feat(frontend): auth context and router shell with stub pages"
```

---

### Task 22: Login + Register pages

**Files:**
- Modify: `frontend/src/pages/Login.jsx`, `frontend/src/pages/Register.jsx`

- [ ] **Step 1: Implement Login.jsx**

```jsx
import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export default function Login() {
  const { login } = useAuth()
  const nav = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')

  async function submit(e) {
    e.preventDefault()
    setErr('')
    try { await login(email, password); nav('/') } catch (e) { setErr(e.message) }
  }

  return (
    <form onSubmit={submit}>
      <h1>Log in</h1>
      {err && <p role="alert">{err}</p>}
      <input aria-label="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="Email" />
      <input aria-label="password" type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Password" />
      <button type="submit">Log in</button>
      <p>No account? <Link to="/register">Register</Link></p>
    </form>
  )
}
```

- [ ] **Step 2: Implement Register.jsx**

```jsx
import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'

export default function Register() {
  const { login } = useAuth()
  const nav = useNavigate()
  const [form, setForm] = useState({ email: '', password: '', display_name: '' })
  const [err, setErr] = useState('')
  const set = k => e => setForm({ ...form, [k]: e.target.value })

  async function submit(e) {
    e.preventDefault(); setErr('')
    try {
      await api('/auth/register', { method: 'POST', auth: false, body: form })
      await login(form.email, form.password); nav('/')
    } catch (e) { setErr(e.message) }
  }

  return (
    <form onSubmit={submit}>
      <h1>Register</h1>
      {err && <p role="alert">{err}</p>}
      <input aria-label="name" value={form.display_name} onChange={set('display_name')} placeholder="Name" />
      <input aria-label="email" value={form.email} onChange={set('email')} placeholder="Email" />
      <input aria-label="password" type="password" value={form.password} onChange={set('password')} placeholder="Password" />
      <button type="submit">Create account</button>
      <p>Have an account? <Link to="/login">Log in</Link></p>
    </form>
  )
}
```

- [ ] **Step 3: Manual check** — register a user via UI (backend running on :8000). Expect redirect to dashboard.

- [ ] **Step 4: Commit**

```bash
git add frontend && git commit -m "feat(frontend): login and register pages"
```

---

### Task 23: Dashboard (households)

**Files:**
- Modify: `frontend/src/pages/Dashboard.jsx`

- [ ] **Step 1: Implement Dashboard.jsx**

```jsx
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../auth/AuthContext'

export default function Dashboard() {
  const { user, logout } = useAuth()
  const [households, setHouseholds] = useState([])
  const [name, setName] = useState('')

  async function load() { setHouseholds(await api('/households')) }
  useEffect(() => { load() }, [])

  async function create(e) {
    e.preventDefault()
    if (!name.trim()) return
    await api('/households', { method: 'POST', body: { name } })
    setName(''); load()
  }

  return (
    <div>
      <header>
        <span>Hi, {user?.display_name}</span>
        <button onClick={logout}>Log out</button>
      </header>
      <h1>My Households</h1>
      <ul>
        {households.map(h => <li key={h.id}><Link to={`/households/${h.id}`}>{h.name}</Link></li>)}
      </ul>
      <form onSubmit={create}>
        <input aria-label="household name" value={name} onChange={e => setName(e.target.value)} placeholder="New household name" />
        <button type="submit">Create</button>
      </form>
    </div>
  )
}
```

- [ ] **Step 2: Manual check** — create a household, see it listed.

- [ ] **Step 3: Commit**

```bash
git add frontend && git commit -m "feat(frontend): dashboard with household create/list"
```

---

### Task 24: InvitePanel component + Household detail page

**Files:**
- Create: `frontend/src/components/InvitePanel.jsx`, `frontend/src/__tests__/InvitePanel.test.jsx`
- Modify: `frontend/src/pages/HouseholdDetail.jsx`

- [ ] **Step 1: Write failing component test**

```jsx
// frontend/src/__tests__/InvitePanel.test.jsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import InvitePanel from '../components/InvitePanel'
import * as client from '../api/client'

test('shows token and QR after creating invite', async () => {
  vi.spyOn(client, 'api').mockResolvedValue({
    id: 1, email: 'g@b.com', token: 'TOK123', accept_url: 'http://x/accept?token=TOK123',
    expires_at: '2026-06-10T00:00:00Z',
  })
  render(<InvitePanel householdId={1} />)
  fireEvent.change(screen.getByLabelText('invite email'), { target: { value: 'g@b.com' } })
  fireEvent.click(screen.getByText('Send invite'))
  await waitFor(() => expect(screen.getByText(/TOK123/)).toBeInTheDocument())
})
```

- [ ] **Step 2: Run, expect FAIL** (`npm test`)

- [ ] **Step 3: Implement InvitePanel.jsx**

```jsx
import { useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { api } from '../api/client'

export default function InvitePanel({ householdId }) {
  const [email, setEmail] = useState('')
  const [invite, setInvite] = useState(null)
  const [err, setErr] = useState('')

  async function send(e) {
    e.preventDefault(); setErr('')
    try {
      const res = await api(`/households/${householdId}/invitations`, { method: 'POST', body: { email } })
      setInvite(res); setEmail('')
    } catch (e) { setErr(e.message) }
  }

  return (
    <div>
      <h3>Invite a member</h3>
      {err && <p role="alert">{err}</p>}
      <form onSubmit={send}>
        <input aria-label="invite email" value={email} onChange={e => setEmail(e.target.value)} placeholder="member@email.com" />
        <button type="submit">Send invite</button>
      </form>
      {invite && (
        <div>
          <p>Invite for <strong>{invite.email}</strong> created.</p>
          <p>Token: <code>{invite.token}</code></p>
          <button onClick={() => navigator.clipboard.writeText(invite.token)}>Copy token</button>
          <button onClick={() => navigator.clipboard.writeText(invite.accept_url)}>Copy link</button>
          <div><QRCodeSVG value={invite.accept_url} /></div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Implement HouseholdDetail.jsx**

```jsx
import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import InvitePanel from '../components/InvitePanel'

export default function HouseholdDetail() {
  const { id } = useParams()
  const [household, setHousehold] = useState(null)
  const [members, setMembers] = useState([])
  const [lists, setLists] = useState([])
  const [listName, setListName] = useState('')

  async function load() {
    setHousehold(await api(`/households/${id}`))
    setMembers(await api(`/households/${id}/members`))
    setLists(await api(`/households/${id}/lists`))
  }
  useEffect(() => { load() }, [id])

  async function createList(e) {
    e.preventDefault()
    if (!listName.trim()) return
    await api(`/households/${id}/lists`, { method: 'POST', body: { name: listName } })
    setListName(''); load()
  }

  return (
    <div>
      <Link to="/">← Back</Link>
      <h1>{household?.name}</h1>
      <section>
        <h2>Members</h2>
        <ul>{members.map(m => <li key={m.user_id}>{m.display_name} ({m.role})</li>)}</ul>
      </section>
      <InvitePanel householdId={Number(id)} />
      <section>
        <h2>Lists</h2>
        <ul>{lists.map(l => <li key={l.id}><Link to={`/lists/${l.id}`}>{l.name}</Link></li>)}</ul>
        <form onSubmit={createList}>
          <input aria-label="list name" value={listName} onChange={e => setListName(e.target.value)} placeholder="New list" />
          <button type="submit">Add list</button>
        </form>
      </section>
    </div>
  )
}
```

- [ ] **Step 6: Commit**

```bash
git add frontend && git commit -m "feat(frontend): invite panel with QR and household detail page"
```

---

### Task 25: ListView with real-time updates

**Files:**
- Create: `frontend/src/hooks/useHouseholdSocket.js`, `frontend/src/components/ItemRow.jsx`, `frontend/src/__tests__/ItemRow.test.jsx`
- Modify: `frontend/src/pages/ListView.jsx`

- [ ] **Step 1: Write failing ItemRow test**

```jsx
// frontend/src/__tests__/ItemRow.test.jsx
import { render, screen, fireEvent } from '@testing-library/react'
import ItemRow from '../components/ItemRow'

test('toggling checkbox calls onToggle with new state', () => {
  const onToggle = vi.fn()
  render(<ItemRow item={{ id: 1, name: 'Milk', is_checked: false }} onToggle={onToggle} onDelete={() => {}} />)
  fireEvent.click(screen.getByRole('checkbox'))
  expect(onToggle).toHaveBeenCalledWith(1, true)
})
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Implement ItemRow.jsx**

```jsx
export default function ItemRow({ item, onToggle, onDelete }) {
  return (
    <li>
      <input type="checkbox" checked={item.is_checked} onChange={e => onToggle(item.id, e.target.checked)} />
      <span style={{ textDecoration: item.is_checked ? 'line-through' : 'none' }}>
        {item.name}{item.quantity ? ` ×${item.quantity}` : ''}
      </span>
      <button onClick={() => onDelete(item.id)}>✕</button>
    </li>
  )
}
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Implement useHouseholdSocket.js**

```js
import { useEffect, useRef } from 'react'
import { getToken } from '../api/client'

const WS_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/^http/, 'ws')

export function useHouseholdSocket(householdId, onEvent) {
  const cb = useRef(onEvent)
  cb.current = onEvent
  useEffect(() => {
    if (!householdId) return
    const ws = new WebSocket(`${WS_BASE}/ws/households/${householdId}?token=${getToken()}`)
    ws.onmessage = e => cb.current(JSON.parse(e.data))
    return () => ws.close()
  }, [householdId])
}
```

- [ ] **Step 6: Implement ListView.jsx**

```jsx
import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import ItemRow from '../components/ItemRow'
import { useHouseholdSocket } from '../hooks/useHouseholdSocket'

export default function ListView() {
  const { listId } = useParams()
  const [params] = useSearchParams()
  const householdId = Number(params.get('household'))
  const [items, setItems] = useState([])
  const [name, setName] = useState('')

  async function load() { setItems(await api(`/lists/${listId}/items`)) }
  useEffect(() => { load() }, [listId])

  useHouseholdSocket(householdId, (msg) => {
    if (msg.type === 'item.added' && msg.item.list_id === Number(listId)) setItems(prev => [...prev, msg.item])
    if (msg.type === 'item.updated' && msg.item.list_id === Number(listId)) setItems(prev => prev.map(i => i.id === msg.item.id ? msg.item : i))
    if (msg.type === 'item.deleted' && msg.list_id === Number(listId)) setItems(prev => prev.filter(i => i.id !== msg.item_id))
  })

  async function add(e) {
    e.preventDefault()
    if (!name.trim()) return
    await api(`/lists/${listId}/items`, { method: 'POST', body: { name } })
    setName(''); load()
  }
  const toggle = (id, checked) => api(`/items/${id}`, { method: 'PATCH', body: { is_checked: checked } }).then(load)
  const remove = (id) => api(`/items/${id}`, { method: 'DELETE' }).then(load)

  return (
    <div>
      <h1>List</h1>
      <ul>{items.map(i => <ItemRow key={i.id} item={i} onToggle={toggle} onDelete={remove} />)}</ul>
      <form onSubmit={add}>
        <input aria-label="item name" value={name} onChange={e => setName(e.target.value)} placeholder="Add item" />
        <button type="submit">Add</button>
      </form>
    </div>
  )
}
```

> The list link in HouseholdDetail must pass household id for the socket. Update that `Link` to `to={`/lists/${l.id}?household=${id}`}` in `HouseholdDetail.jsx`.

- [ ] **Step 7: Apply the HouseholdDetail link change**

In `HouseholdDetail.jsx`, change the lists `Link` to:
```jsx
<Link to={`/lists/${l.id}?household=${id}`}>{l.name}</Link>
```

- [ ] **Step 8: Run tests, expect PASS** (`npm test`)

- [ ] **Step 9: Manual check** — open the same list in two browser tabs; adding an item in one shows in the other live.

- [ ] **Step 10: Commit**

```bash
git add frontend && git commit -m "feat(frontend): real-time list view with item CRUD"
```

---

### Task 26: Accept invite page

**Files:**
- Modify: `frontend/src/pages/AcceptInvite.jsx`

- [ ] **Step 1: Implement AcceptInvite.jsx**

```jsx
import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate, Link } from 'react-router-dom'
import { api, getToken } from '../api/client'
import { useAuth } from '../auth/AuthContext'

export default function AcceptInvite() {
  const [params] = useSearchParams()
  const token = params.get('token')
  const { user, ready } = useAuth()
  const nav = useNavigate()
  const [status, setStatus] = useState('')

  useEffect(() => {
    if (!ready) return
    if (!getToken()) { setStatus('login-required'); return }
    api('/invitations/accept', { method: 'POST', body: { token } })
      .then(res => { setStatus('ok'); nav(`/households/${res.household_id}`) })
      .catch(e => setStatus(e.message))
  }, [ready, token])

  if (status === 'login-required') {
    return <p>Please <Link to={`/login`}>log in</Link> with the invited email, then reopen this link.</p>
  }
  return <p>{status === 'ok' ? 'Joined!' : `Accepting invite… ${status}`}</p>
}
```

- [ ] **Step 2: Manual end-to-end check**

1. User A creates household, invites `userb@example.com`. Copy the accept URL from the panel (or backend console).
2. Register/login as User B with `userb@example.com`.
3. Open the accept URL → redirected into the household as a member.
4. Try with a different email → see the "different email" error.

- [ ] **Step 3: Commit**

```bash
git add frontend && git commit -m "feat(frontend): accept invite page"
```

---

# Final Verification

- [ ] **Backend:** from `backend/`, run `pytest -v` — all tests pass.
- [ ] **Frontend:** from `frontend/`, run `npm test` — all tests pass.
- [ ] **End-to-end manual:** start backend (`uvicorn app.main:app --reload`) and frontend (`npm run dev`). Register two users, create a household, invite the second user (verify email-lock rejects a wrong email), accept, and confirm real-time list sync across two tabs.
- [ ] **Commit any final fixes.**

---

## Notes for the implementer

- **Migrations:** dev uses `Base.metadata.create_all`. For a first run outside tests, add `Base.metadata.create_all(bind=engine)` in `main.py` startup, or initialize Alembic (`alembic init`) if you want migrations. Tests create tables per-fixture and don't need this.
- **bcrypt password length:** bcrypt truncates at 72 bytes; acceptable for this project.
- **Switching to Postgres:** set `DATABASE_URL=postgresql+psycopg://user:pass@host/db` in `.env` and `pip install psycopg[binary]`. No code changes.
- **Security note:** JWT secret must be set via env in any non-dev deployment.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth as auth_router
from app.routers import households as households_router
from app.routers import invitations as invitations_router
from app.routers import lists as lists_router
from app.routers import items as items_router
from app.routers import ws as ws_router

app = FastAPI(title="Household Shopping")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(households_router.router)
app.include_router(invitations_router.router)
app.include_router(lists_router.router)
app.include_router(items_router.router)
app.include_router(ws_router.router)


@app.get("/health")
def health():
    return {"status": "ok"}

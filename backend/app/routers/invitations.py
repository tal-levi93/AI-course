from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user, require_owner, require_member
from app.models.household import Membership
from app.models.invitation import Invitation
from app.models.user import User
from app.schemas.invitation import InviteCreate, InviteCreatedOut, InviteOut, AcceptRequest, AcceptResult
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


@router.post("/invitations/accept", response_model=AcceptResult)
def accept_invite(payload: AcceptRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    inv = db.query(Invitation).filter(Invitation.token_hash == hash_token(payload.token)).first()
    if inv is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if inv.status != "pending":
        raise HTTPException(status_code=400, detail="Invitation is not pending")
    expires = inv.expires_at
    # SQLite stores naive datetimes (drops tzinfo); values were written as UTC, so re-attach it.
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

import base64
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, Request
from fastapi.responses import Response, RedirectResponse
from sqlalchemy.orm import Session

from autoscan.shared.db.database import get_db
from autoscan.shared.db.models import Email, EmailEvent

app = FastAPI(title="AutoScan Email Tracker")

# 1x1 transparent PNG pixel base64 encoded
TRANSPARENT_PIXEL = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")

@app.get("/track/open/{email_id}")
def track_open(email_id: int, request: Request, db: Session = Depends(get_db)):
    email = db.query(Email).filter(Email.id == email_id).first()
    if email:
        if not email.opened_at:
            email.opened_at = datetime.now(timezone.utc)
            
        event = EmailEvent(
            email_id=email.id,
            event_type="open",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        db.add(event)
        try:
            db.commit()
        except Exception:
            db.rollback()

    return Response(content=TRANSPARENT_PIXEL, media_type="image/png")

@app.get("/track/click/{email_id}")
def track_click(email_id: int, target_url: str, request: Request, db: Session = Depends(get_db)):
    email = db.query(Email).filter(Email.id == email_id).first()
    if email:
        if not email.clicked_at:
            email.clicked_at = datetime.now(timezone.utc)
            
        event = EmailEvent(
            email_id=email.id,
            event_type="click",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        db.add(event)
        try:
            db.commit()
        except Exception:
            db.rollback()

    if not target_url.startswith("http"):
        target_url = "https://" + target_url

    return RedirectResponse(url=target_url)

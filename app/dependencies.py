# app/dependencies.py

from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .database import SessionLocal
from . import auth, models
from jose.exceptions import JWTError

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    request: Request,
    db:      Session = Depends(get_db)
) -> models.User | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = auth.decode_token(token)
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        return None
    user = db.query(models.User).get(user_id)
    return user

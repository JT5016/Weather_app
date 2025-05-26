# app/auth.py

from passlib.context import CryptContext
from jose import jwt, JWTError
import datetime, os
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY     = os.getenv("SECRET_KEY", "dev_key")
ALGORITHM      = "HS256"
ACCESS_TTL     = 60  # minutes

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_pw(pw: str) -> str:
    return pwd_ctx.hash(pw)

def verify_pw(pw: str, hashed: str) -> bool:
    return pwd_ctx.verify(pw, hashed)

def create_token(sub: str) -> str:
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TTL)
    to_encode = {"sub": sub, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    """
    Decode a JWT previously created with create_token().
    Raises JWTError if token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        # bubble up so callers know to treat it as “not logged in”
        raise e

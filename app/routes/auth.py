from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer

from datetime import timedelta
from typing import Any, Optional
from app.routes.dependencies import get_db
from app.services.auth import authenticate_user, create_access_token, get_password_hash

# Secret key to encode JWT
SECRET_KEY = "1234"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10000

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter()

class User(BaseModel):
    email: str

class UserCreate(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


@router.post("/register")
async def register(user: UserCreate, db: Any = Depends(get_db)):
    if len(user.email) == 0 or len(user.password) == 0:
        raise HTTPException(status_code=400, detail="Invalid email and password")
    user_in_db = db.users.find_one({"email": user.email})
    if user_in_db:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user.password)
    res = db.users.insert_one({"email": user.email, "hashed_password": hashed_password})

    return {"id": str(res.inserted_id), "email": user.email}


@router.post("/login")
async def login(user: UserCreate, db: Any = Depends(get_db)):
    user_in_db = authenticate_user(db, user.email, user.password)
    if not user_in_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_in_db["email"]}, 
        expires_delta=access_token_expires,
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "id": user_in_db["_id"],
    }


@router.get("/me/", response_model=User)
async def read_users_me(
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="login")),
    db: Any = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception

    user = db.users.find_one({"email": token_data.email})
    if user is None:
        raise credentials_exception
    return {"email": user["email"]}

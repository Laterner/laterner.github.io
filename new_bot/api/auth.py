# api/auth.py
import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from passlib.context import CryptContext
from jose import JWTError, jwt
from dotenv import load_dotenv

load_dotenv()

# Конфигурация
SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key_here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 дней

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Хэширование пароля"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Создание JWT токена"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> bool:
    """Проверка JWT токена"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return True
    except JWTError:
        return False

def get_admin_password() -> str:
    """Получение пароля админа из .env"""
    return os.getenv("ADMIN_PASSWORD", "admin123")

def check_admin_password(password: str) -> bool:
    """Проверка пароля админа"""
    admin_password = get_admin_password()
    return password == admin_password

def get_current_user(request: Request) -> Optional[str]:
    """Получение текущего пользователя из cookie"""
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    if verify_token(token):
        return "admin"
    return None

def require_admin(request: Request):
    """Декоратор для проверки прав администратора"""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Необходима авторизация")
    return user
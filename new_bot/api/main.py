# api/main.py
import os
from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
from typing import Optional
import logging

from .database import db
from .auth import (
    check_admin_password, 
    create_access_token, 
    verify_token,
    get_current_user,
    require_admin
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Создаем папку templates если её нет
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# Инициализация FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Запуск
    logger.info("🚀 Запуск FastAPI приложения...")
    await db.init_db()
    logger.info("✅ База данных инициализирована")
    yield
    # Остановка
    logger.info("👋 Остановка FastAPI приложения...")

app = FastAPI(
    title="fstbot.ru Admin API",
    description="API для управления игроками",
    version="1.0.0",
    lifespan=lifespan
)

# Шаблоны
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Security
security = HTTPBearer()

# Маршруты

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Главная страница с формой добавления очков"""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "Добавление очков"}
    )

@app.post("/api/add_score")
async def add_score(
    player_id: str = Form(...),
    amount: int = Form(...)
):
    """API для добавления очков"""
    try:
        # Проверяем игрока
        user = await db.get_user_by_player_id(player_id)
        if not user:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": f"Игрок с ID {player_id} не найден"}
            )
        
        # Добавляем очки
        success = await db.add_score(player_id, amount)
        
        if success:
            return JSONResponse(
                content={
                    "success": True,
                    "message": f"Добавлено {amount} очков игроку {user['name']} (ID: {player_id})",
                    "player": {
                        "name": user['name'],
                        "player_id": player_id,
                        "new_score": user['score'] + amount
                    }
                }
            )
        else:
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": "Ошибка при добавлении очков"}
            )
    except Exception as e:
        logger.error(f"Error adding score: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )

@app.get("/api/check_player/{player_id}")
async def check_player(player_id: str):
    """Проверка существования игрока"""
    user = await db.get_user_by_player_id(player_id)
    if user:
        return JSONResponse(
            content={
                "exists": True,
                "name": user['name'],
                "score": user['score'],
                "team": user['team']
            }
        )
    else:
        return JSONResponse(
            content={"exists": False}
        )

@app.get("/admin", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Страница входа в админку"""
    # Проверяем, есть ли уже токен
    token = request.cookies.get("access_token")
    if token and verify_token(token):
        # Если токен валидный, перенаправляем в админку
        return RedirectResponse(url="/admin/dashboard")
    
    return templates.TemplateResponse(
        "admin_login.html",
        {"request": request, "title": "Вход в админку", "error": None}
    )

@app.post("/admin/login")
async def admin_login(
    request: Request,
    password: str = Form(...)
):
    """Вход в админку"""
    if check_admin_password(password):
        # Создаем токен
        token = create_access_token({"sub": "admin"})
        
        # Устанавливаем cookie
        response = RedirectResponse(url="/admin/dashboard", status_code=302)
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            max_age=60*60*24*7,  # 7 дней
            samesite="lax"
        )
        return response
    else:
        return templates.TemplateResponse(
            "admin_login.html",
            {
                "request": request, 
                "title": "Вход в админку", 
                "error": "❌ Неверный пароль!"
            },
            status_code=401
        )

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Панель управления админа"""
    # Проверяем авторизацию
    token = request.cookies.get("access_token")
    if not token or not verify_token(token):
        return RedirectResponse(url="/admin", status_code=302)
    
    # Получаем всех пользователей
    users = await db.get_all_users()
    
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "title": "Админ панель",
            "users": users,
            "message": None
        }
    )

@app.post("/admin/api/update_name")
async def admin_update_name(
    request: Request,
    player_id: str = Form(...),
    new_name: str = Form(...)
):
    """Обновление имени игрока"""
    # Проверяем авторизацию
    token = request.cookies.get("access_token")
    if not token or not verify_token(token):
        return JSONResponse(
            status_code=401,
            content={"success": False, "message": "Не авторизован"}
        )
    
    try:
        user = await db.get_user_by_player_id(player_id)
        if not user:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": f"Игрок {player_id} не найден"}
            )
        
        success = await db.update_user_name(player_id, new_name)
        
        if success:
            return JSONResponse(
                content={
                    "success": True,
                    "message": f"Имя обновлено: {user['name']} -> {new_name}"
                }
            )
        else:
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": "Ошибка при обновлении имени"}
            )
    except Exception as e:
        logger.error(f"Error updating name: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )

@app.post("/admin/api/update_score")
async def admin_update_score(
    request: Request,
    player_id: str = Form(...),
    new_score: int = Form(...)
):
    """Обновление очков игрока"""
    # Проверяем авторизацию
    token = request.cookies.get("access_token")
    if not token or not verify_token(token):
        return JSONResponse(
            status_code=401,
            content={"success": False, "message": "Не авторизован"}
        )
    
    try:
        if new_score < 0:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Очки не могут быть отрицательными"}
            )
        
        user = await db.get_user_by_player_id(player_id)
        if not user:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": f"Игрок {player_id} не найден"}
            )
        
        success = await db.update_user_score(player_id, new_score)
        
        if success:
            return JSONResponse(
                content={
                    "success": True,
                    "message": f"Очки обновлены: {user['score']} -> {new_score} для игрока {user['name']}"
                }
            )
        else:
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": "Ошибка при обновлении очков"}
            )
    except Exception as e:
        logger.error(f"Error updating score: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )

@app.get("/admin/api/search")
async def admin_search_users(
    request: Request,
    query: str = ""
):
    """Поиск игроков"""
    token = request.cookies.get("access_token")
    if not token or not verify_token(token):
        return JSONResponse(
            status_code=401,
            content={"success": False, "message": "Не авторизован"}
        )
    
    if not query or len(query) < 2:
        users = await db.get_all_users()
    else:
        users = await db.search_users(query)
    
    return JSONResponse(
        content={"success": True, "users": users}
    )

@app.get("/admin/logout")
async def admin_logout():
    """Выход из админки"""
    response = RedirectResponse(url="/admin", status_code=302)
    response.delete_cookie("access_token")
    return response

# Middleware для логирования
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"{request.method} {request.url.path}")
    response = None # await call_next(request)
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
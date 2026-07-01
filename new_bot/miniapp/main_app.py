import os
import uvicorn
from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
from database import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Запуск
    print("🚀 Запуск FastAPI приложения...")
    await db.init_db()
    print("✅ База данных инициализирована")
    yield
    # Остановка
    print("👋 Остановка FastAPI приложения...")


app = FastAPI(
    title="fstbot.ru Admin API",
    description="API для управления игроками",
    version="1.0.0",
    lifespan=lifespan
)

# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Создаем папку templates если её нет
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# Шаблоны
templates = Jinja2Templates(directory=TEMPLATES_DIR)
# print(STATIC_DIR)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Security
security = HTTPBearer()

# Маршруты

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = await db.get_user_by_player_id("SUHNG")
    print('user::', user)

    return templates.TemplateResponse(
        request=request, name="index.html", context={"title": "Home", 'user':user}
    )

@app.get("/qr", response_class=HTMLResponse)
def qr_page(request: Request):
    return templates.TemplateResponse(
        request=request, name="qr.html", context={"title": "QR"}
    )

@app.get("/quize", response_class=HTMLResponse)
def quize_page(request: Request):
    return templates.TemplateResponse(
        request=request, name="quize.html", context={"title": "Quize"}
    )

@app.post("/answer")
def answer(ans: int ):
    return {'ans':ans}

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
        print(f"Error adding score: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)}
        )

@app.get("/faq", response_class=HTMLResponse)
def faq_page(request: Request):
    return templates.TemplateResponse(
        request=request, name="faq.html", context={"title": "faq"}
    )

@app.get("/map", response_class=HTMLResponse)
def map_page(request: Request):
    return templates.TemplateResponse(
        request=request, name="map.html", context={"title": "map"}
    )

if __name__ == "__main__":
    uvicorn.run(
        "main_app:app",
        host="0.0.0.0",
        port=8080,
        reload=True
    )
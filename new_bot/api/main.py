# api/main.py

import os
import asyncio
from functools import wraps
from typing import Optional
import logging
from quart import (
    Quart, render_template, request, redirect, 
    url_for, make_response, jsonify, session
)
from database import db
from auth import (
    check_admin_password, 
    create_access_token, 
    verify_token,
    get_current_user,
    require_admin
)
from utils import InitData, validate_init_data, eprint

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация Quart (асинхронный Flask)
app = Quart(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

eprint("STATIC_DIR", STATIC_DIR)

# Создаем папки если их нет
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

quizes = [
    {'question':'Нажмите 3', 'answers':["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4", "Вариант 5"], 'ans': 2},
    {'question':'Нажмите 1', 'answers':["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4", "Вариант 5"], 'ans': 0},
    {'question':'Нажмите 1', 'answers':["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4", "Вариант 5"], 'ans': 0},
    {'question':'Нажмите 1', 'answers':["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4", "Вариант 5"], 'ans': 0},
    {'question':'Нажмите 1', 'answers':["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4", "Вариант 5"], 'ans': 0},
    {'question':'Нажмите 1', 'answers':["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4", "Вариант 5"], 'ans': 0},
    {'question':'Нажмите 1', 'answers':["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4", "Вариант 5"], 'ans': 0},
    {'question':'Нажмите 5', 'answers':["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4", "Вариант 5"], 'ans': 4}
]

# Декоратор для проверки авторизации (асинхронный)
def login_required(f):
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        token = request.cookies.get("access_token")
        if not token or not verify_token(token):
            return redirect(url_for('admin_login_page'))
        return await f(*args, **kwargs)
    return decorated_function

# Контекстный менеджер для инициализации БД
@app.before_serving
async def init_db():
    """Инициализация базы данных при запуске"""
    logger.info("🚀 Запуск Quart приложения...")
    await db.init_db()
    logger.info("✅ База данных инициализирована")

# Middleware для логирования
@app.before_request
async def log_request():
    logger.info(f"{request.method} {request.path}")

# Маршруты
@app.route("/")
async def home():
    return await render_template("stub.html", title="Добавление очков")

@app.route("/miniapp")
async def miniapp():
    user = await db.get_user_by_player_id("SUHNG")
    user['photo_url'] = "https://t.me/i/userpic/320/QmCSKEv2Z0aQZyzIgX28SzVLKh0pH-Ovw3otL4VxczQ.svg"
    eprint(user['photo_url'])
    return await render_template("index.html", title="Home", user=user)

@app.route("/miniapp_home")
async def miniapp_home():
    user = await db.get_user_by_player_id("SUHNG")
    user['photo_url'] = "https://t.me/i/userpic/320/QmCSKEv2Z0aQZyzIgX28SzVLKh0pH-Ovw3otL4VxczQ.svg"
    eprint(user['photo_url'])
    return await render_template("index.html", title="Home", user=user, user_data='user_data')

@app.route("/tg_auth", methods=['POST'])
async def tg_auth():
    payload = await request.get_json()
    data = validate_init_data(payload.get('initData'))
    
    if not data:
        return jsonify({"error": "invalid initData"}), 400
    
    user = data.get("user")
    
    # Устанавливаем cookie
    resp = await make_response(jsonify({
        "id": user.get("id"),
        "username": user.get("username"),
        "first_name": user.get("first_name")
    }))
    resp.set_cookie("user_data", value=str(user))
    
    return resp

@app.route("/qr")
async def qr_page():
    return await render_template("qr.html", title="QR", quizes=quizes)

@app.route("/quize")
async def quize_page():
    quize_id = request.args.get('quize_id', '0')
    user = await db.get_user_by_player_id("SUHNG")
    
    try:
        quize_id = int(quize_id)
        _quize = quizes[quize_id]
    except (ValueError, IndexError):
        _quize = quizes[0]
        quize_id = 0
    
    return await render_template(
        "quize.html", 
        title="Quize", 
        player_id=user['player_id'], 
        quize=_quize, 
        quize_id=quize_id
    )

@app.route("/answer", methods=['POST'])
async def answer():
    form = await request.form
    ans = form.get('ans', 0, type=int)
    quize_id = form.get('quize_id', 0, type=int)
    player_id = form.get('player_id', '')
    
    if ans == quizes[quize_id]['ans']:
        return jsonify({'ans': 1, 'player_id': player_id})
    else:
        return jsonify({'ans': 0, 'player_id': player_id})

@app.route("/faq")
async def faq_page():
    return await render_template("faq.html", title="faq")

@app.route("/map")
async def map_page():
    return await render_template("map.html", title="map")

""" Админка роуты """
@app.route("/admin/addscore")
@login_required
async def admin_addscore():
    """Главная страница с формой добавления очков"""
    return await render_template("admin_add_points.html", title="Добавление очков")

# api urls  
@app.route("/api/add_score", methods=['POST'])
async def add_score():
    """API для добавления очков"""
    try:
        form = await request.form
        player_id = form.get('player_id')
        amount = form.get('amount', type=int)
        
        if not player_id or amount is None:
            return jsonify({
                "success": False, 
                "message": "Не указан player_id или amount"
            }), 400
        
        # Проверяем игрока
        user = await db.get_user_by_player_id(player_id)
        if not user:
            return jsonify({
                "success": False, 
                "message": f"Игрок с ID {player_id} не найден"
            }), 404
        
        # Добавляем очки
        success = await db.add_score(player_id, amount)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Добавлено {amount} очков игроку {user['name']} (ID: {player_id})",
                "player": {
                    "name": user['name'],
                    "player_id": player_id,
                    "new_score": user['score'] + amount
                }
            })
        else:
            return jsonify({
                "success": False, 
                "message": "Ошибка при добавлении очков"
            }), 500
            
    except Exception as e:
        logger.error(f"Error adding score: {e}")
        return jsonify({
            "success": False, 
            "message": str(e)
        }), 500

@app.route("/api/check_player/<player_id>")
async def check_player(player_id):
    """Проверка существования игрока"""
    user = await db.get_user_by_player_id(player_id)
    if user:
        return jsonify({
            "exists": True,
            "name": user['name'],
            "score": user['score'],
            "team": user['team']
        })
    else:
        return jsonify({"exists": False})

@app.route("/admin", methods=['GET'])
async def admin_login_page():
    """Страница входа в админку"""
    # Проверяем, есть ли уже токен
    token = request.cookies.get("access_token")
    if token and verify_token(token):
        # Если токен валидный, перенаправляем в админку
        return redirect(url_for('admin_dashboard'))
    
    return await render_template("admin_login.html", title="Вход в админку", error=None)

@app.route("/admin/login", methods=['POST'])
async def admin_login():
    """Вход в админку"""
    form = await request.form
    password = form.get('password')
    
    if check_admin_password(password):
        # Создаем токен
        token = create_access_token({"sub": "admin"})
        
        # Устанавливаем cookie
        resp = await make_response(redirect(url_for('admin_dashboard')))
        resp.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            max_age=60*60*24*7,  # 7 дней
            samesite="Lax"
        )
        return resp
    else:
        return await render_template(
            "admin_login.html",
            title="Вход в админку",
            error="❌ Неверный пароль!"
        ), 401

@app.route("/admin/dashboard")
@login_required
async def admin_dashboard():
    """Панель управления админа"""
    # Получаем всех пользователей
    users = await db.get_all_users()
    
    return await render_template(
        "admin.html",
        title="Админ панель",
        users=users,
        message=None
    )

@app.route("/admin/api/update_name", methods=['POST'])
@login_required
async def admin_update_name():
    """Обновление имени игрока"""
    try:
        form = await request.form
        player_id = form.get('player_id')
        new_name = form.get('new_name')
        
        if not player_id or not new_name:
            return jsonify({
                "success": False, 
                "message": "Не указаны player_id или new_name"
            }), 400
        
        user = await db.get_user_by_player_id(player_id)
        if not user:
            return jsonify({
                "success": False, 
                "message": f"Игрок {player_id} не найден"
            }), 404
        
        success = await db.update_user_name(player_id, new_name)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Имя обновлено: {user['name']} -> {new_name}"
            })
        else:
            return jsonify({
                "success": False, 
                "message": "Ошибка при обновлении имени"
            }), 500
            
    except Exception as e:
        logger.error(f"Error updating name: {e}")
        return jsonify({
            "success": False, 
            "message": str(e)
        }), 500

@app.route("/admin/api/update_score", methods=['POST'])
@login_required
async def admin_update_score():
    """Обновление очков игрока"""
    try:
        form = await request.form
        player_id = form.get('player_id')
        new_score = form.get('new_score', type=int)
        
        if not player_id or new_score is None:
            return jsonify({
                "success": False, 
                "message": "Не указаны player_id или new_score"
            }), 400
        
        if new_score < 0:
            return jsonify({
                "success": False, 
                "message": "Очки не могут быть отрицательными"
            }), 400
        
        user = await db.get_user_by_player_id(player_id)
        if not user:
            return jsonify({
                "success": False, 
                "message": f"Игрок {player_id} не найден"
            }), 404
        
        success = await db.update_user_score(player_id, new_score)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Очки обновлены: {user['score']} -> {new_score} для игрока {user['name']}"
            })
        else:
            return jsonify({
                "success": False, 
                "message": "Ошибка при обновлении очков"
            }), 500
            
    except Exception as e:
        logger.error(f"Error updating score: {e}")
        return jsonify({
            "success": False, 
            "message": str(e)
        }), 500

@app.route("/admin/api/search")
@login_required
async def admin_search_users():
    """Поиск игроков"""
    query = request.args.get('query', '')
    
    if not query or len(query) < 2:
        users = await db.get_all_users()
    else:
        users = await db.search_users(query)
    
    return jsonify({"success": True, "users": users})

@app.route("/admin/logout")
async def admin_logout():
    """Выход из админки"""
    resp = await make_response(redirect(url_for('admin_login_page')))
    resp.delete_cookie("access_token")
    return resp

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8000,
        debug=True
    )
# api/main.py

import os
from flask import Flask, render_template, request, redirect, url_for, make_response, jsonify, session
from functools import wraps
from typing import Optional
import logging
from database import db
from auth import (
    check_admin_password, 
    create_access_token, 
    verify_token,
    get_current_user,
    require_admin
)
from utils import InitData, validate_init_data, eprint
import asyncio

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Инициализация Flask
app = Flask(__name__, static_folder=STATIC_DIR)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

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

# Декоратор для проверки авторизации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.cookies.get("access_token")
        if not token or not verify_token(token):
            return redirect(url_for('admin_login_page'))
        return f(*args, **kwargs)
    return decorated_function

# Инициализация базы данных при запуске
# @app.before_first_request
# def init_db():
#     logger.info("🚀 Запуск Flask приложения...")
#     db.init_db()
#     logger.info("✅ База данных инициализирована")

# Маршруты
@app.route("/")
def home():
    return render_template("stub.html", title="Добавление очков")

@app.route("/miniapp")
async def miniapp():
    user = db.get_user_by_player_id("SUHNG")
    # user['photo_url'] = "https://t.me/i/userpic/320/QmCSKEv2Z0aQZyzIgX28SzVLKh0pH-Ovw3otL4VxczQ.svg"
    # eprint(user['photo_url'])
    return render_template("index.html", title="Home", user=user)

@app.route("/miniapp_home")
def miniapp_home():
    user = db.get_user_by_player_id("SUHNG")
    # user['photo_url'] = "https://t.me/i/userpic/320/QmCSKEv2Z0aQZyzIgX28SzVLKh0pH-Ovw3otL4VxczQ.svg"
    # eprint(user['photo_url'])
    return render_template("index.html", title="Home", user=user, user_data='user_data')

@app.route("/tg_auth", methods=['POST'])
def tg_auth():
    payload = request.get_json()
    data = validate_init_data(payload.get('initData'))
    
    if not data:
        return jsonify({"error": "invalid initData"}), 400
    
    user = data.get("user")
    
    # Устанавливаем cookie
    resp = make_response(jsonify({
        "id": user.get("id"),
        "username": user.get("username"),
        "first_name": user.get("first_name")
    }))
    resp.set_cookie("user_data", value=str(user))
    
    return resp

@app.route("/qr")
def qr_page():
    return render_template("qr.html", title="QR", quizes=quizes)

@app.route("/quize")
def quize_page():
    quize_id = request.args.get('quize_id', '0')
    user = db.get_user_by_player_id("SUHNG")
    
    try:
        quize_id = int(quize_id)
        _quize = quizes[quize_id]
    except (ValueError, IndexError):
        _quize = quizes[0]
        quize_id = 0
    
    return render_template("quize.html", 
                         title="Quize", 
                         player_id=user['player_id'], 
                         quize=_quize, 
                         quize_id=quize_id)

@app.route("/answer", methods=['POST'])
def answer():
    ans = request.form.get('ans', 0, type=int)
    quize_id = request.form.get('quize_id', 0, type=int)
    player_id = request.form.get('player_id', '')
    
    if ans == quizes[quize_id]['ans']:
        return jsonify({'ans': 1, 'player_id': player_id})
    else:
        return jsonify({'ans': 0, 'player_id': player_id})

@app.route("/faq")
def faq_page():
    return render_template("faq.html", title="faq")

@app.route("/map")
async def map_page():
    return render_template("map.html", title="map")

""" Админка роуты """
@app.route("/admin/addscore")
@login_required
def admin_addscore():
    """Главная страница с формой добавления очков"""
    return render_template("admin_add_points.html", title="Добавление очков")

# api urls  
@app.route("/api/add_score", methods=['POST'])
def add_score():
    """API для добавления очков"""
    try:
        player_id = request.form.get('player_id')
        amount = request.form.get('amount', type=int)
        
        if not player_id or amount is None:
            return jsonify({
                "success": False, 
                "message": "Не указан player_id или amount"
            }), 400
        
        # Проверяем игрока
        user = db.get_user_by_player_id(player_id)
        if not user:
            return jsonify({
                "success": False, 
                "message": f"Игрок с ID {player_id} не найден"
            }), 404
        
        # Добавляем очки
        success = db.add_score(player_id, amount)
        
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
def check_player(player_id):
    """Проверка существования игрока"""
    user = db.get_user_by_player_id(player_id)
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
def admin_login_page():
    """Страница входа в админку"""
    # Проверяем, есть ли уже токен
    token = request.cookies.get("access_token")
    if token and verify_token(token):
        # Если токен валидный, перенаправляем в админку
        return redirect(url_for('admin_dashboard'))
    
    return render_template("admin_login.html", title="Вход в админку", error=None)

@app.route("/admin/login", methods=['POST'])
def admin_login():
    """Вход в админку"""
    password = request.form.get('password')
    
    if check_admin_password(password):
        # Создаем токен
        token = create_access_token({"sub": "admin"})
        
        # Устанавливаем cookie
        resp = make_response(redirect(url_for('admin_dashboard')))
        resp.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            max_age=60*60*24*7,  # 7 дней
            samesite="Lax"
        )
        return resp
    else:
        return render_template(
            "admin_login.html",
            title="Вход в админку",
            error="❌ Неверный пароль!"
        ), 401

@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    """Панель управления админа"""
    # Получаем всех пользователей
    users = db.get_all_users()
    
    return render_template(
        "admin.html",
        title="Админ панель",
        users=users,
        message=None
    )

@app.route("/admin/api/update_name", methods=['POST'])
@login_required
def admin_update_name():
    """Обновление имени игрока"""
    try:
        player_id = request.form.get('player_id')
        new_name = request.form.get('new_name')
        
        if not player_id or not new_name:
            return jsonify({
                "success": False, 
                "message": "Не указаны player_id или new_name"
            }), 400
        
        user = db.get_user_by_player_id(player_id)
        if not user:
            return jsonify({
                "success": False, 
                "message": f"Игрок {player_id} не найден"
            }), 404
        
        success = db.update_user_name(player_id, new_name)
        
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
def admin_update_score():
    """Обновление очков игрока"""
    try:
        player_id = request.form.get('player_id')
        new_score = request.form.get('new_score', type=int)
        
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
        
        user = db.get_user_by_player_id(player_id)
        if not user:
            return jsonify({
                "success": False, 
                "message": f"Игрок {player_id} не найден"
            }), 404
        
        success = db.update_user_score(player_id, new_score)
        
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
def admin_search_users():
    """Поиск игроков"""
    query = request.args.get('query', '')
    
    if not query or len(query) < 2:
        users = db.get_all_users()
    else:
        users = db.search_users(query)
    
    return jsonify({"success": True, "users": users})

@app.route("/admin/logout")
def admin_logout():
    """Выход из админки"""
    resp = make_response(redirect(url_for('admin_login_page')))
    resp.delete_cookie("access_token")
    return resp

# Middleware для логирования
@app.before_request
def log_request():
    logger.info(f"{request.method} {request.path}")

if __name__ == "__main__":
    logger.info("🚀 Запуск Flask приложения...")
    db.init_db()
    logger.info("✅ База данных инициализирована")
    app.run(
        host="0.0.0.0",
        port=8000,
        debug=True
    )
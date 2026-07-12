import os
import json
import asyncio
import qrcode

from functools import wraps
from typing import Optional
from dataclasses import dataclass
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
from utils import InitData, validate_init_data, eprint, QUIZES, TeamStatsManager




team_status = None

@dataclass
class GameState:
    current_player_id: Optional[str] = None
    player_scores: dict = None
    
    def __post_init__(self):
        if self.player_scores is None:
            self.player_scores = {}

# Глобальное состояние игры
game_state = GameState()
score_task = None
score_lock = asyncio.Lock()

async def add_points_periodically():
    """Фоновая задача для начисления очков каждые 3 секунды"""
    while True:
        try:
            async with score_lock:
                if game_state.current_player_id:
                    player_id = game_state.current_player_id
                    
                    success = await db.add_score(player_id, 1)
                    if success:
                        logger.error(f"Успешно добавлены очки")
                    else:
                        logger.error(f"Произошла ошибка при добавлении")
                        
                    # Инициализируем счет игрока, если его нет
                    if player_id not in game_state.player_scores:
                        game_state.player_scores[player_id] = 0
                    
                    # Начисляем очки
                    game_state.player_scores[player_id] += 1
                    # logging.info(f"Игроку {player_id} начислено очко. Текущий счет: {game_state.player_scores[player_id]}")
            
            await asyncio.sleep(3)  # Ждем 3 секунды
        except asyncio.CancelledError:
            logging.info("Задача начисления очков остановлена")
            break
        except Exception as e:
            logging.error(f"Ошибка в задаче начисления очков: {e}")
            await asyncio.sleep(3)




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
STATIC_DIR_QR = os.path.join(STATIC_DIR, "user_qrs")

# eprint("STATIC_DIR", STATIC_DIR)

# Создаем папки если их нет
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(STATIC_DIR_QR, exist_ok=True) 

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
    global team_stats
    
    logger.info("🚀 Запуск Quart приложения...")
    
    teams = await db.init_db()
    
    print("---->>>>>>>>", teams)
    team_stats = TeamStatsManager(teams)
    
    logger.info("✅ База данных инициализирована")

@app.before_serving
async def startup():
    """Запуск фоновой задачи при старте сервера"""
    global score_task
    if score_task is None or score_task.done():
        score_task = asyncio.create_task(add_points_periodically())
        logging.info("Задача начисления очков запущена")

@app.after_serving
async def shutdown():
    """Остановка фоновой задачи при завершении сервера"""
    global score_task
    if score_task and not score_task.done():
        score_task.cancel()
        try:
            await score_task
        except asyncio.CancelledError:
            pass
        logging.info("Задача начисления очков остановлена")
        

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/set_player_king', methods=['POST'])
async def set_player():
    """Установка текущего игрока"""
    data = await request.get_json()
    if not data or 'player_id' not in data:
        return jsonify({'error': 'Не указан player_id'}), 400
    
    player_id = str(data['player_id'])
    
    async with score_lock:
        game_state.current_player_id = player_id
        # Инициализируем счет для нового игрока
        if player_id not in game_state.player_scores:
            game_state.player_scores[player_id] = 0
    
    return jsonify({
        'message': f'Текущий игрок установлен: {player_id}',
        'current_player': player_id
    })



def get_user_from_session() -> tuple[int, str]:
    user_id = request.cookies.get("tg_user_id", None)
    player_id = request.cookies.get("player_id", None)

    return user_id, player_id

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
    user_id, player_id = get_user_from_session()
    
    user = None
    
    print("user_id -->", user_id, type(user_id))

    try:
        user_id = int(user_id)
        user = await db.get_user(user_id)
        logger.info(f"user:, {user}")
    except Exception as e:
        print('Ошибка получения get_user():', e)

    if user == None:
        return await render_template("miniapp_auth.html", title="TG Auth")
    
    player_id = user['player_id']
    
    if not os.path.exists(f"./static/user_qrs/{player_id}.png"):
        try:
            os.makedirs("./static/user_qrs", exist_ok=True)
            img = qrcode.make(player_id)
            type(img)
            img.save(f"./static/user_qrs/{player_id}.png")
            print(f"QR код пользователя [{player_id}] успешно создан")
        except Exception as e:
            print("Ошибка создания QR кода пользователя:", e)
    else:
        print(f"QR код пользователя [{player_id}] найден")
    
    top_players = await db.get_top_players(10)
    top_teams = await db.get_all_teams_stats()
    player_rank = await db.get_user_rank_by_player_id(player_id)
    my_team = team_stats.get_by_id(user['team'])
    team_total_score = top_teams[user["team"] - 1]['total_score']
    print("top_teams", top_teams)
    print("top_players", top_players)
    
    return await render_template(
        "index.html", 
        title="Home", 
        user=user, 
        top_players=top_players, 
        top_teams=top_teams, 
        player_rank=player_rank, 
        my_team=my_team, 
        team_total_score=team_total_score
    )


@app.route("/reg_tg_id", methods=['POST'])
async def reg_tg_id():
    try:
        data = await request.get_json()
        tg_id = data.get('tg_id')
        player_id = None
        
        if not tg_id:
            return jsonify({
                "success": False,
                "message": "tg_id обязателен"
            }), 400
        
        # Ваша логика здесь
        print(f"Получен TG ID: {tg_id}")
        
        try:
            user = await db.get_user(int(tg_id))
            player_id = user['player_id']
            
        except Exception as e:
            print('Пользователь ещё не зарегестрирован:', e)
            response = await make_response(jsonify(
                {
                    "success": False,
                    "message": "Пользователь ещё не зарегестирован в боте"
                }
            ))
            return response
            
        response = await make_response(jsonify(
            {
                "success": True,
                "message": "Пользователь успешно авторизован",
                "tg_id": tg_id,
                'player_id': player_id
            }
        ))
    
        # Установка куки с параметрами (значение, время жизни, защита) player_id
        response.set_cookie("tg_user_id", str(tg_id), max_age=18000, secure=True, httponly=True)
        response.set_cookie("player_id", str(player_id), max_age=18000, secure=True, httponly=True)
        
        
        return response

        
    except Exception as e:
        print(e)
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@app.route("/tg_auth", methods=['POST'])
async def tg_auth():
    payload = await request.get_json()
    print("initData 1:", payload.get('initData'))
    initData = validate_init_data(payload.get('initData'))
    print("initData2:", initData)
    tg_user_id = payload.get('tg_user_id')
    if tg_user_id == "":
        tg_user_id = str(initData['user']['id'])
        
    print("auth tg_user_id ----->", tg_user_id)
    if not tg_user_id:
        return jsonify({"error": "invalid initData"}), 400
    
    # Устанавливаем cookie
    response = await make_response(jsonify({'data': "fine: " + str(tg_user_id), 'tg_user_id':tg_user_id}))
    
    # Установка куки с параметрами (значение, время жизни, защита)
    response.set_cookie("tg_user_id", tg_user_id, max_age=3600, secure=True, httponly=True)
    
    
    return response

@app.route("/tg_auth_delete", methods=['POST'])
async def tg_auth_delete():
    response = await make_response(jsonify({'message':'Cookie deleted!'}))
    response.delete_cookie('tg_user_id')
    response.delete_cookie('player_id')
    return response

@app.route("/qr")
async def qr_page():
    return await render_template("qr.html", title="QR", quizes=QUIZES)

@app.route("/faq")
async def faq_page():
    return await render_template("faq.html", title="faq")

@app.route("/map")
async def map_page():
    return await render_template("map.html", title="map")



def find_quiz_index(secret_code):
    for i, quiz in enumerate(QUIZES):
        if quiz['secret_code'] == secret_code:
            return i
    return -1

""" API """
@app.route("/api/secretcode", methods=['POST'])
async def secretcode():
    try:
        user_id, player_id = get_user_from_session()
        raw_data = await request.data
        print(f"Raw data: {raw_data}")
        
        if not raw_data:
            return jsonify({'error': 'No data received'}), 400
        
        # Декодируем и парсим JSON вручную
        try:
            data = json.loads(raw_data.decode('utf-8'))
            print(f"Parsed data: {data}")
            
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return jsonify({'error': 'Invalid JSON'}), 400
        
        secret_code = data.get('secret_code', '00000')
        print(f"Secret code: {secret_code}")
        
        quize = await db.get_quize(secret_code)
        
        is_quiz_completed = await db.is_quiz_completed(player_id, quize['id'])
        
        if is_quiz_completed:
            return jsonify({'completed': 'completed'}) 
        
        print(f"Quiz ID: {quize['id']} {quize['secret_code']}")
        
        return jsonify({'quize_id': quize['id'], 'secret_code': secret_code})
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
@app.route("/api/answer", methods=['POST'])
async def answer():
    ans = request.args.get('ans', 0, type=int)
    secret_code = request.args.get('secret_code', "00000", type=str)
    quize_id = request.args.get('quize_id', 0, type=int)
    user_id, player_id = get_user_from_session()

    print("/api/answer :::>", ans, quize_id, player_id)

    if ans == QUIZES[quize_id]['ans']:
        try:
            amount = 5
            
            if not player_id is None:
                f"Не указан player_id"
            
            # Проверяем игрока
            user = await db.get_user_by_player_id(player_id)
            if not user:
                logger.error(f"Игрок с ID {player_id} не найден")
            
            quize = await db.get_quize(secret_code)
            is_correct = ans == quize.answer
            
            await db.update_quize_status(player_id, quize_id, is_correct, amount)
    
            # Добавляем очки
            success = await db.add_score(player_id, amount)
            
            if success:
                logger.error(f"Успешно добавлены очки")
            else:
                logger.error(f"Произошла ошибка при добавлении")
                
        except Exception as e:
            logger.error(f"Error adding score: {e}")
        
        return jsonify({'ans': 1, 'player_id': player_id})
    else:
        return jsonify({'ans': 0, 'player_id': player_id})

@app.route("/quize")
async def quize_page():
    secret_code = request.args.get('secret_code', 0)
    user_id, player_id = get_user_from_session()
    
    try:
        quize = await db.get_quize(secret_code)
        print(quize)

    except (ValueError, IndexError):
        resp = await make_response("Произошла ошибка")
        return resp
    
    return await render_template(
        "quize.html", 
        title="Quize", 
        player_id=player_id, 
        quize=quize, 
        quize_id=quize['id']
    )


""" Админка роуты """
@app.route("/admin/addscore")
async def admin_addscore():
    """Главная страница с формой добавления очков"""
    return await render_template("admin_add_points_test.html", title="Добавление очков")

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
        try:
            return jsonify({
                "exists": True,
                "name": user['name'],
                "score": user['score'],
                "team": user['team_name']
            })
        except Exception as e:
            return jsonify({
                "exists": True,
                "name": user['name'],
                "score": user['score']
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
        return redirect(url_for('admin_addscore'))
    
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

@app.route("/admin/king")
async def king():
    """Начисление очков со временем"""
    
    return await render_template("king.html", title="Добавление очков")

@app.route("/api/create_quize")
async def create_quize():
    for q in QUIZES:
        await db.create_quize(
            q['question'], 
            q["secret_code"], 
            q["ans"], 
            q['answers']
            )
        print(q)
    
    resp = await make_response("Успех")
    return resp

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8000,
        debug=True
    )


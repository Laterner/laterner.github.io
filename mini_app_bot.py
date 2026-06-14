import asyncio
import json
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from database import init_db, get_user, update_balance, get_user_by_member_number, register_user

from dotenv import load_dotenv
import os

load_dotenv()

# Конфигурация
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBAPP_URL = os.getenv('WEBAPP_URL')

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    member_number = register_user(user.id, user.username, user.first_name, user.last_name)
    user_data = get_user(user.id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть Mini App", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton(text="Счёт", callback_data="balance")],
        [InlineKeyboardButton(text="Мой номер", callback_data="my_number")]
    ])
    
    await message.answer(
        f"✅ Добро пожаловать, {user.first_name}!\n\n🆔 Ваш номер: <code>{member_number}</code>\nСчёт: {user_data['balance']}",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data == "balance")
async def show_balance(callback: types.CallbackQuery):
    user_data = get_user(callback.from_user.id)
    await callback.message.answer(f"Счёт: {user_data['balance']} баллов")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "my_number")
async def show_number(callback: types.CallbackQuery):
    user_data = get_user(callback.from_user.id)
    await callback.message.answer(f"🆔 Номер: <code>{user_data['member_number']}</code>", parse_mode="HTML")
    await callback.answer()

# ========== Веб-сервер для Mini App ==========
async def handle_user(request):
    """Получение данных текущего пользователя"""
    init_data = request.headers.get('X-Telegram-Init-Data', '')
    if not init_data:
        return web.json_response({"success": False, "error": "No auth data"}, status=401)
    
    # Парсим initData (упрощённо, в продакшене нужно верифицировать через bot.checkWebAppSignature)
    from urllib.parse import parse_qs
    data = parse_qs(init_data)
    user_json = data.get('user', ['{}'])[0]
    user_info = json.loads(user_json)
    
    tg_user = get_user(user_info['id'])
    if not tg_user:
        return web.json_response({"success": False, "error": "User not found"})
    
    return web.json_response({
        "success": True,
        "user": tg_user
    })

async def handle_add_points(request):
    """Начисление баллов через Mini App"""
    init_data = request.headers.get('X-Telegram-Init-Data', '')
    if not init_data:
        return web.json_response({"success": False, "error": "No auth"}, status=401)
    
    from urllib.parse import parse_qs
    data = parse_qs(init_data)
    user_json = data.get('user', ['{}'])[0]
    user_info = json.loads(user_json)
    
    # Проверяем, является ли пользователь админом
    admin_user = get_user(user_info['id'])
    if not admin_user or not admin_user.get('is_admin', False):
        return web.json_response({"success": False, "error": "Access denied"}, status=403)
    
    # Получаем данные из запроса
    body = await request.json()
    member_number = body.get('member_number')
    amount = body.get('amount')
    
    if not member_number or not amount:
        return web.json_response({"success": False, "error": "Missing fields"})
    
    target_user = get_user_by_member_number(member_number)
    if not target_user:
        return web.json_response({"success": False, "error": "User not found"})
    
    updated_user = update_balance(target_user['telegram_id'], amount, user_info['id'], "Начислено через Mini App")
    
    # Отправляем уведомление пользователю
    try:
        await bot.send_message(
            target_user['telegram_id'],
            f"Вам начислено {amount} баллов!\nНовый счёт: {updated_user['balance']}"
        )
    except:
        pass
    
    return web.json_response({"success": True, "new_balance": updated_user['balance']})

async def serve_html(request):
    """Отдача HTML файла"""
    with open('static/index.html', 'r', encoding='utf-8') as f:
        return web.Response(text=f.read(), content_type='text/html')

async def main():
    # Запуск веб-сервера
    app = web.Application()
    app.router.add_get('/api/user', handle_user)
    app.router.add_post('/api/add-points', handle_add_points)
    app.router.add_get('/', serve_html)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
    
    print("Веб-сервер запущен на http://0.0.0.0:8000")
    
    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    init_db()
    asyncio.run(main())
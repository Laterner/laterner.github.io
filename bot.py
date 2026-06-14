import asyncio
import json
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from database import register_user, get_user, update_balance, get_user_by_member_number

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Токен вашего бота (получите у @BotFather)
BOT_TOKEN = "8635221010:AAHzOmYisA2xukDEeFZoSsK5W4ueZ77zWlg"
# URL вашего Mini App (должен быть HTTPS)
WEBAPP_URL = "https://your-domain.com/index.html"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработка команды /start - регистрация пользователя"""
    user = message.from_user
    
    # Регистрируем пользователя
    member_number = register_user(
        user.id,
        user.username,
        user.first_name,
        user.last_name
    )
    
    # Получаем данные пользователя
    user_data = get_user(user.id)
    
    # Создаём клавиатуру с кнопкой Mini App
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Открыть Mini App", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton(text="📊 Мой баланс", callback_data="balance")],
        [InlineKeyboardButton(text="🆔 Мой номер", callback_data="my_number")]
    ])
    
    welcome_text = (
        f"🎉 Добро пожаловать, {user.first_name}!\n\n"
        f"✅ Вы успешно зарегистрированы!\n"
        f"🆔 Ваш номер участника: <code>{member_number}</code>\n"
        f"💰 Баланс: {user_data['balance']} баллов\n\n"
        f"📱 Нажмите кнопку ниже, чтобы открыть Mini App"
    )
    
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(lambda c: c.data == "balance")
async def show_balance(callback: types.CallbackQuery):
    """Показать баланс пользователя"""
    user_data = get_user(callback.from_user.id)
    if user_data:
        text = (
            f"💰 Ваш баланс: <b>{user_data['balance']}</b> баллов\n"
            f"🆔 Номер участника: <code>{user_data['member_number']}</code>"
        )
        await callback.message.answer(text, parse_mode="HTML")
    else:
        await callback.message.answer("❌ Пользователь не найден. Используйте /start для регистрации.")
    await callback.answer()

@callback_query(lambda c: c.data == "my_number")
async def show_member_number(callback: types.CallbackQuery):
    """Показать номер участника"""
    user_data = get_user(callback.from_user.id)
    if user_data:
        text = f"🆔 Ваш номер участника: <code>{user_data['member_number']}</code>"
        await callback.message.answer(text, parse_mode="HTML")
    else:
        await callback.message.answer("❌ Пользователь не найден. Используйте /start для регистрации.")
    await callback.answer()

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    """Админ-панель (только для администраторов)"""
    user_data = get_user(message.from_user.id)
    
    # Проверяем, является ли пользователь администратором
    # Для первого запуска можно установить админа через SQL:
    # UPDATE users SET is_admin = 1 WHERE telegram_id = YOUR_ID;
    if not user_data or not user_data.get("is_admin", False):
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Все пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="➕ Начислить баллы", callback_data="admin_add_points")],
        [InlineKeyboardButton(text="📈 Топ пользователей", callback_data="admin_top")]
    ])
    
    await message.answer("👑 Админ-панель\nВыберите действие:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "admin_users")
async def list_users(callback: types.CallbackQuery):
    """Список всех пользователей (админ)"""
    from database import get_all_users
    users = get_all_users()
    
    if not users:
        await callback.message.answer("📭 Пользователей пока нет.")
        await callback.answer()
        return
    
    text = "📋 <b>Список пользователей:</b>\n\n"
    for i, user in enumerate(users[:20], 1):  # Показываем первые 20
        text += f"{i}. {user['name']}\n   🆔 {user['member_number']} | 💰 {user['balance']} баллов\n"
    
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_top")
async def top_users(callback: types.CallbackQuery):
    """Топ пользователей по баллам"""
    from database import get_all_users
    users = get_all_users()
    
    if not users:
        await callback.message.answer("📭 Пользователей пока нет.")
        await callback.answer()
        return
    
    text = "🏆 <b>Топ пользователей по баллам:</b>\n\n"
    for i, user in enumerate(users[:10], 1):
        text += f"{i}. {user['name']} — {user['balance']} 💰\n"
    
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_add_points")
async def request_member_number(callback: types.CallbackQuery):
    """Запрос номера участника для начисления баллов"""
    await callback.message.answer("📝 Введите номер участника и количество баллов в формате:\n\n`НОМЕР СУММА`\n\nНапример: `12345 100`", parse_mode="HTML")
    await callback.answer()

@dp.message()
async def handle_points_addition(message: types.Message):
    """Обработка ввода номера и суммы (только для админов)"""
    user_data = get_user(message.from_user.id)
    
    if not user_data or not user_data.get("is_admin", False):
        return
    
    try:
        parts = message.text.split()
        if len(parts) == 2:
            member_number = parts[0]
            amount = int(parts[1])
            
            # Ищем пользователя по номеру
            target_user = get_user_by_member_number(member_number)
            
            if target_user:
                # Начисляем баллы
                updated_user = update_balance(
                    target_user['telegram_id'],
                    amount,
                    message.from_user.id,
                    f"Начисление от админа {message.from_user.id}"
                )
                
                await message.answer(
                    f"✅ Успешно!\n"
                    f"Пользователю {target_user['first_name']} {target_user.get('last_name', '')}\n"
                    f"🆔 {member_number}\n"
                    f"💰 Начислено {amount} баллов\n"
                    f"📊 Новый баланс: {updated_user['balance']} баллов"
                )
                
                # Отправляем уведомление пользователю
                try:
                    await bot.send_message(
                        target_user['telegram_id'],
                        f"🎉 Вам начислено {amount} баллов!\n💰 Ваш новый баланс: {updated_user['balance']}"
                    )
                except:
                    pass
            else:
                await message.answer(f"❌ Пользователь с номером {member_number} не найден.")
        else:
            await message.answer("❌ Неверный формат. Используйте: `НОМЕР СУММА`\nПример: `12345 100`", parse_mode="HTML")
    except ValueError:
        await message.answer("❌ Сумма должна быть числом.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

async def main():
    """Запуск бота"""
    print("🤖 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
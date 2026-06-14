import sqlite3
import random
from datetime import datetime

DB_NAME = "users.db"

def init_db():
    """Создание таблиц при первом запуске"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            member_number TEXT UNIQUE,
            balance INTEGER DEFAULT 0,
            registered_at TIMESTAMP,
            is_admin BOOLEAN DEFAULT 0
        )
    ''')
    
    # Таблица транзакций (история начислений)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            amount INTEGER,
            admin_id INTEGER,
            description TEXT,
            created_at TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def generate_member_number():
    """Генерация уникального 5-значного номера участника"""
    while True:
        number = str(random.randint(10000, 99999))
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT member_number FROM users WHERE member_number = ?", (number,))
        if not cursor.fetchone():
            conn.close()
            return number
        conn.close()

def register_user(telegram_id, username, first_name, last_name):
    """Регистрация нового пользователя"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Проверяем, существует ли пользователь
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()
    
    if user:
        conn.close()
        return user[4]  # Возвращаем существующий member_number
    
    # Создаём нового пользователя
    member_number = generate_member_number()
    cursor.execute('''
        INSERT INTO users (telegram_id, username, first_name, last_name, member_number, balance, registered_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (telegram_id, username, first_name, last_name, member_number, 0, datetime.now()))
    
    conn.commit()
    conn.close()
    return member_number

def get_user(telegram_id):
    """Получение данных пользователя"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {
            "telegram_id": user[0],
            "username": user[1],
            "first_name": user[2],
            "last_name": user[3],
            "member_number": user[4],
            "balance": user[5],
            "registered_at": user[6],
            "is_admin": user[7]
        }
    return None

def update_balance(telegram_id, amount, admin_id, description=""):
    """Обновление баланса пользователя"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Обновляем баланс
    cursor.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (amount, telegram_id))
    
    # Записываем транзакцию
    cursor.execute('''
        INSERT INTO transactions (telegram_id, amount, admin_id, description, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (telegram_id, amount, admin_id, description, datetime.now()))
    
    conn.commit()
    conn.close()
    
    return get_user(telegram_id)

def get_user_by_member_number(member_number):
    """Поиск пользователя по номеру участника"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE member_number = ?", (member_number,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {
            "telegram_id": user[0],
            "username": user[1],
            "first_name": user[2],
            "last_name": user[3],
            "member_number": user[4],
            "balance": user[5]
        }
    return None

def get_all_users():
    """Получение всех пользователей (для администратора)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT telegram_id, first_name, last_name, member_number, balance FROM users ORDER BY balance DESC")
    users = cursor.fetchall()
    conn.close()
    
    return [{"telegram_id": u[0], "name": f"{u[1]} {u[2]}", "member_number": u[3], "balance": u[4]} for u in users]

# Инициализация БД при импорте
init_db()
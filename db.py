import sqlite3
import os
import time
import random
from datetime import datetime
from contextlib import contextmanager
from config import new_worker_balance, cooldown, new_fisher

# Настройки пути к БД
DATABASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database')
DATABASE_PATH = os.path.join(DATABASE_DIR, 'database.db')

# Создаем папку для БД при необходимости
os.makedirs(DATABASE_DIR, exist_ok=True)

def init_db():
    """Инициализация структуры базы данных"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Создание таблицы users
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER NOT NULL,
            fishing_level INTEGER NOT NULL,
            last_work TEXT
        )""")
        
        # Создание таблицы coins
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS coins (
            user_id INTEGER PRIMARY KEY,
            coins INTEGER NOT NULL
        )""")
        
        # Создание таблицы cooldowns
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cooldowns (
            user_id INTEGER PRIMARY KEY,
            work_cooldown REAL,
            fishing_cooldown REAL
        )""")
        
        # Создание таблицы fish
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS fish (
            user_id INTEGER PRIMARY KEY,
            cod INTEGER DEFAULT 0,
            salmon INTEGER DEFAULT 0,
            tropical INTEGER DEFAULT 0,
            squid INTEGER DEFAULT 0
        )""")

        # Создание таблицы svo
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS svo (
           user_id INTEGER PRIMARY KEY,
           lvl INTEGER DEFAULT 1,
           exp INTEGER DEFAULT 0,
           hp INTEGER DEFAULT 100,
           armor INTEGER DEFAULT 0,
           weapon BIGINT NOT NULL,
           grenade INTEGER DEFAULT 0,
           vehicle BIGINT NOT NULL,
           vehiclehp INTEGER DEFAULT 0,
           kills INTEGER DEFAULT 0,
           vehiclekills INTEGER DEFAULT 0,
           deaths INTEGER DEFAULT 0
    
)
""")
        conn.commit()  # Фиксация изменений

@contextmanager
def get_connection():
    """Контекстный менеджер для подключений"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    except sqlite3.Error as e:
        print(f"Ошибка SQLite: {e}")
        raise
    finally:
        conn.close()

# Инициализация БД при первом запуске
init_db()

#-----------------------------------------------------------------------------------ВАЛЮТА
# Регистрация пользователя
def register_user(user_id):
    with get_connection() as conn:
        # Регистрация в users
        conn.execute("""
            INSERT OR IGNORE INTO users (user_id, balance, fishing_level) 
            VALUES (?, ?, ?)
        """, (user_id, new_worker_balance, 1))
        
        # Регистрация в cooldowns
        conn.execute("""
            INSERT OR IGNORE INTO cooldowns (user_id) 
            VALUES (?)
        """, (user_id,))
        
        # Регистрация в coins
        conn.execute("""
            INSERT OR IGNORE INTO coins (user_id, coins)
            VALUES (?, ?)
        """, (user_id, 0))

        # Регистрация в fish
        conn.execute("""
            INSERT OR IGNORE INTO fish (user_id) 
            VALUES (?)
        """, (user_id,))
        
        conn.commit()
        
# Проверка баланса
def is_enought(user_id, need):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT coins FROM coins WHERE user_id = ?", (user_id,))
        s = cur.fetchone()
        return s[0] >= need if s else False

# Получение баланса
def get_balance(user_id):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        result = cur.fetchone()
        return result[0] if result else 0

# Обновление баланса
def update_balance(user_id, amount):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (amount, user_id)
        )
        conn.commit()

#-----------------------------------------------------------------------------------КУЛДАУН
# Проверка существования пользователя
def is_user_exists(user_id):
    """Проверка существования пользователя"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM users WHERE user_id = ?", 
            (user_id,)
        )
        return cursor.fetchone() is not None

# Установка кулдауна
def set_cooldown(user_id: int, action: str, duration: int):
    """Устанавливает кулдаун (время окончания = текущее время + длительность)."""
    action_map = {
        'work': 'work_cooldown',
        'fishing': 'fishing_cooldown'
    }
    column = action_map.get(action)
    if not column:
        return
    
    end_time = time.time() + duration
    with get_connection() as conn:
        conn.execute(
            f"UPDATE cooldowns SET {column} = ? WHERE user_id = ?",
            (end_time, user_id)
        )
        conn.commit()

def get_add_cooldowns(user_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT work_cooldown, fishing_cooldown FROM cooldowns WHERE user_id = ?",
            (user_id,)
        )
        result = cursor.fetchone()
        return result if result else (0, 0)

def get_cooldown(user_id: int, action: str) -> float:
    """Возвращает оставшееся время кулдауна в секундах."""
    action_map = {
        'work': 'work_cooldown',
        'fishing': 'fishing_cooldown'
    }
    column = action_map.get(action)
    if not column:
        return 0.0
    
    with get_connection() as conn:
        result = conn.execute(
            f"SELECT {column} FROM cooldowns WHERE user_id = ?",
            (user_id,)
        ).fetchone()
    
    if not result or result[0] is None:
        return 0.0
    
    remaining = result[0] - time.time()
    return max(0.0, remaining)  # Не может быть отрицательным

#-----------------------------------------------------------------------------------РЫБАЛКА
def fishing(user_id: int) -> str:
    """Добавляет случайную рыбу пользователю и возвращает её тип"""
    fish_types = ['cod', 'salmon', 'tropical', 'squid']
    random_fish = random.choice(fish_types)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        # Создаем запись если не существует
        cursor.execute("INSERT OR IGNORE INTO fish (user_id) VALUES (?)", (user_id,))
        # Обновляем счетчик
        cursor.execute(
            f"UPDATE fish SET {random_fish} = {random_fish} + 1 WHERE user_id = ?",
            (user_id,)
        )
        conn.commit()
    
    return random_fish

def sellfish(user_id):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT cod, salmon, tropical, squid FROM fish WHERE user_id = ?", (user_id,))
        fish_counts = cur.fetchone()
        if fish_counts:
            total_earnings = sum(fish_counts) * 10
            update_balance(user_id, total_earnings)
            cur.execute(
                "UPDATE fish SET cod = 0, salmon = 0, tropical = 0, squid = 0 WHERE user_id = ?",
                (user_id,)
            )
            conn.commit()

def get_fishing_stats(user_id: int) -> dict:
    """Получить статистику рыбалки пользователя"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT cod, salmon, tropical, squid 
            FROM fish 
            WHERE user_id = ?
        """, (user_id,))
        result = cursor.fetchone()
        
    if not result:
        return {"cod": 0, "salmon": 0, "tropical": 0, "squid": 0}
        
    return dict(result)

#-----------------------------------------------------------------------------------ДЕНЬГИ
def add_money(user_id: int, amount: int):
    if amount < 0:
        raise ValueError("Количество денег не может быть отрицательным.")
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Создаем запись в coins, если её нет
        cursor.execute(
            "INSERT OR IGNORE INTO coins (user_id, coins) VALUES (?, 0)",
            (user_id,)
        )
        
        # Обновляем баланс
        cursor.execute(
            "UPDATE coins SET coins = coins + ? WHERE user_id = ?",
            (amount, user_id)
        )
        
        conn.commit()
    print(f"[DEBUG] Добавлено {amount} монет пользователю {user_id}.")

def transfer_money(sender_id: int, receiver_id: int, amount: int) -> None:
    with get_connection() as conn:
        try:
            conn.execute("BEGIN TRANSACTION")
            
            # Проверка баланса
            sender_balance = conn.execute(
                "SELECT balance FROM users WHERE user_id = ?", 
                (sender_id,)
            ).fetchone()[0]
            
            if sender_balance < amount:
                raise ValueError("Недостаточно средств")
            
            # Списание
            conn.execute(
                "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                (amount, sender_id)
            )
            
            # Зачисление
            conn.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (amount, receiver_id)
            )
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise

# Добавьте в конец db.py для теста
if __name__ == "__main__":
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("Таблицы в базе данных:")
        for table in tables:
            print(table[0])
        print("Путь к БД:", DATABASE_PATH)
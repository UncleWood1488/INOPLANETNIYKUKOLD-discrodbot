import sqlite3
import os
import time
import random
from datetime import datetime
from contextlib import contextmanager
from config import new_worker_balance, cooldown, new_fisher, MAP_SETTINGS, DATABASE_PATH

os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

def init_db():
    """Инициализация структуры базы данных"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER NOT NULL,
            fishing_level INTEGER NOT NULL,
            last_work TEXT
        )""")
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS coins (
            user_id INTEGER PRIMARY KEY,
            coins INTEGER NOT NULL
        )""")
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cooldowns (
            user_id INTEGER PRIMARY KEY,
            work_cooldown REAL,
            fishing_cooldown REAL
        )""")
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS fish (
            user_id INTEGER PRIMARY KEY,
            cod INTEGER DEFAULT 0,
            salmon INTEGER DEFAULT 0,
            tropical INTEGER DEFAULT 0,
            squid INTEGER DEFAULT 0
        )""")

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

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS map_positions (
            user_id INTEGER PRIMARY KEY,
            x INTEGER DEFAULT 0,
            y INTEGER DEFAULT 0,
            last_updated TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS upgrades (
            user_id INTEGER PRIMARY KEY,
            net INTEGER DEFAULT 0,
            pro_rod INTEGER DEFAULT 0,
            improved_bag INTEGER DEFAULT 0,
            golden_pickaxe INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )""")
        
        conn.commit()

def add_lootbox_column():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(fish)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'lootboxes' not in columns:
            cursor.execute("ALTER TABLE fish ADD COLUMN lootboxes INTEGER DEFAULT 0")
            conn.commit()
            print("[DB] Добавлен столбец lootboxes в таблицу fish")

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
add_lootbox_column()

def register_user(user_id):
    with get_connection() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO users (user_id, balance, fishing_level) 
            VALUES (?, ?, ?)
        """, (user_id, new_worker_balance, 1))
        
        conn.execute("""
            INSERT OR IGNORE INTO cooldowns (user_id) 
            VALUES (?)
        """, (user_id,))
        
        conn.execute("""
            INSERT OR IGNORE INTO coins (user_id, coins)
            VALUES (?, ?)
        """, (user_id, 0))

        conn.execute("""
            INSERT OR IGNORE INTO fish (user_id) 
            VALUES (?)
        """, (user_id,))

        conn.execute("""
            INSERT OR IGNORE INTO map_positions (user_id, x, y) 
            VALUES (?, ?, ?)
        """, (user_id, random.randint(0, MAP_SETTINGS['grid_size']-1), random.randint(0, MAP_SETTINGS['grid_size']-1)))
        
        conn.execute("""
            INSERT OR IGNORE INTO upgrades (user_id) 
            VALUES (?)
        """, (user_id,))
        
        conn.commit()
        
def is_enought(user_id, need):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT coins FROM coins WHERE user_id = ?", (user_id,))
        s = cur.fetchone()
        return s[0] >= need if s else False

def get_balance(user_id):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        result = cur.fetchone()
        return result[0] if result else 0

def update_balance(user_id, amount):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (amount, user_id)
        )
        conn.commit()

def is_user_exists(user_id):
    """Проверка существования пользователя"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM users WHERE user_id = ?", 
            (user_id,)
        )
        return cursor.fetchone() is not None

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
    return max(0.0, remaining)

def fishing(user_id: int) -> str:
    """Добавляет случайную рыбу пользователю и возвращает её тип"""
    fish_types = ['cod', 'salmon', 'tropical', 'squid']
    random_fish = random.choice(fish_types)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO fish (user_id) VALUES (?)", (user_id,))
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
            SELECT cod, salmon, tropical, squid, lootboxes
            FROM fish 
            WHERE user_id = ?
        """, (user_id,))
        result = cursor.fetchone()
        
    if not result:
        return {"cod": 0, "salmon": 0, "tropical": 0, "squid": 0, "lootboxes": 0}
        
    return dict(result)

def add_money(user_id: int, amount: int):
    if amount < 0:
        raise ValueError("Количество денег не может быть отрицательным.")
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT OR IGNORE INTO coins (user_id, coins) VALUES (?, 0)",
            (user_id,)
        )
        
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
            
            sender_balance = conn.execute(
                "SELECT balance FROM users WHERE user_id = ?", 
                (sender_id,)
            ).fetchone()[0]
            
            if sender_balance < amount:
                raise ValueError("Недостаточно средств")
            
            conn.execute(
                "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                (amount, sender_id)
            )
            
            conn.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (amount, receiver_id)
            )
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise

def set_player_position(user_id: int, x: int, y: int):
    """Установить позицию игрока на карте"""
    if x < 0 or x >= MAP_SETTINGS['grid_size'] or y < 0 or y >= MAP_SETTINGS['grid_size']:
        raise ValueError("Координаты за пределами карты")
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO map_positions (user_id, x, y, last_updated)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (user_id, x, y))
        conn.commit()

def get_player_position(user_id: int):
    """Получить позицию игрока на карте"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT x, y FROM map_positions WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        if result:
            return result[0], result[1]
        x, y = random.randint(0, MAP_SETTINGS['grid_size']-1), random.randint(0, MAP_SETTINGS['grid_size']-1)
        set_player_position(user_id, x, y)
        return x, y

def get_all_player_positions():
    """Получить позиции всех игроков"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, x, y FROM map_positions")
        return {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

def get_upgrade(user_id: int, upgrade: str) -> int:
    """Возвращает 0 или 1 для конкретного апгрейда"""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT {upgrade} FROM upgrades WHERE user_id = ?", (user_id,))
        result = cur.fetchone()
        return result[0] if result else 0

def set_upgrade(user_id: int, upgrade: str, value: int):
    """Устанавливает значение апгрейда (0 или 1)"""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE upgrades SET {upgrade} = ? WHERE user_id = ?", (value, user_id))
        conn.commit()

def get_all_upgrades(user_id: int) -> dict:
    """Возвращает словарь со всеми апгрейдами пользователя"""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT net, pro_rod, improved_bag, golden_pickaxe FROM upgrades WHERE user_id = ?", (user_id,))
        result = cur.fetchone()
        if result:
            return dict(result)
        return {'net': 0, 'pro_rod': 0, 'improved_bag': 0, 'golden_pickaxe': 0}
    
def get_lootboxes(user_id: int) -> int:
    """Возвращает количество лутбоксов у пользователя"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT lootboxes FROM fish WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else 0

def add_lootbox(user_id: int, amount: int = 1):
    """Добавляет лутбоксы пользователю"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO fish (user_id, lootboxes) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET lootboxes = lootboxes + ?
        """, (user_id, amount, amount))
        conn.commit()

def remove_lootbox(user_id: int, amount: int = 1):
    """Убирает лутбоксы у пользователя (проверка на отрицательное значение не выполняется)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE fish SET lootboxes = lootboxes - ? WHERE user_id = ?
        """, (amount, user_id))
        conn.commit()

def add_fish(user_id: int, fish_type: str, amount: int = 1):
    """Добавляет определённый вид рыбы пользователю"""
    valid_types = ['cod', 'salmon', 'tropical', 'squid']
    if fish_type not in valid_types:
        raise ValueError(f"Неверный тип рыбы. Допустимо: {valid_types}")
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            INSERT INTO fish (user_id, {fish_type}) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET {fish_type} = {fish_type} + ?
        """, (user_id, amount, amount))
        conn.commit()

if __name__ == "__main__":
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("Таблицы в базе данных:")
        for table in tables:
            print(table[0])
        print("Путь к БД:", DATABASE_PATH)
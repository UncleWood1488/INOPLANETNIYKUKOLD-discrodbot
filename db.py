import sqlite3
import os
import time
import random
import json
from datetime import datetime
from contextlib import contextmanager
from config import (
    new_worker_balance, cooldown, new_fisher, MAP_SETTINGS,
    DATABASE_PATH, RARITY_DATA, FISH_BASE_PRICES
)

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
            squid INTEGER DEFAULT 0,
            lootboxes INTEGER DEFAULT 0,
            rarities TEXT DEFAULT '{}'
        )""")

        # Миграция: колонка rarities для существующих БД
        try:
            cursor.execute("ALTER TABLE fish ADD COLUMN rarities TEXT DEFAULT '{}'")
        except sqlite3.OperationalError:
            pass

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

    migrate_rarities()


def migrate_rarities():
    """Переносит старые счётчики рыбы в JSON редкости (как common)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, cod, salmon, tropical, squid, rarities FROM fish")
        rows = cursor.fetchall()
        for row in rows:
            user_id, cod, salmon, tropical, squid, rarities = row
            try:
                data = json.loads(rarities) if rarities else {}
            except (json.JSONDecodeError, TypeError):
                data = {}

            for fish_type, count in [('cod', cod), ('salmon', salmon),
                                      ('tropical', tropical), ('squid', squid)]:
                if count > 0 and fish_type not in data:
                    data[fish_type] = {'common': count}

            cursor.execute(
                "UPDATE fish SET rarities = ? WHERE user_id = ?",
                (json.dumps(data), user_id)
            )
        conn.commit()


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


init_db()


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
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM users WHERE user_id = ?",
            (user_id,)
        )
        return cursor.fetchone() is not None


def set_cooldown(user_id: int, action: str, duration: int):
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


def fishing(user_id: int) -> dict:
    """Ловит рыбу со случайной редкостью."""
    fish_types = ['cod', 'salmon', 'tropical', 'squid']
    random_fish = random.choice(fish_types)

    # Ролл редкости
    rarities_list = list(RARITY_DATA.keys())
    weights = [RARITY_DATA[r]['weight'] for r in rarities_list]
    rarity = random.choices(rarities_list, weights=weights, k=1)[0]

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO fish (user_id) VALUES (?)", (user_id,))
        cursor.execute(
            f"UPDATE fish SET {random_fish} = {random_fish} + 1 WHERE user_id = ?",
            (user_id,)
        )

        cursor.execute("SELECT rarities FROM fish WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        try:
            rarity_data = json.loads(row[0]) if row and row[0] else {}
        except (json.JSONDecodeError, TypeError):
            rarity_data = {}

        rarity_data.setdefault(random_fish, {})
        rarity_data[random_fish][rarity] = rarity_data[random_fish].get(rarity, 0) + 1

        cursor.execute(
            "UPDATE fish SET rarities = ? WHERE user_id = ?",
            (json.dumps(rarity_data), user_id)
        )
        conn.commit()

    result = {'fish_type': random_fish, 'rarity': rarity, 'lootbox': False}

    from config import LOOTBOX
    if random.random() < LOOTBOX['drop_chance']:
        add_lootbox(user_id, 1)
        result['lootbox'] = True

    return result


def sellfish(user_id) -> int:
    """Продаёт всю рыбу с учётом редкости. Возвращает заработанную сумму."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT rarities FROM fish WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if not row or not row[0]:
            return 0

        try:
            rarity_data = json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            rarity_data = {}

        total = 0
        for fish_type, rarity_counts in rarity_data.items():
            base = FISH_BASE_PRICES.get(fish_type, 10)
            for rarity, count in rarity_counts.items():
                mult = RARITY_DATA.get(rarity, {}).get('multiplier', 1.0)
                total += int(base * mult) * count

        if total > 0:
            cursor.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (total, user_id)
            )

        cursor.execute("""
            UPDATE fish SET cod = 0, salmon = 0, tropical = 0, squid = 0, rarities = '{}'
            WHERE user_id = ?
        """, (user_id,))
        conn.commit()
        return total


def get_fishing_stats(user_id: int) -> dict:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT cod, salmon, tropical, squid, lootboxes, rarities
            FROM fish WHERE user_id = ?
        """, (user_id,))
        result = cursor.fetchone()

    if not result:
        return {"cod": 0, "salmon": 0, "tropical": 0, "squid": 0,
                "lootboxes": 0, "rarities": {}}

    data = dict(result)
    try:
        data['rarities'] = json.loads(data.get('rarities') or '{}')
    except (json.JSONDecodeError, TypeError):
        data['rarities'] = {}
    return data


def add_money(user_id: int, amount: int):
    if amount < 0:
        raise ValueError("Количество денег не может быть отрицательным.")

    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            register_user(user_id)

        cursor.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
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
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, x, y FROM map_positions")
        return {row[0]: (row[1], row[2]) for row in cursor.fetchall()}


def get_upgrade(user_id: int, upgrade: str) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT {upgrade} FROM upgrades WHERE user_id = ?", (user_id,))
        result = cur.fetchone()
        return result[0] if result else 0


def set_upgrade(user_id: int, upgrade: str, value: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE upgrades SET {upgrade} = ? WHERE user_id = ?", (value, user_id))
        conn.commit()


def get_all_upgrades(user_id: int) -> dict:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT net, pro_rod, improved_bag, golden_pickaxe FROM upgrades WHERE user_id = ?", (user_id,))
        result = cur.fetchone()
        if result:
            return dict(result)
        return {'net': 0, 'pro_rod': 0, 'improved_bag': 0, 'golden_pickaxe': 0}


def get_lootboxes(user_id: int) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT lootboxes FROM fish WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else 0


def add_lootbox(user_id: int, amount: int = 1):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM fish WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO fish (user_id) VALUES (?)", (user_id,))

        cursor.execute("""
            UPDATE fish SET lootboxes = lootboxes + ? WHERE user_id = ?
        """, (amount, user_id))
        conn.commit()


def remove_lootbox(user_id: int, amount: int = 1):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE fish SET lootboxes = lootboxes - ? WHERE user_id = ?
        """, (amount, user_id))
        conn.commit()


def add_fish(user_id: int, fish_type: str, amount: int = 1, rarity: str = 'common'):
    """Добавляет определённый вид рыбы с указанной редкостью."""
    valid_types = ['cod', 'salmon', 'tropical', 'squid']
    if fish_type not in valid_types:
        raise ValueError(f"Неверный тип рыбы. Допустимо: {valid_types}")
    if rarity not in RARITY_DATA:
        rarity = 'common'

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM fish WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO fish (user_id) VALUES (?)", (user_id,))

        cursor.execute(f"""
            UPDATE fish SET {fish_type} = {fish_type} + ? WHERE user_id = ?
        """, (amount, user_id))

        cursor.execute("SELECT rarities FROM fish WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        try:
            rarity_data = json.loads(row[0]) if row and row[0] else {}
        except (json.JSONDecodeError, TypeError):
            rarity_data = {}

        rarity_data.setdefault(fish_type, {})
        rarity_data[fish_type][rarity] = rarity_data[fish_type].get(rarity, 0) + amount

        cursor.execute(
            "UPDATE fish SET rarities = ? WHERE user_id = ?",
            (json.dumps(rarity_data), user_id)
        )
        conn.commit()


def add_fish_to_user(user_id: int, fish_type: str, amount: int = 1):
    """Обёртка для /addfish — добавляет рыбу как обычную."""
    if amount <= 0:
        raise ValueError("Количество должно быть положительным")
    add_fish(user_id, fish_type, amount, rarity='common')


def open_lootbox(user_id: int) -> dict:
    lootboxes = get_lootboxes(user_id)
    if lootboxes <= 0:
        return {'success': False, 'message': 'У вас нет лутбоксов!'}

    remove_lootbox(user_id, 1)

    from config import fish_data
    from emoji import SKUFCOIN_EMOJI

    if random.random() < 0.08:
        coins_amount = random.randint(500, 1000)
        add_money(user_id, coins_amount)
        return {
            'success': True,
            'message': f'💰 Вы получили {coins_amount} скуфкоинов {SKUFCOIN_EMOJI}!',
            'reward_type': 'coins',
            'amount': coins_amount
        }

    fish_types = ['cod', 'salmon', 'tropical', 'squid']
    fish_type = random.choice(fish_types)
    fish_amount = random.randint(1, 3)

    # Ролл редкости для лутбокса
    rarities_list = list(RARITY_DATA.keys())
    weights = [RARITY_DATA[r]['weight'] for r in rarities_list]
    rarity = random.choices(rarities_list, weights=weights, k=1)[0]

    add_fish(user_id, fish_type, fish_amount, rarity=rarity)

    fish_name = fish_data[fish_type]['name']
    fish_emoji = fish_data[fish_type]['emoji']
    rarity_info = RARITY_DATA[rarity]

    return {
        'success': True,
        'message': (
            f'{fish_emoji} Вы получили **{fish_name}** '
            f'{rarity_info["emoji"]} *{rarity_info["name"]}* x{fish_amount}!'
        ),
        'reward_type': 'fish',
        'fish_type': fish_type,
        'rarity': rarity,
        'amount': fish_amount
    }


if __name__ == "__main__":
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("Таблицы в базе данных:")
        for table in tables:
            print(table[0])
        print("Путь к БД:", DATABASE_PATH)
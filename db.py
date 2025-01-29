import datetime
import psycopg2
from psycopg2 import sql
import time
import random
from config import new_worker_balance, cooldown, new_fisher

# Подключение к PostgreSQL
conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="postgres",
    host="localhost",
    port="5432"
)

# Подключение к базе данных
def get_connection():
    return psycopg2.connect(
        dbname="nedobase",
        user="",
        password="",
        host="localhost",
        port="5432"
    )

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS coins (
    member BIGINT PRIMARY KEY,
    coins INTEGER NOT NULL
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS cooldowns (
    member BIGINT PRIMARY KEY,
    work TIMESTAMP NOT NULL,
    fishing TIMESTAMP NOT NULL
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS fish (
    member BIGINT PRIMARY KEY,
    Cod BIGINT NOT NULL,
    Salmon BIGINT NOT NULL,
    Tropical BIGINT NOT NULL,
    Squid BIGINT NOT NULL
)
""")
# cursor.execute("""
# CREATE TABLE IF NOT EXISTS svo (
#     member BIGINT NOT NULL,
#     lvl BIGINT NOT NULL,
#     exp BIGINT NOT NULL,
#     hp BIGINT NOT NULL,
#     armor BIGINT NOT NULL,
#     weapon BIGINT NOT NULL,
#     grenade BIGINT NOT NULL,
#     vechicle BIGINT NOT NULL,
#     kills BIGINT NOT NULL,
#     vehkills BIGINT NOT NULL,
#     deaths BIGINT NOT NULL
#     
# )
# """)

#-----------------------------------------------------------------------------------ВАЛЮТА
# Регистрация пользователя
def register_user(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("INSERT INTO users (user_id, balance, fishing_level) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO NOTHING"),
                (user_id, 100, 1)  # Начальный баланс и уровень
            )
            conn.commit()

# Проверка баланса
def is_enought(memberid, need):
    cursor.execute("SELECT coins FROM coins WHERE member = %s", (memberid,))
    s = cursor.fetchone()
    return s[0] >= need if s else False

# Получение баланса
def get_balance(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT balance FROM users WHERE user_id = %s"),
                (user_id,)
            )
            result = cur.fetchone()
            return result[0] if result else 0

# Обновление баланса
def update_balance(user_id, amount):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("UPDATE users SET balance = balance + %s WHERE user_id = %s"),
                (amount, user_id)
            )
            conn.commit()

#-----------------------------------------------------------------------------------ВАЛЮТА

#-----------------------------------------------------------------------------------КУЛДАУН

# Проверка существования пользователя
def is_member_exists(member):
    cursor.execute("SELECT EXISTS(SELECT 1 FROM coins WHERE member = %s)", (member,))
    return cursor.fetchone()[0]


# Установка кулдауна
def set_cooldown(user_id, action):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("UPDATE users SET last_work = NOW() WHERE user_id = %s"),
                (user_id,)
            )
            conn.commit()

def get_add_cooldowns(member):
    cursor.execute("SELECT work, fishing FROM cooldowns WHERE member = ?", (member,))
    result = cursor.fetchone()
    return result if result else (0, 0)

def get_cooldown(member, skill):
    if not is_member_exists(member)['cooldowns']:
        return 0
    
    if skill not in ['work', 'fishing']:
        raise ValueError(f"Недопустимый навык: {skill}")
    
    cursor.execute(f"SELECT {skill} FROM cooldowns WHERE member = ?", (member,))
    result = cursor.fetchone()
    
    if result and result[0] > 0:
        return result[0] - round(time.time())
    return 0

# Проверка кулдауна
def is_cooldown(user_id, action):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT last_work FROM users WHERE user_id = %s"),
                (user_id,)
            )
            result = cur.fetchone()
            if not result or not result[0]:
                return False
            # Проверка времени (например, 1 час для работы)
            return (datetime.now() - result[0]).total_seconds() < 3600

#-----------------------------------------------------------------------------------КУЛДАУН

#-----------------------------------------------------------------------------------РЫБАЛКА
def fishing(member):
    random_fish = random.choice(['Cod', 'Salmon', 'Tropical', 'Squid'])
    cursor.execute(f"UPDATE fish SET {random_fish} = {random_fish} + 1 WHERE member = %s", (member,))
    conn.commit()

def sellfish(member):
    cursor.execute("SELECT Cod, Salmon, Tropical, Squid FROM fish WHERE member = %s", (member,))
    fish_counts = cursor.fetchone()
    total_earnings = sum(fish_counts) * 10  # Пример: каждая рыба стоит 10 монет
    update_balance(member, total_earnings)
    cursor.execute("UPDATE fish SET Cod = 0, Salmon = 0, Tropical = 0, Squid = 0 WHERE member = %s", (member,))
    conn.commit()
#-----------------------------------------------------------------------------------РЫБАЛКА

# Добавление денег (админская команда)
def add_money(memberid, amount):
    if amount < 0:
        raise ValueError("Количество денег не может быть отрицательным.")
    cursor.execute("UPDATE coins SET coins = coins + %s WHERE member = %s", (amount, memberid))
    conn.commit()
    print(f"Добавлено {amount} монет пользователю {memberid}.")

# Передача денег между пользователями
def transfer_money(sender_id, receiver_id, amount):
    if amount < 0:
        raise ValueError("Количество денег не может быть отрицательным.")
    if not is_enought(sender_id, amount):
        raise ValueError("Недостаточно средств для перевода.")
    cursor.execute("UPDATE coins SET coins = coins - %s WHERE member = %s", (amount, sender_id))
    cursor.execute("UPDATE coins SET coins = coins + %s WHERE member = %s", (amount, receiver_id))
    conn.commit()
    print(f"Переведено {amount} монет от пользователя {sender_id} пользователю {receiver_id}.")

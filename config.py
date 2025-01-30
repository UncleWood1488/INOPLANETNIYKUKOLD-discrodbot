import os
from random import *
BOT_TOKEN = os.environ.get('BOT_TOKEN') or "NjAzOTM4OTUzNzQ5NDYzMDUw.GGMGPi.jqEIV5-X2Wh3jm99wUaNLn6Zj6qEj6nufk0Pm8"
BOT_PREFIX = os.environ.get('BOT_PREFIX') or '.'
PROXY_SCHEMA = os.environ.get('PROXY_SCHEMA') or "http"
PROXY_HOST = os.environ.get('PROXY_HOST') or "localhost"
PROXY_PORT = os.environ.get('PROXY_PORT') or 3130
PROXY_USER = os.environ.get('PROXY_USER') or ""
PROXY_PASSWORD = os.environ.get('PROXY_PASSWORD') or ""

# Настройки кулдаунов (в секундах)
cooldown = {
    'work': 30,     # Кулдаун для работы
    'fishing': 60,  # Кулдаун для рыбалки
}

# Настройки выплат за действия
pay = {
    'work': 100,   # Заработок за работу
    'snake': 1000, # Заработок за игру в змейку (или другое действие)
}

# Множитель для выплат (например, для повышения сложности или бонусов)
multiplier = 1

# Начальный баланс нового пользователя
new_worker_balance = 100

# Начальные значения для нового рыбака (количество пойманной рыбы)
new_fisher = {
    'Cod': 0,       # Треска
    'Salmon': 0,    # Лосось
    'Tropical': 0,  # Тропическая рыба
    'Squid': 0,     # Кальмар
}

# Настройки рыбалки (возможное количество пойманной рыбы за одну попытку)
fish = {
    'Cod': [0, 1, 2, 3],       # Треска: можно поймать от 0 до 3 штук
    'Salmon': [0, 1, 2, 3],    # Лосось: можно поймать от 0 до 3 штук
    'Tropical': [0, 1, 2, 3],  # Тропическая рыба: можно поймать от 0 до 3 штук
    'Squid': [0, 1, 2, 3],     # Кальмар: можно поймать от 0 до 3 штук
}
#game war-------
import os
from random import *
BOT_TOKEN = os.environ.get('BOT_TOKEN') or ""
BOT_PREFIX = os.environ.get('BOT_PREFIX') or '.'
# PROXY_SCHEMA = os.environ.get('PROXY_SCHEMA') or "http"
# PROXY_HOST = os.environ.get('PROXY_HOST') or "localhost"
# PROXY_PORT = os.environ.get('PROXY_PORT') or 3130
# PROXY_USER = os.environ.get('PROXY_USER') or ""
# PROXY_PASSWORD = os.environ.get('PROXY_PASSWORD') or ""

# Роли модераторов
MOD_ROLE_IDS = [406211889228546048, 406212152316395574]

FFMPEG_PATH = "C:/Users/UncleWood/Desktop/Programming/INOPLANETNIYKUKOLD-discrodbot-main/FFmpeg/bin/ffmpeg.exe"

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin',
    'options': '-vn -sn -dn -ignore_unknown -hide_banner -loglevel error'
}


# Настройки кулдаунов (в секундах)
cooldown = {
    'work': 60,     # 1 минута
    'fishing': 30   # 30 секунд
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
    'cod': 0,       # Треска
    'salmon': 0,    # Лосось
    'tropical': 0,  # Тропическая рыба
    'squid': 0,     # Кальмар
}

# Настройки рыбалки (возможное количество пойманной рыбы за одну попытку)
fish = {
    'cod': [0, 1, 2, 3],       # Треска: можно поймать от 0 до 3 штук
    'salmon': [0, 1, 2, 3],    # Лосось: можно поймать от 0 до 3 штук
    'tropical': [0, 1, 2, 3],  # Тропическая рыба: можно поймать от 0 до 3 штук
    'squid': [0, 1, 2, 3],     # Кальмар: можно поймать от 0 до 3 штук
}

fish_data = {
    'cod': {'name': 'Треска', 'emoji': '<:Fish_Raw_Cod:1327154668463325216>'},
    'salmon': {'name': 'Лосось', 'emoji': '<:Fish_Raw_Salmon:1327154686335385641>'},
    'tropical': {'name': 'Тропическая рыба', 'emoji': '<:Fish_Tropical:1327154699383607317>'},
    'squid': {'name': 'Кальмар', 'emoji': '<:Fish_Squid:1327427600888500326>'}
}

# Настройки карты
MAP_SETTINGS = {
    'grid_size': 50,
    'cell_size': 20,
    'view_radius': 5
}

# svo
weapons = {

}

vehicle = {
    
}
#game war-------
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан! Проверьте .env файл.")

BOT_PREFIX = os.getenv('BOT_PREFIX', '.')

DATABASE_PATH = os.getenv('DATABASE_PATH', './database/database.db')

FFMPEG_PATH = os.getenv('FFMPEG_PATH', '/usr/bin/ffmpeg')
if not os.path.exists(FFMPEG_PATH):
    print(f"⚠️ ВНИМАНИЕ: FFmpeg не найден по пути {FFMPEG_PATH}")
    print("Установите ffmpeg: sudo apt install ffmpeg  (или укажите путь в .env)")

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin',
    'options': '-vn -sn -dn -ignore_unknown -hide_banner -loglevel error'
}

MOD_ROLE_IDS = [406211889228546048, 406212152316395574]

cooldown = {
    'work': 60,
    'fishing': 30
}

pay = {
    'work': 100,
    'snake': 1000,
}

multiplier = 1
new_worker_balance = 100

new_fisher = {
    'cod': 0,
    'salmon': 0,
    'tropical': 0,
    'squid': 0,
}

fish = {
    'cod': [0, 1, 2, 3],
    'salmon': [0, 1, 2, 3],
    'tropical': [0, 1, 2, 3],
    'squid': [0, 1, 2, 3],
}

fish_data = {
    'cod': {'name': 'Треска', 'emoji': '<:Fish_Raw_Cod:1327154668463325216>'},
    'salmon': {'name': 'Лосось', 'emoji': '<:Fish_Raw_Salmon:1327154686335385641>'},
    'tropical': {'name': 'Тропическая рыба', 'emoji': '<:Fish_Tropical:1327154699383607317>'},
    'squid': {'name': 'Кальмар', 'emoji': '<:Fish_Squid:1327427600888500326>'}
}

MAP_SETTINGS = {
    'grid_size': 50,
    'cell_size': 20,
    'view_radius': 5
}

LOOTBOX = {
    'drop_chance': 0.05,
    'rewards': {
        'fish': {
            'cod': (1, 3),
            'salmon': (1, 3),
            'tropical': (1, 3),
            'squid': (1, 3)
        },
        'coins': (50, 200)
    },
    'reward_weights': {
        'fish': 70,
        'coins': 30
    }
}

weapons = {
    'assault_rifles': {
        'western': {
            'HK 416': {
                'damage': 35,
                'health': 100,
                'cost': 1500,
                'level_required': 3,
                'description': 'Немецкая штурмовая винтовка, отличается высокой надёжностью и точностью.'
            },
            'FN SCAR': {
                'damage': 38,
                'health': 95,
                'cost': 1600,
                'level_required': 4,
                'description': 'Бельгийская винтовка, используемая спецподразделениями.'
            },
            'M4A1': {
                'damage': 32,
                'health': 90,
                'cost': 1400,
                'level_required': 2,
                'description': 'Американский карабин, основа армии США.'
            },
            'Steyr AUG': {
                'damage': 34,
                'health': 88,
                'cost': 1450,
                'level_required': 3,
                'description': 'Австрийская винтовка компоновки булл-пап.'
            }
        },
        'eastern': {
            'АК-12': {
                'damage': 34,
                'health': 120,
                'cost': 1400,
                'level_required': 3,
                'description': 'Современная модификация автомата Калашникова.'
            },
            'АК-15': {
                'damage': 36,
                'health': 125,
                'cost': 1550,
                'level_required': 4,
                'description': 'Крупнокалиберная версия АК-12.'
            },
            'АК-308': {
                'damage': 40,
                'health': 110,
                'cost': 1700,
                'level_required': 5,
                'description': 'Экспортный вариант под патрон НАТО.'
            }
        }
    },
    'sniper_rifles': {
        'western': {
            'FR-F2': {
                'damage': 70,
                'health': 80,
                'cost': 2000,
                'level_required': 5,
                'description': 'Французская снайперская винтовка, хорошая точность.'
            },
            'M110': {
                'damage': 68,
                'health': 85,
                'cost': 2100,
                'level_required': 5,
                'description': 'Американская полуавтоматическая снайперская винтовка.'
            },
            'L115A3': {
                'damage': 75,
                'health': 75,
                'cost': 2300,
                'level_required': 6,
                'description': 'Британская крупнокалиберная снайперская винтовка.'
            }
        },
        'eastern': {
            'СВДМ': {
                'damage': 65,
                'health': 90,
                'cost': 1800,
                'level_required': 4,
                'description': 'Модернизированная снайперская винтовка Драгунова.'
            },
            'Orsis T-5000': {
                'damage': 72,
                'health': 82,
                'cost': 2200,
                'level_required': 6,
                'description': 'Высокоточная винтовка российского производства.'
            }
        }
    },
    'pistols': {
        'western': {
            'SIG Sauer P320': {
                'damage': 15,
                'health': 50,
                'cost': 500,
                'level_required': 1,
                'description': 'Основной пистолет армии США.'
            },
            'Glock 17': {
                'damage': 14,
                'health': 55,
                'cost': 480,
                'level_required': 1,
                'description': 'Австрийский пистолет, распространён по всему миру.'
            }
        },
        'eastern': {
            'Пистолет Ярыгина (ПЯ) «Грач»': {
                'damage': 16,
                'health': 60,
                'cost': 520,
                'level_required': 1,
                'description': 'Основной армейский пистолет России.'
            },
            'Пистолет Лебедева (ПЛ)': {
                'damage': 17,
                'health': 58,
                'cost': 550,
                'level_required': 2,
                'description': 'Новейший российский пистолет с улучшенной эргономикой.'
            }
        }
    },
    'grenades': {
        'western': {
            'M67 (осколочная)': {
                'damage': 50,
                'health': 10,
                'cost': 300,
                'level_required': 2,
                'description': 'Стандартная осколочная граната НАТО.'
            }
        },
        'eastern': {
            'РГД-5': {
                'damage': 48,
                'health': 10,
                'cost': 280,
                'level_required': 2,
                'description': 'Наступательная осколочная граната.'
            },
            'Ф-1': {
                'damage': 55,
                'health': 10,
                'cost': 320,
                'level_required': 3,
                'description': 'Оборонительная граната «лимонка».'
            }
        }
    }
}

vehicle = {
    'artillery': {
        'western': {
            'CAESAR (Франция)': {
                'damage': 120,
                'health': 150,
                'cost': 5000,
                'level_required': 8,
                'description': 'Колёсная самоходная гаубица, высокая мобильность.'
            },
            'PzH 2000 (Германия)': {
                'damage': 130,
                'health': 180,
                'cost': 5500,
                'level_required': 9,
                'description': 'Немецкая гусеничная САУ, высокая скорострельность.'
            },
            'Archer (Швеция)': {
                'damage': 125,
                'health': 140,
                'cost': 5200,
                'level_required': 8,
                'description': 'Автоматизированная САУ на колёсном шасси.'
            }
        },
        'eastern': {
            '2С19 «Мста-С»': {
                'damage': 115,
                'health': 170,
                'cost': 4800,
                'level_required': 8,
                'description': 'Основная российская гусеничная САУ.'
            },
            '2С35 «Коалиция-СВ»': {
                'damage': 140,
                'health': 160,
                'cost': 6000,
                'level_required': 10,
                'description': 'Новейшая российская САУ с необитаемой башней.'
            }
        }
    },
    'tanks': {
        'western': {
            'M1A2 Abrams (США)': {
                'damage': 100,
                'health': 250,
                'cost': 7000,
                'level_required': 10,
                'description': 'Основной боевой танк США, мощная броня.'
            },
            'Leopard 2A7 (Германия)': {
                'damage': 105,
                'health': 240,
                'cost': 7200,
                'level_required': 10,
                'description': 'Немецкий основной танк, отличная точность.'
            },
            'Challenger 3 (Великобритания)': {
                'damage': 110,
                'health': 260,
                'cost': 7500,
                'level_required': 11,
                'description': 'Британский танк с гладкоствольной пушкой.'
            }
        },
        'eastern': {
            'Т-90М «Прорыв»': {
                'damage': 98,
                'health': 230,
                'cost': 6800,
                'level_required': 9,
                'description': 'Глубокая модернизация Т-90.'
            },
            'Т-14 «Армата»': {
                'damage': 115,
                'health': 280,
                'cost': 8000,
                'level_required': 12,
                'description': 'Российский танк нового поколения с необитаемой башней.'
            }
        }
    },
    'helicopters': {
        'western': {
            'AH-64 Apache (ударный)': {
                'damage': 90,
                'health': 150,
                'cost': 6000,
                'level_required': 9,
                'description': 'Основной ударный вертолёт армии США.'
            },
            'UH-60 Black Hawk (многоцелевой)': {
                'damage': 20,
                'health': 180,
                'cost': 4500,
                'level_required': 7,
                'description': 'Многоцелевой вертолёт, может перевозить десант.'
            }
        },
        'eastern': {
            'Ми-28Н (ударный)': {
                'damage': 88,
                'health': 160,
                'cost': 5900,
                'level_required': 9,
                'description': 'Российский ударный вертолёт «Ночной охотник».'
            },
            'Ка-52 (ударный)': {
                'damage': 92,
                'health': 155,
                'cost': 6100,
                'level_required': 9,
                'description': 'Соосный ударный вертолёт с катапультой.'
            },
            'Ми-8 (многоцелевой)': {
                'damage': 15,
                'health': 200,
                'cost': 4000,
                'level_required': 6,
                'description': 'Самый массовый вертолёт в мире.'
            },
            '«Ансат» (лёгкий)': {
                'damage': 10,
                'health': 120,
                'cost': 3500,
                'level_required': 5,
                'description': 'Лёгкий многоцелевой вертолёт.'
            }
        }
    },
    'aircraft': {
        'western': {
            'F-35 (истребитель)': {
                'damage': 120,
                'health': 180,
                'cost': 9000,
                'level_required': 12,
                'description': 'Истребитель пятого поколения, малозаметность.'
            },
            'C-130 Hercules (транспортный)': {
                'damage': 5,
                'health': 300,
                'cost': 5500,
                'level_required': 8,
                'description': 'Военно-транспортный самолёт, большая грузоподъёмность.'
            }
        },
        'eastern': {
            'Су-57 (истребитель)': {
                'damage': 118,
                'health': 175,
                'cost': 8800,
                'level_required': 12,
                'description': 'Российский истребитель пятого поколения.'
            },
            'Ил-76МД-90А (транспортный)': {
                'damage': 5,
                'health': 320,
                'cost': 5800,
                'level_required': 8,
                'description': 'Модернизированный транспортный самолёт.'
            }
        }
    },
    'transport': {
        'western': {
            'HMMWV (Хамви)': {
                'damage': 10,
                'health': 80,
                'cost': 1500,
                'level_required': 2,
                'description': 'Армейский внедорожник.'
            },
            'JLTV': {
                'damage': 12,
                'health': 90,
                'cost': 1800,
                'level_required': 3,
                'description': 'Современная замена Хамви.'
            },
            'Грузовики MAN': {
                'damage': 5,
                'health': 150,
                'cost': 2000,
                'level_required': 2,
                'description': 'Немецкие военные грузовики.'
            },
            'Грузовики Scania': {
                'damage': 5,
                'health': 140,
                'cost': 1900,
                'level_required': 2,
                'description': 'Шведские грузовики, используются в армиях Европы.'
            }
        },
        'eastern': {
            '«Тигр» (бронеавтомобиль)': {
                'damage': 15,
                'health': 100,
                'cost': 1700,
                'level_required': 2,
                'description': 'Российский бронеавтомобиль.'
            },
            'Урал (грузовики)': {
                'damage': 5,
                'health': 160,
                'cost': 1800,
                'level_required': 2,
                'description': 'Отечественные армейские грузовики.'
            },
            'КамАЗ (грузовики)': {
                'damage': 5,
                'health': 155,
                'cost': 1850,
                'level_required': 2,
                'description': 'Российские грузовики, участники ралли.'
            },
            'ДТ-30 «Витязь» (двухзвенный тягач)': {
                'damage': 8,
                'health': 250,
                'cost': 3500,
                'level_required': 5,
                'description': 'Двухзвенный гусеничный тягач для северных условий.'
            }
        }
    }
}
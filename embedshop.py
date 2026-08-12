import discord
from emoji import SKUFCOIN_EMOJI
from config import fish_data, new_worker_balance
from db import get_balance, get_fishing_stats

FISH_PRICES = {
    'cod': 15,
    'salmon': 25,
    'tropical': 35,
    'squid': 50
}

def create_fish_embed(user: discord.User, fish_type: str) -> discord.Embed:
    fish_info = fish_data.get(fish_type, {'name': 'Неизвестная рыба', 'emoji': ''})
    
    embed = discord.Embed(
        title=f"🎣 {user.display_name} поймал рыбу!",
        description=f"{fish_info['emoji']} **{fish_info['name']}**",
        color=discord.Color.blue()
    )
    
    stats = get_fishing_stats(user.id)
    fish_count = stats.get(fish_type, 0)
    embed.add_field(
        name="Теперь у вас:",
        value=f"{fish_info['emoji']} {fish_count + 1} шт.",
        inline=False
    )
    
    embed.set_thumbnail(url="https://i.imgur.com/3QZ4T7A.png")
    return embed

def create_welcome_embed(user: discord.User) -> discord.Embed:
    embed = discord.Embed(
        title="🎉 Добро пожаловать!",
        description=f"Вы получили начальный капитал: **{new_worker_balance} {SKUFCOIN_EMOJI}**",
        color=discord.Color.blue()
    )
    icon_url = user.avatar.url if user.avatar else None
    embed.set_author(name=user.display_name, icon_url=icon_url)
    
    embed.add_field(
        name="Как начать?",
        value="Используйте команды:\n"
              "`/work` — работа\n"
              "`/fishing` — рыбалка\n"
              "`/shop` — магазин",
        inline=False
    )
    
    embed.set_footer(text="Удачи в заработке!")
    return embed

def format_fish_stats(user_id: int) -> str:
    fish_stats = get_fishing_stats(user_id)
    fish_only = {k: v for k, v in fish_stats.items() if k in FISH_PRICES}
    return "\n".join(
        f"{fish_data[fish]['emoji']} {fish_data[fish]['name']}: {count} (Цена: {FISH_PRICES[fish]}{SKUFCOIN_EMOJI}/шт)"
        for fish, count in fish_only.items() if count > 0
    ) or "Пусто"

def create_main_embed(user: discord.User) -> discord.Embed:
    balance = get_balance(user.id) or 0
    stats = get_fishing_stats(user.id)
    lootboxes = stats.get('lootboxes', 0)
    
    embed = discord.Embed(
        title="🛒 Магазин Скуфкоинов",
        color=discord.Color.gold(),
        description="Выберите категорию товаров:"
    )
    icon_url = user.avatar.url if user.avatar else None
    embed.set_author(name=user.display_name, icon_url=icon_url)
    
    embed.add_field(
        name="💰 Ваш баланс",
        value=f"{balance} {SKUFCOIN_EMOJI}",
        inline=False
    )
    
    embed.add_field(
        name="📦 Лутбоксы",
        value=f"У вас **{lootboxes}** лутбоксов",
        inline=False
    )
    
    embed.add_field(
        name="Доступные разделы:",
        value="🎣 Рыбалка | ⚙️ Улучшения | 💰 Продажа рыбы",
        inline=False
    )
    
    embed.set_footer(text="Нажмите на кнопку ниже, чтобы продолжить")
    return embed

def create_sell_fish_embed(user: discord.User) -> discord.Embed:
    balance = get_balance(user.id) or 0
    stats = get_fishing_stats(user.id)
    lootboxes = stats.get('lootboxes', 0)
    
    embed = discord.Embed(
        title="💰 Продажа рыбы",
        color=discord.Color.green(),
        description="Выберите рыбу для продажи:"
    )
    icon_url = user.avatar.url if user.avatar else None
    embed.set_author(name=user.display_name, icon_url=icon_url)
    
    embed.add_field(
        name='Ваш баланс',
        value=f"{balance} {SKUFCOIN_EMOJI}",
        inline=False
    )
    
    embed.add_field(
        name='📦 Лутбоксы',
        value=f"У вас **{lootboxes}** лутбоксов",
        inline=False
    )
    
    fish_stats = {k: v for k, v in stats.items() if k in FISH_PRICES}
    if fish_stats and any(fish_stats.values()):
        embed.add_field(
            name="Ваш улов",
            value=format_fish_stats(user.id),
            inline=False
        )
    else:
        embed.add_field(
            name="Ваш улов",
            value="У вас нет рыбы для продажи!",
            inline=False
        )
    
    embed.set_footer(text="Нажмите на кнопку с рыбой для продажи")
    return embed

def create_category_embed(user: discord.User, page: int) -> discord.Embed:
    balance = get_balance(user.id) or 0
    fish_stats = get_fishing_stats(user.id) or {}
    lootboxes = fish_stats.get('lootboxes', 0)
    
    embed = discord.Embed(color=discord.Color.gold())
    icon_url = user.avatar.url if user.avatar else None
    embed.set_author(name=user.display_name, icon_url=icon_url)
    
    embed.add_field(
        name='Баланс',
        value=f"{balance} {SKUFCOIN_EMOJI}",
        inline=False
    )
    
    embed.add_field(
        name='📦 Лутбоксы',
        value=f"У вас **{lootboxes}** лутбоксов",
        inline=False
    )
    
    embed.add_field(
        name='🎣 Ваш улов',
        value=format_fish_stats(user.id) or "Пусто",
        inline=False
    )
    
    if page == 1:
        embed.title = "Рыболовные товары"
        embed.add_field(
            name="Сеть", 
            value=f"+1 рыба за попытку\n**Цена:** 500 {SKUFCOIN_EMOJI}", 
            inline=True
        )
        embed.add_field(
            name="Удочка PRO", 
            value=f"-50% к кулдауну\n**Цена:** 1000 {SKUFCOIN_EMOJI}", 
            inline=True
        )
    elif page == 2:
        embed.title = "⚙️ Улучшения"
        embed.add_field(
            name="Улучшенная сумка", 
            value=f"+10 слотов\n**Цена:** 750 {SKUFCOIN_EMOJI}", 
            inline=True
        )
        embed.add_field(
            name="Золотая кирка", 
            value=f"x2 к доходу\n**Цена:** 1500 {SKUFCOIN_EMOJI}", 
            inline=True
        )
    elif page == 3:
        return create_sell_fish_embed(user)
    
    embed.set_footer(text="Назад: 🔙 | Закрыть: ❌")
    return embed
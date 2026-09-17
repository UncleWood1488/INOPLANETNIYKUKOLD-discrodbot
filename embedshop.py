import discord
from emoji import SKUFCOIN_EMOJI
from config import fish_data, new_worker_balance, RARITY_DATA, FISH_BASE_PRICES
from db import get_balance, get_fishing_stats

FISH_PRICES = FISH_BASE_PRICES  # алиас для обратной совместимости


def create_fish_embed(user: discord.User, fish_type: str, rarity: str = 'common') -> discord.Embed:
    fish_info = fish_data.get(fish_type, {'name': 'Неизвестная рыба', 'emoji': ''})
    rarity_info = RARITY_DATA.get(rarity, {'name': 'Обычная', 'emoji': '⚪', 'multiplier': 1.0})

    embed = discord.Embed(
        title=f"🎣 {user.display_name} поймал рыбу!",
        description=(
            f"{fish_info['emoji']} **{fish_info['name']}** "
            f"{rarity_info['emoji']} *{rarity_info['name']}*"
        ),
        color=discord.Color.blue()
    )

    stats = get_fishing_stats(user.id)
    count = stats.get('rarities', {}).get(fish_type, {}).get(rarity, 0)
    price = int(FISH_BASE_PRICES.get(fish_type, 10) * rarity_info['multiplier'])

    embed.add_field(
        name="Теперь у вас:",
        value=f"{fish_info['emoji']} {rarity_info['emoji']} {count} шт. (цена: {price} {SKUFCOIN_EMOJI})",
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
    stats = get_fishing_stats(user_id)
    rarity_data = stats.get('rarities', {})

    if not rarity_data:
        return "Пусто"

    lines = []
    for fish_type, rarities in rarity_data.items():
        fish_info = fish_data.get(fish_type, {'name': fish_type, 'emoji': ''})
        base = FISH_BASE_PRICES.get(fish_type, 10)
        for rarity, count in rarities.items():
            if count <= 0:
                continue
            r_info = RARITY_DATA.get(rarity, {'name': 'Обычная', 'emoji': '⚪', 'multiplier': 1.0})
            price = int(base * r_info['multiplier'])
            lines.append(
                f"{fish_info['emoji']} {fish_info['name']} {r_info['emoji']} "
                f"({r_info['name']}): {count} × {price} = {count * price}"
            )
    return "\n".join(lines) if lines else "Пусто"


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
        value="🎣 Рыбалка | ⚙️ Улучшения | 💰 Продажа рыбы | 📦 Открыть лутбокс",
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

    rarity_data = stats.get('rarities', {})
    if rarity_data and any(rarity_data.values()):
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

    embed.set_footer(text="Нажмите на кнопку ниже, чтобы продать всю рыбу")
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
import discord
from config import new_worker_balance
from db import get_balance, get_fishing_stats

fish_data = {
    'cod': {'name': 'Треска', 'emoji': '<:Fish_Raw_Cod:1327154668463325216>'},
    'salmon': {'name': 'Лосось', 'emoji': '<:Fish_Raw_Salmon:1327154686335385641>'},
    'tropical': {'name': 'Тропическая рыба', 'emoji': '<:Fish_Tropical:1327154699383607317>'},
    'squid': {'name': 'Кальмар', 'emoji': '<:Fish_Squid:1327427600888500326>'}
}

def create_welcome_embed(bot):
    return (
        discord.Embed(
            title='Добро пожаловать в магазин!',
            color=discord.Color.gold(),
            description=f"Ваш стартовый баланс: **{new_worker_balance}** <:skufcoin:1248834544233353227>"
        )
        .set_author(name=bot.user.display_name, icon_url=bot.user.avatar.url)
        .set_footer(text="Используйте кнопки для навигации")
    )

def create_main_embed(user):
    balance = get_balance(user.id) or 0
    return (
        discord.Embed(
            title='Главное меню',
            color=discord.Color.gold(),
            description="Выберите раздел:"
        )
        .add_field(name="Доступные категории", value="🎣 Рыбалка\n⚙️ Улучшения", inline=False)
        .set_author(name=user.display_name, icon_url=user.avatar.url)
        .set_footer(text=f"Ваш баланс: {balance} <:skufcoin:1248834544233353227>")
    )

def create_category_embed(user, page):
    balance = get_balance(user.id) or 0
    fish_stats = get_fishing_stats(user.id) or {}
    
    embed = discord.Embed(color=discord.Color.gold())
    embed.set_author(name=user.display_name, icon_url=user.avatar.url)
    
    # Блок с балансом
    embed.add_field(
        name='Баланс',
        value=f"{balance} <:skufcoin:1248834544233353227>",
        inline=False
    )
    
    # Блок с уловом
    fish_list = [
        f"{fish_data[f]['emoji']} {fish_data[f]['name']}: {c}" 
        for f, c in fish_stats.items() 
        if c > 0
    ]
    embed.add_field(
        name='🎣 Ваш улов',
        value='\n'.join(fish_list) or "Пусто",
        inline=False
    )
    
    # Блок с товарами
    if page == 1:
        embed.title = "Рыболовные товары"
        embed.add_field(
            name="Сеть", 
            value="+1 рыба за попытку\n**Цена:** 500 <:skufcoin:1248834544233353227>", 
            inline=True
        )
        embed.add_field(
            name="Удочка PRO", 
            value="-50% к кулдауну\n**Цена:** 1000 <:skufcoin:1248834544233353227>", 
            inline=True
        )
    elif page == 2:
        embed.title = "⚙️ Улучшения"
        embed.add_field(
            name="Улучшенная сумка", 
            value="+10 слотов\n**Цена:** 750 <:skufcoin:1248834544233353227>", 
            inline=True
        )
        embed.add_field(
            name="Золотая кирка", 
            value="x2 к доходу\n**Цена:** 1500 <:skufcoin:1248834544233353227>", 
            inline=True
        )
    
    embed.set_footer(text="Назад: 🔙 | Закрыть: ❌")
    return embed
import os
import traceback
import discord
from discord.ext import commands
import time
import db
import buttons
import logging
from embedshop import *
from shop import ShopView
from blackjack import blackjack
from random import randint, choice
from emoji import *
from config import (
    pay, cooldown, multiplier, new_worker_balance, fish_data,
    MOD_ROLE_IDS, MAP_SETTINGS, LOOTBOX
)
from map_generator import generate_full_map_embed, generate_player_map_embed

logger = logging.getLogger(__name__)
bjplayers = {}
snakeplayers = {}

bot = None

def setup_bot(bot_instance):
    global bot
    bot = bot_instance

def log(message: str, type: str = 'info'):
    if type == 'error':
        logger.error(message)
    elif type == 'debug':
        logger.debug(message)
    else:
        logger.info(message)

def get_online_members(bot):
    return [m.name for m in bot.get_all_members() if m.status != discord.Status.offline]

def replace_mention(message):
    return message.content.replace(
        message.mentions[0].mention, 
        f'@{message.mentions[0].name}'
    ) if message.mentions else message.content

async def move(ctx, members):
    role_names = [ctx.guild.get_role(role_id).name for role_id in MOD_ROLE_IDS]
    if not any(role.id in MOD_ROLE_IDS for role in ctx.author.roles) and not ctx.author.guild_permissions.move_members:
        return await ctx.reply(f"Недостаточно прав! Требуются роли: {', '.join(role_names)}", ephemeral=True)
    
    empty_channel = next((vc for vc in ctx.guild.voice_channels if len(vc.members) == 0), None)
    if not empty_channel:
        return await ctx.reply("❌ Нет пустых каналов", ephemeral=True)
    
    success, errors = [], []
    for member in members:
        try:
            await member.move_to(empty_channel)
            success.append(member.mention)
        except discord.HTTPException as e:
            errors.append(f"{member.mention}: {str(e)}")
    
    report = []
    if success: report.append(f"Успешно: {', '.join(success)}")
    if errors: report.append(f"Ошибки: {' | '.join(errors)}")
    await ctx.reply("\n".join(report), ephemeral=True)

async def addmoney(ctx, member: discord.Member, coins: int):
    if coins < 0:
        return await ctx.reply("❌ Сумма не может быть отрицательной!", ephemeral=True)
    
    try:
        db.add_money(member.id, coins)
        await ctx.reply(f"✅ Выдано {coins} скуфкоинов {SKUFCOIN_EMOJI} пользователю {member.mention}")
    except Exception as e:
        logger.error(f"[DB] Ошибка: {str(e)}")
        await ctx.reply("⚠️ Ошибка базы данных", ephemeral=True)

async def show_full_map(ctx):
    try:
        embed, file = await generate_full_map_embed()
        await ctx.reply(embed=embed, file=file)
    except Exception as e:
        logger.error(f"[MAP] Ошибка генерации карты: {str(e)}")
        await ctx.reply("❌ Ошибка генерации карты", ephemeral=True)

async def show_player_map(ctx):
    try:
        embed, file = await generate_player_map_embed(ctx.author.id, ctx.author.display_name)
        await ctx.reply(embed=embed, file=file)
    except Exception as e:
        logger.error(f"[PLAYER MAP] Ошибка генерации карты: {str(e)}")
        await ctx.reply("❌ Ошибка генерации карты", ephemeral=True)

async def set_position(ctx, x: int, y: int):
    try:
        if x < 0 or x >= MAP_SETTINGS['grid_size'] or y < 0 or y >= MAP_SETTINGS['grid_size']:
            await ctx.reply(f"❌ Координаты должны быть от 0 до {MAP_SETTINGS['grid_size']-1}", ephemeral=True)
            return
        
        db.set_player_position(ctx.author.id, x, y)
        await ctx.reply(f"✅ Позиция установлена: X={x}, Y={y}", ephemeral=True)
    except Exception as e:
        logger.error(f"[SET POSITION] Ошибка: {str(e)}")
        await ctx.reply("❌ Ошибка установки позиции", ephemeral=True)

async def show_position(ctx):
    try:
        x, y = db.get_player_position(ctx.author.id)
        embed = discord.Embed(
            title="📍 Ваша позиция на карте",
            color=discord.Color.blue()
        )
        embed.add_field(name="X координата", value=str(x), inline=True)
        embed.add_field(name="Y координата", value=str(y), inline=True)
        embed.add_field(name="Область карты", value=f"{MAP_SETTINGS['grid_size']}x{MAP_SETTINGS['grid_size']}", inline=True)
        
        await ctx.reply(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"[POSITION] Ошибка: {str(e)}")
        await ctx.reply("❌ Ошибка получения позиции", ephemeral=True)

async def balance(ctx):
    try:
        balance = db.get_balance(ctx.author.id)
        coin_text = (
            "скуфкоин" if balance == 1 
            else "скуфкоина" if 2 <= balance % 100 <= 4 
            else "скуфкоинов"
        )
        emb = discord.Embed(
            title="🍉 Баланс",
            description=f"**{balance}** {coin_text} {SKUFCOIN_EMOJI}",
            color=discord.Color.green()
        )
        emb.set_author(
            name=ctx.author.display_name, 
            icon_url=ctx.author.display_avatar.url
        )
        await ctx.reply(embed=emb, ephemeral=True)
    except Exception as e:
        logger.error(f"[BALANCE] Ошибка: {str(e)}")
        await ctx.reply("⚠️ Ошибка получения баланса", ephemeral=True)

async def work(ctx):
    try:
        user_id = ctx.author.id
        if not db.is_user_exists(user_id):
            db.register_user(user_id)
            await ctx.reply(f"🎉 Новый работник! Вам начислено {new_worker_balance} скуфкоинов")
            return

        remaining = db.get_cooldown(user_id, 'work')
        if remaining > 0:
            cd = f"{int(remaining // 60)} мин. {int(remaining % 60)} сек."
            return await ctx.reply(f"⏳ Кулдаун: {cd}", ephemeral=True)

        db.update_balance(user_id, pay['work'] * multiplier)
        db.set_cooldown(user_id, 'work', cooldown['work'])
        await ctx.reply(f"✅ Вы заработали {pay['work'] * multiplier} скуфкоинов!")

    except Exception as e:
        logger.error(f"[WORK] Ошибка: {str(e)}")
        await ctx.reply("⚠️ Ошибка выполнения работы", ephemeral=True)

async def shop(ctx):
    try:
        user_id = ctx.author.id
        if not db.is_user_exists(user_id):
            db.register_user(user_id)
        
        from embedshop import create_main_embed
        from shop import ShopView
        
        embed = create_main_embed(ctx.author)
        view = ShopView(ctx.author)
        message = await ctx.reply(embed=embed, view=view, ephemeral=True)
        view.message = message
        
    except Exception as e:
        logger.error(f"[SHOP] Ошибка: {str(e)}")
        await ctx.reply("⚠️ Ошибка открытия магазина", ephemeral=True)

async def bj(ctx, bet: int):
    game = None
    try:
        if ctx.author.id in bjplayers:
            return await ctx.reply("⚠️ Вы уже в игре!", ephemeral=True)
        
        if bet <= 0:
            return await ctx.reply("❌ Ставка должна быть положительной!", ephemeral=True)

        balance = db.get_balance(ctx.author.id)
        logger.debug(f"[BJ] User {ctx.author.id} balance: {balance}, bet: {bet}")

        if balance < bet:
            return await ctx.reply("❌ Недостаточно средств!", ephemeral=True)

        game = blackjack(ctx.author, bet)
        bjplayers[ctx.author.id] = game
        view = await buttons.bj_buttons(ctx, bjplayers)
        await ctx.reply(game.prepare_message(), view=view)

    except Exception as e:
        logger.error(f"[BJ] Ошибка: {str(e)}")
        await ctx.reply("⚠️ Ошибка запуска игры", ephemeral=True)
    finally:
        if game is None and ctx.author.id in bjplayers:
            del bjplayers[ctx.author.id]

async def fishing(ctx):
    try:
        user_id = ctx.author.id
        if not db.is_user_exists(user_id):
            db.register_user(user_id)
            await ctx.reply(f"🎣 Новый рыбак! Вам начислено {new_worker_balance} скуфкоинов")
            return

        remaining = db.get_cooldown(user_id, 'fishing')
        if remaining > 0:
            cd = f"{int(remaining // 60)} мин. {int(remaining % 60)} сек."
            return await ctx.reply(f"⏳ Кулдаун: {cd}", ephemeral=True)

        caught_fish = db.fishing(user_id)
        db.set_cooldown(user_id, 'fishing', cooldown['fishing'])
        
        lootbox_message = ""
        import random
        if random.random() < LOOTBOX['drop_chance']:
            db.add_lootbox(user_id, 1)
            lootbox_message = "\n\n📦 **Вам выпал лутбокс!** Загляните в магазин, чтобы открыть его."

        embed = create_fish_embed(ctx.author, caught_fish)
        if lootbox_message:
            if embed.description:
                embed.description += lootbox_message
            else:
                embed.description = lootbox_message
        
        await ctx.reply(embed=embed)

    except Exception as e:
        logger.error(f"[FISHING] Ошибка: {str(e)}")
        await ctx.reply("🎣 Ошибка рыбалки", ephemeral=True)

async def open_lootbox(user_id: int):
    from config import LOOTBOX, fish_data
    import random

    lootboxes = db.get_lootboxes(user_id)
    if lootboxes <= 0:
        return False, "У вас нет лутбоксов!"

    db.remove_lootbox(user_id, 1)

    reward_type = random.choices(
        population=list(LOOTBOX['reward_weights'].keys()),
        weights=list(LOOTBOX['reward_weights'].values())
    )[0]

    if reward_type == 'fish':
        fish_type = random.choice(['cod', 'salmon', 'tropical', 'squid'])
        min_q, max_q = LOOTBOX['rewards']['fish'][fish_type]
        amount = random.randint(min_q, max_q)
        db.add_fish(user_id, fish_type, amount)
        
        fish_name = fish_data[fish_type]['name']
        fish_emoji = fish_data[fish_type]['emoji']
        return True, f"Вы получили {fish_emoji} **{fish_name}** x{amount}!"

    else:
        min_c, max_c = LOOTBOX['rewards']['coins']
        amount = random.randint(min_c, max_c)
        db.add_money(user_id, amount)
        return True, f"Вы получили {amount} скуфкоинов {SKUFCOIN_EMOJI}!"

async def help(ctx):
    emb = discord.Embed(
        title="📚 Помощь",
        color=discord.Color.blue(),
        description=(
            "**Основные команды:**\n"
            "`/work` - Заработать скуфкоины\n"
            "`/balance` - Проверить баланс\n"
            "`/shop` - Открыть магазин\n\n"
            "**Музыка:**\n"
            "`/play [запрос]` - Воспроизвести трек\n"
            "`/pause` - Приостановить воспроизведение\n"
            "`/resume` - Возобновить воспроизведение\n"
            "`/skip` - Пропустить текущий трек\n"
            "`/stop` - Остановить воспроизведение\n"
            "`/queue` - Показать очередь\n"
            "`/shuffle` - Перемешать очередь\n"
            "`/loop_queue` - Повтор плейлиста\n"
            "`/loop_one` - Повтор текущего трека\n\n"
            "**Управление через кнопки:**\n"
            "Нажмите 📋 в плеере для просмотра очереди"
        )
    )
    await ctx.reply(embed=emb, ephemeral=True)

async def svogamehelp(ctx):
    embed = discord.Embed(
        title="🎮 Помощь по игре 'Специальная Военная Операция'",
        color=discord.Color.dark_green(),
        description=(
            "**Основные команды:**\n"
            "`/svogameprofile` - Показать ваш профиль\n"
            "`/svogameattack [@игрок]` - Атаковать другого игрока\n"
            "`/svogamebuy [предмет]` - Купить оружие или технику\n\n"
            "**Статистика:**\n"
            "• Уровень и опыт\n"
            "• Здоровье и броня\n"
            "• Оружие и техника\n"
            "• Убийства и смерти\n"
        )
    )
    await ctx.reply(embed=embed, ephemeral=True)

async def svogameprofile(ctx):
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT lvl, exp, hp, armor, weapon, vehicle, kills, deaths FROM svo WHERE user_id = ?",
                (ctx.author.id,)
            )
            result = cursor.fetchone()
            
            if not result:
                cursor.execute("""
                    INSERT INTO svo (user_id, lvl, exp, hp, armor, weapon, vehicle) 
                    VALUES (?, 1, 0, 100, 0, 1, 1)
                """, (ctx.author.id,))
                conn.commit()
                result = (1, 0, 100, 0, 1, 1, 0, 0)
            
            lvl, exp, hp, armor, weapon, vehicle, kills, deaths = result
            
            embed = discord.Embed(
                title=f"🎮 Профиль {ctx.author.display_name}",
                color=discord.Color.dark_green()
            )
            
            embed.add_field(name="⚔️ Уровень", value=f"{lvl} (Опыт: {exp}/100)", inline=True)
            embed.add_field(name="❤️ Здоровье", value=f"{hp}/100", inline=True)
            embed.add_field(name="🛡️ Броня", value=armor, inline=True)
            embed.add_field(name="🔫 Оружие", value=f"Уровень {weapon}", inline=True)
            embed.add_field(name="🚗 Техника", value=f"Уровень {vehicle}", inline=True)
            embed.add_field(name="🎯 Статистика", value=f"Убийств: {kills}\nСмертей: {deaths}", inline=True)
            
            await ctx.reply(embed=embed, ephemeral=True)
            
    except Exception as e:
        logger.error(f"[SVO PROFILE] Ошибка: {str(e)}")
        await ctx.reply("⚠️ Ошибка загрузки профиля", ephemeral=True)
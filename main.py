import discord
import traceback
import logging
import os
import functions
import musicplayer
import requests
import asyncio
import subprocess
import sys
from discord.ext import commands
from discord import app_commands
from discord.ext.commands import Greedy
from config import BOT_TOKEN, BOT_PREFIX
from functions import log, get_online_members, replace_mention
from emoji import *
from random import choice

# Настройка логирования
logger = logging.getLogger("discord")
logger.setLevel(logging.INFO)

# Очистка логов
if os.path.exists("bot.log"):
    try:
        os.remove("bot.log")
    except Exception as e:
        print(f"Ошибка при удаления bot.log: {e}")

# Обработчики
file_handler = logging.FileHandler(filename="bot.log", encoding="utf-8", mode="w")
file_handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))

logger.addHandler(file_handler)
logger.addHandler(console_handler)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)
bot.remove_command('help')

# Setup the bot in modules
functions.setup_bot(bot)
musicplayer.setup_bot(bot)

# Список разрешенных каналов для музыкальных команд
ALLOWED_CHANNEL_IDS = [898603315372363797, 550857202139791362]  # Замените на реальные ID каналов

async def check_music_channel(interaction: discord.Interaction) -> bool:
    """Проверка разрешенного канала для музыкальных команд"""
    if interaction.channel_id not in ALLOWED_CHANNEL_IDS:
        await interaction.response.send_message(
            "❌ Эта команда недоступна в данном канале!", 
            ephemeral=True
        )
        return False
    return True

def update_yt_dlp():
    """Автоматическое обновление yt-dlp"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"])
        logger.info("[UPDATE] yt-dlp успешно обновлен")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"[UPDATE] Ошибка обновления yt-dlp: {e}")
        return False

def check_dependencies():
    # --- ИСПРАВЛЕНИЕ: Замена pkg_resources ---
    try:
        # Используем importlib.metadata для получения версии пакета
        from importlib.metadata import version, PackageNotFoundError
        yt_dlp_version = version("yt-dlp")
        logger.info(f"[DEPS] yt-dlp version: {yt_dlp_version}")
    except ImportError:
        # На случай, если importlib.metadata недоступен (Python < 3.8 без backport)
        logger.warning("[DEPS] Не удалось проверить версию yt-dlp: importlib.metadata недоступен")
    except PackageNotFoundError:
        logger.warning("[DEPS] yt-dlp не установлен")
    except Exception as e:
        logger.warning(f"[DEPS] Не удалось проверить версию yt-dlp: {e}")

def check_youtube_access():
    """Проверка доступности YouTube"""
    import urllib.request
    import socket
    try:
        socket.setdefaulttimeout(10)
        # --- ИСПРАВЛЕНИЕ: Исправлена опечатка в URL ---
        urllib.request.urlopen('https://www.youtube.com', timeout=10)
        logger.info("[NETWORK] YouTube доступен")
        return True
    except Exception as e:
        logger.error(f"[NETWORK] Нет доступа к YouTube: {e}")
        return False

@bot.event
async def on_ready():    
    # Проверка и обновление зависимостей
    logger.info("Проверка зависимостей...")
    check_dependencies()
    update_yt_dlp()
    
    # Проверка сети
    if not check_youtube_access():
        logger.error("ВНИМАНИЕ: Нет доступа к YouTube. Музыкальные функции могут не работать.")
    
    # Проверка Opus
    if not discord.opus.is_loaded():
        try:
            # --- ИСПРАВЛЕНИЕ: Уточнение пути к opus, если необходимо ---
            # Если у вас есть конкретный файл opus.dll, укажите его путь
            # discord.opus.load_opus('path/to/your/libopus-0.dll')
            discord.opus.load_opus('opus') # Или 'libopus-0.dll' на Windows, если он не найден как 'opus'
            logger.info("[INIT] Opus библиотека загружена")
        except OSError as e:
            logger.warning(f"[INIT] Не удалось загрузить Opus из 'opus': {e}")
            # Попробуем стандартный способ
            try:
                # discord.py может попытаться найти opus автоматически
                # Этот блок может быть избыточным, но оставлен для ясности
                # Discord.py обычно сам ищет opus в системе
                pass
            except Exception as auto_load_e:
                 logger.warning(f"[INIT] Автоматическая загрузка Opus не удалась: {auto_load_e}")
        except Exception as e:
             logger.warning(f"[INIT] Неизвестная ошибка при загрузке Opus: {e}")
    
    if discord.opus.is_loaded():
        logger.info("[INIT] Opus библиотека доступна")
    else:
        logger.warning("[INIT] Opus библиотека не загружена - аудио может не работать")
    
    # Запускаем фоновые задачи
    await start_background_tasks()
    
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, 
        name="на тебя!"
    ))

    logger.info('{0:#^60}'.format(''))
    logger.info('{0:*^60}'.format(f'Logged in as: {bot.user.name}'))
    logger.info('{0:*^60}'.format(f'Bot ID: {bot.user.id}'))
    logger.info('{0:#^60}'.format('USER STATS:'))
    logger.info('{0:*^60}'.format(f'All users: {len(bot.users)}'))
    logger.info('{0:*^60}'.format(f'Online: {len(get_online_members(bot))}'))
    
    logger.info('{0:#^60}'.format('SYNCING SLASH COMMANDS:'))
    for guild in bot.guilds:
        bot.tree.clear_commands(guild=guild)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        logger.info('{0:*^60}'.format(f"{guild}: {[i.name for i in synced]}"))
    logger.info('{0:*^60}'.format('Done!'))

async def start_background_tasks():
    """Запуск фоновых задач"""
    bot.loop.create_task(cleanup_task())

async def cleanup_task():
    """Задача периодической очистки"""
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            # Очистка неактивных музыкальных плееров
            await musicplayer.cleanup_inactive_players()
        except Exception as e:
            logger.error(f"[CLEANUP TASK] Ошибка: {e}")
        await asyncio.sleep(300)  # Проверка каждые 5 минут

@bot.event
async def on_voice_state_update(member, before, after):
    try:
        # Пропускаем если это не наш бот
        if member.id != bot.user.id:
            return
            
        guild = member.guild
        if not guild:
            return
            
        # Если бот отключился
        if not after.channel:
            await asyncio.sleep(1)
            if guild.id in musicplayer.music_players:
                async with musicplayer.music_players[guild.id]['lock']:
                    musicplayer.music_players[guild.id]['queue'].clear()
                musicplayer.music_players.pop(guild.id, None)
            return
            
    except Exception as e:
        logger.error(f"[VOICE] Ошибка обработки состояния: {str(e)}")

@bot.event
async def on_guild_join(guild):
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)

@bot.event
async def on_message(message):
    functions.log(f'{message.guild} - #{message.channel} - @{message.author}: "{functions.replace_mention(message)}"', type='message')
    await bot.process_commands(message)

@bot.event
async def on_error(event, *args, **kwargs):
    error_msg = traceback.format_exc()
    logger.error(f'Task error: {event},\n{error_msg}')
    user = bot.get_user(303817809253629952)
    if user:
        await user.send(f"```py\n{error_msg}```")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    try:
        await ctx.send(f"❌ Ошибка: {str(error)}", ephemeral=True)
    except discord.errors.NotFound:
        pass

# Музыкальные команды (теперь используют musicplayer)
@bot.tree.command(name="play", description="Воспроизвести трек")
@app_commands.describe(query="Название или URL трека")
@app_commands.check(check_music_channel)
async def play_command(interaction: discord.Interaction, query: str):
    await musicplayer.play_music(interaction, query)

@bot.tree.command(name="playlist", description="Добавить плейлист YouTube")
@app_commands.describe(playlist_url="URL плейлиста YouTube")
@app_commands.check(check_music_channel)
async def playlist_command(interaction: discord.Interaction, playlist_url: str):
    await musicplayer.play_playlist(interaction, playlist_url)

@bot.tree.command(name="pause", description="Приостановить воспроизведение")
@app_commands.check(check_music_channel)
async def pause_command(interaction: discord.Interaction):
    await musicplayer.pause_music(interaction)

@bot.tree.command(name="resume", description="Возобновить воспроизведение")
@app_commands.check(check_music_channel)
async def resume_command(interaction: discord.Interaction):
    await musicplayer.resume_music(interaction)

@bot.tree.command(name="skip", description="Пропустить текущий трек")
@app_commands.check(check_music_channel)
async def skip_command(interaction: discord.Interaction):
    await musicplayer.skip_music(interaction)

@bot.tree.command(name="stop", description="Остановить воспроизведение и очистить очередь")
@app_commands.check(check_music_channel)
async def stop_command(interaction: discord.Interaction):
    await musicplayer.stop_music(interaction)

@bot.tree.command(name="loop_queue", description="Включить/выключить повтор плейлиста")
@app_commands.check(check_music_channel)
async def loop_queue_command(interaction: discord.Interaction):
    await musicplayer.loop_queue(interaction)

@bot.tree.command(name="loop_one", description="Включить/выключить повтор текущего трека")
@app_commands.check(check_music_channel)
async def loop_one_command(interaction: discord.Interaction):
    await musicplayer.loop_one(interaction)

@bot.tree.command(name="queue", description="Показать очередь треков")
@app_commands.check(check_music_channel)
async def queue_command(interaction: discord.Interaction):
    await musicplayer.queue_music(interaction)

@bot.tree.command(name="shuffle", description="Перемешать очередь")
@app_commands.check(check_music_channel)
async def shuffle_command(interaction: discord.Interaction):
    await musicplayer.shuffle_music(interaction)

# Остальные команды (экономика, игры и т.д.) остаются в functions.py
@bot.hybrid_command(name='check', guild_ids=[537267521565229056])
async def check(ctx):
    functions.log(f'Check by {ctx.author}', type='debug')
    await ctx.reply(f'```bash\n{functions.get_online_members(bot)}```', ephemeral=True)

@bot.hybrid_command(name='roulette')
@app_commands.describe(members='Участники')
async def _roulette(ctx, members: Greedy[discord.Member]):
    if not members:
        await ctx.reply("Список участников пуст", ephemeral=True)
        return
    winner = choice(members)
    await ctx.reply(f'{winner.mention} победил!')

@bot.hybrid_command(name='work')
async def _work(ctx):
    '''Заработок скуфкоинов'''
    log(f'{ctx.author} /work', type='debug')
    await functions.work(ctx)

@bot.hybrid_command(name="bj")
@app_commands.describe(bet='Ставка (целое число)')
async def _bj(ctx, bet: int):
    if bet < 1:
        await ctx.reply("Ставка должна быть больше 0!", ephemeral=True)
        return
    await functions.bj(ctx, bet)

@_bj.error
async def _bj_error(ctx, error):
    log(f'Blackjack {ctx.author}: "{ctx.message.content}" - "{error}"', type='error')
    if isinstance(error, discord.ext.commands.errors.BadArgument):
        return await ctx.reply(f'{ctx.author.mention}, введите ставку nedocoins')
    elif isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
        return await ctx.reply(f'{ctx.author.mention}, введите ставку nedocoins')

@bot.hybrid_command(name='move')
@app_commands.describe(members="Кого переместить")
async def _move(ctx, members: Greedy[discord.Member]):
    '''Переместить участников в свободный голосовой канал'''
    log(f'{ctx.author} /move: {members}', type='debug')
    await functions.move(ctx, members)

@_move.error
async def _move_error(ctx, error):
    log(f'Move {ctx.author}: "{ctx.message.content}" - "{error}"', type='error')
    if isinstance(error, discord.ext.commands.errors.CommandInvokeError):
        await ctx.reply("Невозможно переместить участника, который не находится в голосовом канале")

@bot.hybrid_command(name='balance')
async def _balance(ctx):
    '''Проверка баланса'''
    log(f'{ctx.author} /balance', type='debug')
    await functions.balance(ctx)

@bot.hybrid_command(name='fishing')
async def _fishing(ctx):
    '''Рыбалка'''
    log(f'{ctx.author} /fishing', type='debug')
    await functions.fishing(ctx)

@bot.hybrid_command(name='shop')
async def _shop(ctx):
    '''Магазин'''
    log(f'{ctx.author} /shop', type='debug')
    await functions.shop(ctx)

@bot.hybrid_command(name='help')
async def _help(ctx):
    '''Помощь'''
    log(f'{ctx.author} /help', type='debug')
    await functions.help(ctx)

@bot.hybrid_command(name='addmoney')
@app_commands.describe(member="Участник", coins="Количество скуфкоинов")
async def _addmoney(ctx, member: discord.Member, coins: int):
    await functions.addmoney(ctx, member, coins)

# Команды для карты
@bot.hybrid_command(name='map')
async def _map(ctx):
    '''Показать полную карту игры'''
    log(f'{ctx.author} /map', type='debug')
    await functions.show_full_map(ctx)

@bot.hybrid_command(name='mymap')
async def _mymap(ctx):
    '''Показать карту вокруг вашего персонажа'''
    log(f'{ctx.author} /mymap', type='debug')
    await functions.show_player_map(ctx)

@bot.hybrid_command(name='setposition')
@app_commands.describe(x="X координата (0-49)", y="Y координата (0-49)")
async def _setposition(ctx, x: int, y: int):
    '''Установить позицию на карте'''
    log(f'{ctx.author} /setposition: {x}, {y}', type='debug')
    await functions.set_position(ctx, x, y)

@bot.hybrid_command(name='position')
async def _position(ctx):
    '''Показать вашу текущую позицию'''
    log(f'{ctx.author} /position', type='debug')
    await functions.show_position(ctx)

@bot.hybrid_command(name='svogamehelp')
async def _svogamehelp(ctx):
    '''Помощь по игре специальная военная операция'''
    log(f'{ctx.author} /svogamehelp', type='debug')
    await functions.svogamehelp(ctx)

@bot.hybrid_command(name='svogameprofile')
async def _svogameprofile(ctx):
    '''Профиль специальной военной операции'''
    log(f'{ctx.author} /svogameprofile', type='debug')
    await functions.svogameprofile(ctx)

if __name__ == '__main__':
    bot.run(BOT_TOKEN)
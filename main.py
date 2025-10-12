import discord
import traceback
import logging
import os
import functions
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
        print(f"Ошибка при удалении bot.log: {e}")

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
    import pkg_resources
    try:
        yt_dlp_version = pkg_resources.get_distribution("yt-dlp").version
        logger.info(f"[DEPS] yt-dlp version: {yt_dlp_version}")
    except Exception as e:
        logger.warning(f"[DEPS] Не удалось проверить версию yt-dlp: {e}")

@bot.event
async def on_ready():    
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
            # Импортируем и вызываем функцию очистки
            from functions import cleanup_inactive_players
            await cleanup_inactive_players()
        except Exception as e:
            logger.error(f"[CLEANUP TASK] Ошибка: {e}")
        await asyncio.sleep(300)  # Проверка каждые 5 минут

@bot.event
async def on_voice_state_update(member, before, after):
    try:
        guild = member.guild
        if not guild or guild.id not in functions.music_players:
            return
            
        voice_client = guild.voice_client
        
        # Если бот отключился
        if member.id == bot.user.id and not after.channel:
            await asyncio.sleep(1)
            if guild.id in functions.music_players:
                async with functions.music_players[guild.id]['lock']:
                    functions.music_players[guild.id]['queue'].clear()
                functions.music_players.pop(guild.id, None)
            return
            
        # Если бот остался один в канале
        if (voice_client and voice_client.is_connected() and 
            len(voice_client.channel.members) == 1 and
            voice_client.channel.members[0].id == bot.user.id):
            
            await asyncio.sleep(60)  # Ждем 60 секунд перед отключением
            
            # Проверяем еще раз после ожидания
            if (voice_client and voice_client.is_connected() and 
                len(voice_client.channel.members) == 1 and
                voice_client.channel.members[0].id == bot.user.id):
                
                if guild.id in functions.music_players:
                    async with functions.music_players[guild.id]['lock']:
                        functions.music_players[guild.id]['queue'].clear()
                    functions.music_players.pop(guild.id, None)
                await voice_client.disconnect()
                logger.info(f"[VOICE] Бот отключен из-за отсутствия участников в канале")
                
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

@bot.command()
async def start_game(ctx):
    url = f"http://your-api-server:3000/session"
    payload = {
        "guildId": str(ctx.guild.id),
        "channelId": str(ctx.channel.id)
    }
    response = requests.post(url, json=payload)
    game_url = f"http://your-web-client.com?guild_id={ctx.guild.id}&channel_id={ctx.channel.id}"
    await ctx.send(f"Новая игра начата: {game_url}")

@bot.command()
async def game_status(ctx):
    session_id = f"{ctx.guild.id}-{ctx.channel.id}"
    response = requests.get(f"http://your-api-server:3000/session/{session_id}")
    status = response.json().get('status', 'not_found')
    await ctx.send(f"Статус игры: {status}")

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

@bot.tree.command(name="play", description="Воспроизвести трек")
@app_commands.describe(query="Название или URL трека")
async def play_command(interaction: discord.Interaction, query: str):
    await functions.play_music(interaction, query)

@bot.tree.command(name="playlist", description="Добавить плейлист YouTube")
@app_commands.describe(playlist_url="URL плейлиста YouTube")
async def playlist_command(interaction: discord.Interaction, playlist_url: str):
    await functions.play_playlist(interaction, playlist_url)

@bot.tree.command(name="pause", description="Приостановить воспроизведение")
async def pause_command(interaction: discord.Interaction):
    await functions.pause_music(interaction)

@bot.tree.command(name="resume", description="Возобновить воспроизведение")
async def resume_command(interaction: discord.Interaction):
    await functions.resume_music(interaction)

@bot.tree.command(name="skip", description="Пропустить текущий трек")
async def skip_command(interaction: discord.Interaction):
    await functions.skip_music(interaction)

@bot.tree.command(name="stop", description="Остановить воспроизведение и очистить очередь")
async def stop_command(interaction: discord.Interaction):
    await functions.stop_music(interaction)

@bot.tree.command(name="loop_queue", description="Включить/выключить повтор плейлиста")
async def loop_queue_command(interaction: discord.Interaction):
    await functions.loop_queue(interaction)

@bot.tree.command(name="loop_one", description="Включить/выключить повтор текущего трека")
async def loop_one_command(interaction: discord.Interaction):
    await functions.loop_one(interaction)

@bot.tree.command(name="queue", description="Показать очередь треков")
async def queue_command(interaction: discord.Interaction):
    await functions.queue_music(interaction)

@bot.tree.command(name="shuffle", description="Перемешать очередь")
async def shuffle_command(interaction: discord.Interaction):
    await functions.shuffle_music(interaction)

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
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
import aiohttp
from discord.ext import commands, tasks
from discord import app_commands
from discord.ext.commands import Greedy
from config import BOT_TOKEN, BOT_PREFIX
from functions import log, get_online_members, replace_mention
from emoji import *
from random import choice

from stream_announcer import StreamAnnouncer

logger = logging.getLogger("discord")
logger.setLevel(logging.INFO)

if os.path.exists("bot.log"):
    try:
        os.remove("bot.log")
    except Exception as e:
        print(f"Ошибка при удаления bot.log: {e}")

file_handler = logging.FileHandler(filename="bot.log", encoding="utf-8", mode="w")
file_handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))

logger.addHandler(file_handler)
logger.addHandler(console_handler)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)
bot.remove_command('help')

functions.setup_bot(bot)
musicplayer.setup_bot(bot)

# --- АНОНСЕР СТРИМОВ ---
stream_announcer = StreamAnnouncer(bot)

# ID каналов
ALLOWED_CHANNEL_IDS = [898603315372363797, 550860387378003968]
SVO_CHANNEL_ID = 550860387378003968
MAIN_CHANNEL_ID = 898603315372363797
LEAVE_CHANNEL_ID = 410189814269214720
NEW_ROLE_ID = 406212330678910978

# ID роли для админских команд
ADMIN_ROLE_ID = 406211889228546048


async def check_main_channel(interaction: discord.Interaction) -> bool:
    """Проверка что команда выполняется в основном канале"""
    if interaction.channel_id != MAIN_CHANNEL_ID:
        await interaction.response.send_message(
            f"❌ Эта команда доступна только в канале <#{MAIN_CHANNEL_ID}>!",
            ephemeral=True
        )
        return False
    return True


async def check_music_channel(interaction: discord.Interaction) -> bool:
    if interaction.channel_id not in ALLOWED_CHANNEL_IDS:
        await interaction.response.send_message(
            "❌ Эта команда недоступна в данном канале!",
            ephemeral=True
        )
        return False
    return True


async def check_svo_channel(interaction: discord.Interaction) -> bool:
    """Проверка что команда выполняется в канале СВО"""
    if interaction.channel_id != SVO_CHANNEL_ID:
        await interaction.response.send_message(
            f"❌ Эта команда доступна только в канале <#{SVO_CHANNEL_ID}>!",
            ephemeral=True
        )
        return False
    return True


def update_yt_dlp():
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"])
        logger.info("[UPDATE] yt-dlp успешно обновлен")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"[UPDATE] Ошибка обновления yt-dlp: {e}")
        return False


def check_dependencies():
    try:
        from importlib.metadata import version, PackageNotFoundError
        yt_dlp_version = version("yt-dlp")
        logger.info(f"[DEPS] yt-dlp version: {yt_dlp_version}")
    except ImportError:
        logger.warning("[DEPS] Не удалось проверить версию yt-dlp: importlib.metadata недоступен")
    except PackageNotFoundError:
        logger.warning("[DEPS] yt-dlp не установлен")
    except Exception as e:
        logger.warning(f"[DEPS] Не удалось проверить версию yt-dlp: {e}")


def check_youtube_access():
    import urllib.request
    import socket
    try:
        socket.setdefaulttimeout(10)
        urllib.request.urlopen('https://www.youtube.com', timeout=10)
        logger.info("[NETWORK] YouTube доступен")
        return True
    except Exception as e:
        logger.error(f"[NETWORK] Нет доступа к YouTube: {e}")
        return False


@bot.event
async def on_ready():
    logger.info("Проверка зависимостей...")
    check_dependencies()
    update_yt_dlp()

    if not check_youtube_access():
        logger.error("ВНИМАНИЕ: Нет доступа к YouTube. Музыкальные функции могут не работать.")

    if not discord.opus.is_loaded():
        try:
            discord.opus.load_opus('opus')
            logger.info("[INIT] Opus библиотека загружена")
        except OSError as e:
            logger.warning(f"[INIT] Не удалось загрузить Opus из 'opus': {e}")
            try:
                pass
            except Exception as auto_load_e:
                logger.warning(f"[INIT] Автоматическая загрузка Opus не удалась: {auto_load_e}")
        except Exception as e:
            logger.warning(f"[INIT] Неизвестная ошибка при загрузке Opus: {e}")

    if discord.opus.is_loaded():
        logger.info("[INIT] Opus библиотека доступна")
    else:
        logger.warning("[INIT] Opus библиотека не загружена - аудио может не работать")

    await start_background_tasks()

    # --- Запуск анонсера стримов ---
    stream_announcer.start()

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
    bot.loop.create_task(cleanup_task())


async def cleanup_task():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            await musicplayer.cleanup_inactive_players()
        except Exception as e:
            logger.error(f"[CLEANUP TASK] Ошибка: {e}")
        await asyncio.sleep(300)


@bot.event
async def on_voice_state_update(member, before, after):
    try:
        if member.id != bot.user.id:
            return

        guild = member.guild
        if not guild:
            return

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
    # Логируем все сообщения
    functions.log(
        f'{message.guild} - #{message.channel} - @{message.author}: '
        f'"{functions.replace_mention(message)}"',
        type='message'
    )

    # --- Автоочистка во всех каналах ---
    # Пропускаем ЛС (message.guild is None)
    if message.guild is not None:
        if not message.author.bot and not message.content.startswith("/"):
            try:
                await message.delete()
            except discord.Forbidden:
                logger.warning(
                    f"[CLEANUP] Нет прав удалять сообщения в #{message.channel}"
                )
            except discord.HTTPException as e:
                logger.error(f"[CLEANUP] Ошибка удаления: {e}")

    await bot.process_commands(message)


@bot.event
async def on_member_join(member):
    """Выдача роли новому пользователю"""
    try:
        role = member.guild.get_role(NEW_ROLE_ID)
        if role:
            await member.add_roles(role)
            logger.info(f"[ROLE] Выдана роль {role.name} пользователю {member.name}")
    except Exception as e:
        logger.error(f"[ROLE] Ошибка выдачи роли: {e}")


@bot.event
async def on_member_remove(member):
    """Уведомление о выходе пользователя"""
    try:
        channel = bot.get_channel(LEAVE_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="👋 Пользователь покинул сервер",
                description=f"**{member.name}#{member.discriminator}** покинул сервер.",
                color=discord.Color.red()
            )
            embed.add_field(name="ID", value=member.id, inline=True)
            embed.add_field(name="Был на сервере с", value=member.joined_at.strftime("%d.%m.%Y %H:%M"), inline=True)
            embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
            await channel.send(embed=embed)
    except Exception as e:
        logger.error(f"[LEAVE] Ошибка отправки уведомления: {e}")


@bot.event
async def on_error(event, *args, **kwargs):
    error_msg = traceback.format_exc()
    logger.error(f'Task error: {event},\n{error_msg}')
    user = bot.get_user(303817809253629952)
    if user:
        await user.send(f"```py\n{error_msg}```")


@bot.event
async def on_command_error(ctx, error):
    """Обработчик ошибок команд"""
    if isinstance(error, commands.CommandNotFound):
        return

    logger.error(f"Command error in {ctx.command}: {error}")

    try:
        if ctx.interaction:
            if not ctx.interaction.response.is_done():
                await ctx.interaction.response.send_message(f"❌ Ошибка: {str(error)}", ephemeral=True)
            else:
                await ctx.interaction.followup.send(f"❌ Ошибка: {str(error)}", ephemeral=True)
        else:
            await ctx.reply(f"❌ Ошибка: {str(error)}")
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение об ошибке: {e}")


# --- МУЗЫКАЛЬНЫЕ КОМАНДЫ ---
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


# --- ОСНОВНЫЕ КОМАНДЫ (только в основном канале) ---
@bot.hybrid_command(name='check', guild_ids=[537267521565229056])
@app_commands.check(check_main_channel)
async def check(ctx):
    functions.log(f'Check by {ctx.author}', type='debug')
    await ctx.reply(f'```bash\n{functions.get_online_members(bot)}```', ephemeral=True)


@bot.hybrid_command(name='roulette')
@app_commands.describe(members='Участники')
@app_commands.check(check_main_channel)
async def _roulette(ctx, members: Greedy[discord.Member]):
    if not members:
        await ctx.reply("Список участников пуст", ephemeral=True)
        return
    winner = choice(members)
    await ctx.reply(f'{winner.mention} победил!')


@bot.hybrid_command(name='work')
@app_commands.check(check_main_channel)
async def _work(ctx):
    '''Заработок скуфкоинов'''
    log(f'{ctx.author} /work', type='debug')
    await functions.work(ctx)


@bot.hybrid_command(name='balance')
@app_commands.check(check_main_channel)
async def _balance(ctx):
    '''Проверка баланса'''
    log(f'{ctx.author} /balance', type='debug')
    await functions.balance(ctx)


@bot.hybrid_command(name='fishing')
@app_commands.check(check_main_channel)
async def _fishing(ctx):
    '''Рыбалка'''
    log(f'{ctx.author} /fishing', type='debug')
    await functions.fishing(ctx)


@bot.hybrid_command(name='shop')
@app_commands.check(check_main_channel)
async def _shop(ctx):
    '''Магазин'''
    log(f'{ctx.author} /shop', type='debug')
    await functions.shop(ctx)


@bot.hybrid_command(name='help')
@app_commands.check(check_main_channel)
async def _help(ctx):
    '''Помощь'''
    log(f'{ctx.author} /help', type='debug')
    await functions.help(ctx)


@bot.hybrid_command(name='addmoney')
@app_commands.describe(member="Участник", coins="Количество скуфкоинов")
@app_commands.check(check_main_channel)
async def _addmoney(ctx, member: discord.Member, coins: int):
    await functions.addmoney(ctx, member, coins)


@bot.hybrid_command(name='addfish')
@app_commands.describe(
    member="Участник",
    fish_type="Тип рыбы (cod, salmon, tropical, squid)",
    amount="Количество (по умолчанию 1)"
)
@app_commands.check(check_main_channel)
async def _addfish(ctx, member: discord.Member, fish_type: str, amount: int = 1):
    '''Выдать рыбу пользователю (только для модераторов)'''
    log(f'{ctx.author} /addfish {member} {fish_type} {amount}', type='debug')
    await functions.addfish(ctx, member, fish_type, amount)


@bot.hybrid_command(name='clear', description='Удалить сообщения в канале (только для админов)')
@app_commands.describe(amount='Сколько последних сообщений удалить (0 = все)')
async def _clear(ctx, amount: int = 100):
    """
    Удаляет последние N сообщений в текущем канале.
    amount=0 — удалить все сообщения (в пределах лимита Discord).
    Работает в любом канале.
    """
    # --- Проверка роли или права ---
    has_role = any(role.id == ADMIN_ROLE_ID for role in ctx.author.roles)
    has_perm = ctx.author.guild_permissions.manage_messages

    if not (has_role or has_perm):
        return await ctx.reply(
            "❌ У вас нет прав на использование этой команды!",
            ephemeral=True
        )

    # --- Проверка прав бота ---
    perms = ctx.channel.permissions_for(ctx.guild.me)
    if not (perms.manage_messages and perms.read_message_history):
        return await ctx.reply(
            "❌ У бота нет прав `Manage Messages` или `Read Message History` в этом канале.",
            ephemeral=True
        )

    if amount < 0:
        return await ctx.reply(
            "❌ Количество не может быть отрицательным (0 = все).",
            ephemeral=True
        )

    status_msg = await ctx.reply("🧹 Удаляю сообщения...")

    total_deleted = 0

    try:
        if amount == 0:
            while True:
                deleted = await ctx.channel.purge(
                    limit=100,
                    check=lambda m: m.id != status_msg.id,
                    bulk=True
                )
                total_deleted += len(deleted)
                if len(deleted) < 100:
                    break
        else:
            remaining = amount
            while remaining > 0:
                batch = min(remaining, 100)
                deleted = await ctx.channel.purge(
                    limit=batch,
                    check=lambda m: m.id != status_msg.id,
                    bulk=True
                )
                total_deleted += len(deleted)
                if len(deleted) < batch:
                    break
                remaining -= len(deleted)

        log(
            f'[CLEAR] {ctx.author} удалил {total_deleted} сообщений в #{ctx.channel}',
            type='debug'
        )

        try:
            await status_msg.edit(content=f"✅ Удалено **{total_deleted}** сообщений.")
        except Exception:
            pass

        await asyncio.sleep(5)
        try:
            await status_msg.delete()
        except Exception:
            pass

    except discord.Forbidden:
        logger.error("[CLEAR] Нет прав на удаление")
        try:
            await status_msg.edit(content="❌ У бота нет прав удалять сообщения в этом канале.")
        except Exception:
            pass
    except discord.HTTPException as e:
        logger.error(f"[CLEAR] Ошибка удаления: {e}")
        try:
            await status_msg.edit(content=f"❌ Ошибка: `{e}`")
        except Exception:
            pass


@bot.hybrid_command(name='map')
@app_commands.check(check_main_channel)
async def _map(ctx):
    '''Показать полную карту игры'''
    log(f'{ctx.author} /map', type='debug')
    await functions.show_full_map(ctx)


@bot.hybrid_command(name='mymap')
@app_commands.check(check_main_channel)
async def _mymap(ctx):
    '''Показать карту вокруг вашего персонажа'''
    log(f'{ctx.author} /mymap', type='debug')
    await functions.show_player_map(ctx)


@bot.hybrid_command(name='setposition')
@app_commands.describe(x="X координата (0-49)", y="Y координата (0-49)")
@app_commands.check(check_main_channel)
async def _setposition(ctx, x: int, y: int):
    '''Установить позицию на карте'''
    log(f'{ctx.author} /setposition: {x}, {y}', type='debug')
    await functions.set_position(ctx, x, y)


@bot.hybrid_command(name='position')
@app_commands.check(check_main_channel)
async def _position(ctx):
    '''Показать вашу текущую позицию'''
    log(f'{ctx.author} /position', type='debug')
    await functions.show_position(ctx)


@bot.hybrid_command(name='svogamehelp')
@app_commands.check(check_main_channel)
async def _svogamehelp(ctx):
    '''Помощь по игре специальная военная операция'''
    log(f'{ctx.author} /svogamehelp', type='debug')
    await functions.svogamehelp(ctx)


@bot.hybrid_command(name='svogameprofile')
@app_commands.check(check_main_channel)
async def _svogameprofile(ctx):
    '''Профиль специальной военной операции'''
    log(f'{ctx.author} /svogameprofile', type='debug')
    await functions.svogameprofile(ctx)


# --- МИНИ-ИГРЫ (без проверки канала) ---
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


# --- КОМАНДА СВО ---
class SVOButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="📊 Профиль", style=discord.ButtonStyle.primary)
    async def svo_profile(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔄 Заглушка: Профиль СВО", ephemeral=True)

    @discord.ui.button(label="⚔️ Атака", style=discord.ButtonStyle.danger)
    async def svo_attack(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔄 Заглушка: Атака в СВО", ephemeral=True)

    @discord.ui.button(label="🛒 Магазин", style=discord.ButtonStyle.success)
    async def svo_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔄 Заглушка: Магазин СВО", ephemeral=True)


@bot.tree.command(name="svo", description="Меню игры Специальная Военная Операция")
@app_commands.check(check_svo_channel)
async def svo_command(interaction: discord.Interaction):
    """Открывает эмбед меню с кнопками для игры СВО"""
    embed = discord.Embed(
        title="🎮 Специальная Военная Операция",
        description="Выберите действие:",
        color=discord.Color.dark_green()
    )
    embed.add_field(
        name="📊 Ваш профиль",
        value="Посмотреть свою статистику и прогресс",
        inline=False
    )
    embed.add_field(
        name="⚔️ Сражение",
        value="Атаковать другого игрока",
        inline=False
    )
    embed.add_field(
        name="🛒 Магазин",
        value="Купить оружие и технику",
        inline=False
    )
    embed.set_footer(text="Используйте кнопки ниже для навигации")

    view = SVOButtons()
    await interaction.response.send_message(embed=embed, view=view)


if __name__ == '__main__':
    bot.run(BOT_TOKEN)
import os
import discord
from discord.ext import commands
import time
import db
import buttons
import logging
from embedmusicplayer import *
from embedshop import create_welcome_embed, create_main_embed
from shop import ShopView
from functools import partial
# from snake import Snake
from blackjack import blackjack
from random import *
from emoji import *
from config import pay, cooldown, multiplier, new_worker_balance, fish_data
from discord import FFmpegPCMAudio
from yt_dlp import YoutubeDL, DownloadError
import asyncio

logger = logging.getLogger(__name__)
bjplayers = {}
snakeplayers = {}
music_players = {}

# Укажите полный путь к ffmpeg
FFMPEG_PATH = "./ffmpeg/bin/ffmpeg.exe"  # Для Windows
# FFMPEG_PATH = "/usr/bin/ffmpeg"           # Для Linux/macOS

# Проверка существования файла
if not os.path.exists(FFMPEG_PATH):
    logger.error(f"[FATAL] FFmpeg не найден по пути: {os.path.abspath(FFMPEG_PATH)}")
    raise RuntimeError("FFmpeg не установлен")
else:
    logger.info(f"[INIT] FFmpeg найден: {os.path.abspath(FFMPEG_PATH)}")

FFmpegPCMAudio.executable = FFMPEG_PATH

# Для Linux/macOS
# FFmpegPCMAudio.executable = "/usr/bin/ffmpeg"


def get_online_members(bot):
    gen = bot.get_all_members()
    members = list(bot.get_all_members())
    online_members = [m.name for m in members if m.status != discord.Status.offline]
    return online_members

def replace_mention(message):
    msg = message.content
    for member in message.mentions:
        msg = msg.replace(member.mention, f'@{member}')
    return msg

def log(message: str, *, type: str):
    '''
    [MESSAGE] 2023/Mar/30 12:32:44 PIZZA #bot-commands @RIPtide#4497 ".bj 1 2 3"
    [DEBUG] 2023/Mar/30 12:31:57 work RIPtide#4497
    [DEBUG] 2023/Mar/30 12:32:44 Blackjack RIPtide#4497 Dealer Q
    '''
    date = time.strftime("%Y/%b/%d %H:%M:%S")
    print(f'[{type.upper()}] {date} {message}')

def format_fish_stats(user_id: int) -> str:
    """Форматирует статистику рыбы в строку для Embed."""
    fish_stats = db.get_fishing_stats(user_id)
    return "\n".join(
        f"{fish_data[fish]['emoji']} {fish_data[fish]['name']}: {count}"
        for fish, count in fish_stats.items()
        if count > 0
    ) or "Пусто"
    

async def move(ctx, members):
    # Проверка наличия ролей или прав
    roles = [406211889228546048, 406212152316395574, 406212396806569984, 430721367592140803]
    has_role = any(role in [r.id for r in ctx.author.roles] for role in roles)
    
    if not has_role and not ctx.author.guild_permissions.move_members:
        return await ctx.reply(f'Недостаточно прав на исполнение команды, нужна роль {roles} или права на перемещение участников', ephemeral=True)
    
    for member in members:
        if member.voice is None:  # Проверка, подключен ли участник к голосовому каналу
            return await ctx.reply("Невозможно переместить участника, который не находится в голосовом канале", ephemeral=True)
    
    # Поиск пустого голосового канала
    channel = None
    for voice_channel in ctx.guild.voice_channels:
        if len(voice_channel.members) == 0:
            channel = voice_channel
            break
    
    if channel is None:
        return await ctx.reply("Нет доступных пустых голосовых каналов", ephemeral=True)
    
    # Перемещение участников
    for member in members:
        await member.move_to(channel)
    
    await ctx.reply('Done!', ephemeral=True)

#ПОМОЩЬ
async def help(ctx):
    emb = discord.Embed(title= 'Помощь', colour = discord.Color.light_gray(), )
    emb.set_author(name = ctx.bot.application.name, icon_url = ctx.bot.application.icon)
    emb.add_field(name = '🍉 __Список команд__', value = '```/check``` - список людей на сервере онлайн\n ```/roullete``` - рулетка с игроком\n ```/work``` - работа\n ```/move``` - переместить кого либо\n ```/balance``` - проверить баланс\n ```/fishing``` - рыбалка\n ```/shop``` - магазин\n ```/svogamehelp``` - помощь по миниигре СВО')
    emb.add_field(name = '🎵 ____ВОСПРОИЗВЕДЕНИЕ МУЗЫКИ____', value = '```/play``` - играть музыку\n```/pause``` - поставить на паузу\n```/resume``` - продолжить\n```/stop``` - остановить\n```/queue``` - очередь')
    emb.add_field(name = '❗__НЕ РАБОЧИЕ КОМАНДЫ__❗', value = '~~/svogameprofile - профиль сво~~\n ~~/durak - дурак~~\n ~~/bj - блекджек~~\n ~~/skip - пропустить~~')
    await ctx.reply(embed=emb, ephemeral=True)

# #МУЗЫКАЛЬНЫЙ ПЛЕЕР
def get_music_player(guild_id):
    if guild_id not in music_players:
        music_players[guild_id] = {
            'queue': [],
            'lock': asyncio.Lock(),
            'in_voice': False,
            'voice_channel': None,
            'chat_channel': None,
            'paused': False,
            'yt_options': {
            'format': 'bestaudio/best',
            'ignoreerrors': True,  # Пропускать ошибки
            'quiet': True,         # Убрать лишние логи
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'extract_flat': True,
            'force-ipv4': True,
            'cachedir': False,     # Отключить кэширование
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.youtube.com/'
                },
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            },
            'ffmpeg_options': {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -loglevel debug -nostdin',
            'options': '-vn -sn -dn -b:a 192k -af loudnorm=I=-16:LRA=11:TP=-1.5'
            }
        }
    return music_players[guild_id]

async def yt_query(query):
    loop = asyncio.get_event_loop()
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9'
            }
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            if 'entries' in info:
                info = info['entries'][0]

            # Фильтруем только аудиоформаты с ключом 'acodec'
            audio_formats = [
                f for f in info['formats'] 
                if f.get('acodec') != 'none' and 'acodec' in f
            ]

            # Если нет подходящих форматов, вызываем ошибку
            if not audio_formats:
                raise DownloadError("Нет доступных аудиоформатов")

            # Ищем OPUS или выбираем первый аудиоформат
            best_audio = None
            for f in audio_formats:
                if 'opus' in f['acodec']:
                    best_audio = f
                    break
            if not best_audio:
                best_audio = audio_formats[0]

            return {

            'source': best_audio['url'],
            'title': info['title'],
            'url': info['webpage_url'],
            'duration': info.get('duration', 0),
            'author': info.get('uploader', 'Неизвестный автор'),
            'thumbnail': info.get('thumbnail', '')
            }
        info = await loop.run_in_executor(None, partial(ydl.extract_info, query, download=False))
    except Exception as e:
        logger.error(f"[YT] Ошибка: {str(e)}")
        raise
    
async def play_next(interaction: discord.Interaction):
    try:
        guild = interaction.guild
        player = get_music_player(guild.id)
        voice = guild.voice_client

        async with player['lock']:
            if not player['queue']:
                if voice and voice.is_connected():
                    await voice.disconnect()
                return
            current = player['queue'].pop(0)

        # Ждем освобождения голосового клиента
        while voice.is_playing() or voice.is_paused():
            await asyncio.sleep(0.1)

        def after_playback(error):
            if error:
                logger.error(f"[FFMPEG] Ошибка: {error}")
            asyncio.run_coroutine_threadsafe(play_next(interaction), interaction.client.loop)

        voice.play(
            FFmpegPCMAudio(source=current['source'], executable=FFMPEG_PATH, **player['ffmpeg_options']),
            after=after_playback
        )
        await interaction.followup.send(
            embed=now_playing_embed(current['title'], current['url'], current['duration'], current['author'], current['thumbnail'])
        )

    except Exception as e:
        logger.error(f"Playback failed: {str(e)}")
        await interaction.followup.send("❌ Ошибка воспроизведения. Пропускаю трек.")
        await play_next(interaction)  # Retry

async def play_music(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    try:
        guild = interaction.guild
        user = interaction.user
        voice_client = guild.voice_client

        # Проверка подключения пользователя к голосовому каналу
        if not user.voice:
            await interaction.followup.send(embed=error_embed("Вы не в голосовом канале!"))
            return

        channel = user.voice.channel

        # Подключение/переподключение к каналу
        if not voice_client or not voice_client.is_connected():
            voice_client = await channel.connect()
        elif voice_client.channel != channel:
            await voice_client.move_to(channel)

        # Добавление трека в очередь
        track = await yt_query(query)
        track['added_by'] = user.id

        player = get_music_player(guild.id)
        async with player['lock']:
            player['queue'].append(track)

        if not voice_client.is_playing():
            await play_next(interaction)
        else:
            await interaction.followup.send(f"Добавлено в очередь: {track['title']}")

    except Exception as e:
        await interaction.followup.send(embed=error_embed(f"❌ Ошибка: {str(e)}"))

async def skip_music(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
        voice = interaction.guild.voice_client

        if not voice or not voice.is_connected():
            await interaction.followup.send(embed=error_embed("🔇 Бот не подключен"))
            return

        player = get_music_player(interaction.guild.id)

        if voice.is_playing() or voice.is_paused():
            voice.stop()
            await asyncio.sleep(1.5)  # Ожидание завершения FFmpeg

            async with player['lock']:
                if player['queue']:
                    await play_next(interaction)
                    await interaction.followup.send(embed=discord.Embed(
                        description="⏭ Трек пропущен",
                        color=discord.Color.green()
                    ))
                else:
                    await interaction.followup.send(embed=discord.Embed(
                        description="🎶 Очередь пуста!",
                        color=discord.Color.blue()
                    ))
                    if interaction.guild.id in music_players:
                        del music_players[interaction.guild.id]
                    await voice.disconnect()
        else:
            await interaction.followup.send(embed=error_embed("Нет активного трека"))

    except Exception as e:
        logger.error(f"[SKIP] Ошибка: {str(e)}", exc_info=True)
        await interaction.followup.send(embed=error_embed("⚠️ Внутренняя ошибка"))

async def pause_music(ctx):
    try:
        voice = ctx.voice_client
        player = get_music_player(ctx.guild.id)
        
        # Проверка подключения бота
        if not voice or not voice.is_connected():
            return await ctx.send(embed=error_embed("🔇 Бот не подключен к голосовому каналу"))
            
        # Проверка текущего состояния
        if voice.is_playing():
            voice.pause()
            player['paused'] = True
            await ctx.send(embed=discord.Embed(
                title="⏸ Пауза",
                description="Воспроизведение приостановлено",
                color=discord.Color.orange()
            ).set_footer(text="Используйте /resume для продолжения"))
            
        elif voice.is_paused():
            await ctx.send(embed=error_embed("⚠️ Воспроизведение уже на паузе!"))
            
        else:
            await ctx.send(embed=error_embed("❌ Нет активного воспроизведения"))

    except Exception as e:
        logger.error(f"[PAUSE] Critical error: {str(e)}", exc_info=True)
        await ctx.send(embed=error_embed(f"🚨 Ошибка: {str(e)}"))

async def resume_music(ctx):
    try:
        voice = ctx.voice_client
        player = get_music_player(ctx.guild.id)
        
        # Проверка подключения бота
        if not voice or not voice.is_connected():
            return await ctx.send(embed=error_embed("🔇 Бот не подключен к голосовому каналу"))
            
        # Проверка текущего состояния
        if voice.is_paused():
            voice.resume()
            player['paused'] = False
            await ctx.send(embed=discord.Embed(
                title="▶ Возобновлено",
                description="Воспроизведение продолжается",
                color=discord.Color.green()
            ))
            
        elif voice.is_playing():
            await ctx.send(embed=error_embed("⚠️ Воспроизведение уже активно!"))
            
        else:
            await ctx.send(embed=error_embed("❌ Нет трека на паузе"))

    except Exception as e:
        logger.error(f"[RESUME] Critical error: {str(e)}", exc_info=True)
        await ctx.send(embed=error_embed(f"🚨 Ошибка: {str(e)}"))

async def stop_music(ctx):
    player = get_music_player(ctx.guild.id)
    guild_id = ctx.guild.id
    async with player['lock']:  # Захват блокировки
        if guild_id in music_players:
            del music_players[guild_id]
        voice = ctx.voice_client
        if voice and voice.is_connected():
            await voice.disconnect()
            player['queue'].clear()  # Очистка очереди
            await ctx.send("Воспроизведение остановлено")

async def show_queue(ctx):
    player = get_music_player(ctx.guild.id)
    await ctx.send(embed=queue_embed(player['queue']))

# Обработчики ошибок
async def on_voice_state_update(member, before, after):
    if member.bot and not after.channel:
        guild_id = member.guild.id
        if guild_id in music_players:
            del music_players[guild_id]

async def handle_play_error(ctx, error):
    if isinstance(error, DownloadError):
        await ctx.send("Ошибка загрузки трека")
    elif isinstance(error, commands.CommandInvokeError):
        await ctx.send("Ошибка выполнения команды")
#БАЛАНС
async def balance(ctx):
    emb = discord.Embed(title = '```🍉IONOTEKA BANK🍉```', colour = discord.Color.brand_green())
    emb.set_author(name = ctx.author.name, icon_url = ctx.author.avatar.url)
    if db.get_balance(ctx.author.id) <= 4:
        emb.add_field(name = 'Ваш баланс:', value = f'{db.get_balance(ctx.author.id)} скуфкоина <:skufcoin:1248834544233353227>', )
        return await ctx.reply(embed=emb, ephemeral=True)
    emb.add_field(name = 'Ваш баланс:', value = f'{db.get_balance(ctx.author.id)} скуфкоинов <:skufcoin:1248834544233353227>', )
    await ctx.reply(embed=emb, ephemeral=True)

#ВЫДАТЬ ДЕНЬГИ
async def addmoney(ctx, member: discord.Member, coins: int):
    roles = [406211889228546048, 406212152316395574, 406212396806569984, 430721367592140803]
    if not any(role in [r.id for r in ctx.author.roles] for role in roles) and not ctx.author.guild_permissions.administrator:
        return await ctx.reply('Недостаточно прав!', ephemeral=True)
    
    if not db.is_user_exists(member.id):
        return await ctx.reply('Пользователь не зарегистрирован!', ephemeral=True)
    
    db.add_money(member.id, coins)
    await ctx.reply(f'Успешно выдано {coins} скуфкоинов пользователю {member.mention}')

#РАБОТА
async def work(ctx):
    user_id = ctx.author.id

    if not db.is_user_exists(user_id):
        db.register_user(user_id)
        return await ctx.reply(f'Новый работник! Вам выдали начальный капитал: {new_worker_balance} скуфкоинов <:skufcoin:1248834544233353227>')
    
    remaining = db.get_cooldown(user_id, 'work')
    print(f"[DEBUG] Кулдаун работы для {user_id}: {remaining} сек.")  # Логирование
    
    if remaining > 0:
        cd = f"{int(remaining // 60)} мин. {int(remaining % 60)} сек."
        return await ctx.reply(f'{ctx.author.mention}, устал и не может работать. Кулдаун: {cd}')
    
    db.update_balance(user_id, pay['work'] * multiplier)
    db.set_cooldown(user_id, 'work', cooldown['work'])
    await ctx.reply(f'{ctx.author.mention} сходил на работу! +100 <:skufcoin:1248834544233353227>')

#МАГАЗИН
async def shop(ctx):
    user = ctx.author
    
    if not db.is_user_exists(user.id):
        db.register_user(user.id)
        return await ctx.reply(
            embed=create_welcome_embed(ctx.bot),
            ephemeral=True
        )
    
    view = ShopView(user)
    await ctx.reply(
        embed=create_main_embed(user),
        view=view,
        ephemeral=True
    )
    
#БЛЕКДЖЕК
async def bj(ctx, bet):
    if ctx.author.id in bjplayers and bjplayers[ctx.author.id].is_playing():
        return await ctx.reply(f'{ctx.author.mention}, Ты уже в игре!')
    if not db.is_enought(ctx.author.id, bet):
        return await ctx.reply(f'{ctx.author.mention}, недостаточно скуфкоинов <:skufcoin:1248834544233353227>')
    
    bjplayers[ctx.author.id] = blackjack(ctx.author, bet)

    if bjplayers[ctx.author.id].is_playing(): # рисовать кнопки, если партия продолжается
        view = await buttons.bj_buttons(ctx, bjplayers)
        return await ctx.reply(blackjack.prepare_message(bjplayers[ctx.author.id]), view=view)
    return await ctx.reply(blackjack.prepare_message(bjplayers[ctx.author.id]))


#РЫБАЛКА
async def fishing(ctx):
    user_id = ctx.author.id
    
    # Проверка регистрации
    if not db.is_user_exists(user_id):
        db.register_user(user_id)
        return await ctx.reply(f'Новый рыбачок! Вам выдали начальный капитал: 100 скуфкоинов <:skufcoin:1248834544233353227>')

    # Проверка кулдауна
    remaining = db.get_cooldown(user_id, 'fishing')
    if remaining > 0:
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        cd = f"{minutes} мин. {seconds} сек."
        return await ctx.reply(f"⏳ Подождите {cd}!", ephemeral=True)  # return здесь!

    # Ловля рыбы
    caught_fish = db.fishing(user_id)  # Возвращает тип рыбы
    
    # Установка кулдауна (передаем длительность, а не время)
    db.set_cooldown(user_id, 'fishing', cooldown['fishing'])

    # Создание embed
    emb = discord.Embed(
        title="<:Fishing_Rod:1327154633818509322> Результаты рыбалки",
        color=discord.Color.blue(),
        description=f"{fish_data[caught_fish]['emoji']} Вы поймали {fish_data[caught_fish]['name']}!"
    )
    emb.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
    
    # Статистика рыбы
    stats_text = format_fish_stats(user_id)
    emb.add_field(name="Ваш улов", value=stats_text, inline=False)

    await ctx.reply(embed=emb, ephemeral=True)


# async def snakemsg(ctx):
#     if ctx.author.id in snakeplayers and snakeplayers[ctx.author.id].status == 'playing':
#         return await ctx.reply(f'{ctx.author.mention}, Ты уже в игре!')
    
#     snakeplayers[ctx.author.id] = Snake(ctx.author)
#     if snakeplayers[ctx.author.id].status == 'playing': # рисовать кнопки, если партия продолжается
#         view = await buttons.snake_buttons(ctx, snakeplayers)
#         return await ctx.reply(Snake.prepare_message(snakeplayers[ctx.author.id]), view=view)
#     return await ctx.reply(Snake.prepare_message(snakeplayers[ctx.author.id]))

#CВО_ИГРА==========================================================================================================================================================================
#СВО_ПОМОЩЬ
async def svogamehelp(ctx):
    emb = discord.Embed(title= 'Помощь по мини игре СВО', colour = discord.Color.light_gray(), )
    emb.set_author(name = ctx.bot.application.name, icon_url = ctx.bot.application.icon)
    emb.add_field(name = '🍉Список команд', value = '/svogameprofile')
    emb.add_field(name= 'Описание', value= 'Открыть профиль')
    await ctx.reply(embed=emb, ephemeral=True)

#СВО_ПРОФИЛЬ
async def svogameprofile(ctx):
    emb = discord.Embed(title= 'Special Military Operation', colour = discord.Color.light_gray(), )
    emb.set_author(name = ctx.bot.application.name, icon_url = ctx.bot.application.icon)
    emb.add_field(name = '🍉Список команд', value = '__Профиль__\n Уровень:\n Опыт:\n __Статы__\n Атака:\n Защита:\n ♥ Жизнь:')
    emb.add_field(name= 'Экипировка', value=None)
    emb.add_field(name= 'Деньги', value= f'{db.balanceid(ctx.author.id)} скуфкоинов <:skufcoin:1248834544233353227>')
    await ctx.reply(embed=emb, ephemeral=True)
    

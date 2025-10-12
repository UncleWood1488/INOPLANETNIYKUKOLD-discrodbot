import os
import traceback
import discord
from discord.ext import commands
import time
import db
import yt_dlp
import buttons
import logging
from embedmusicplayer import *
from embedshop import *
from shop import ShopView
from functools import partial
from blackjack import blackjack
from random import randint, choice
from emoji import *
from config import (
    pay, cooldown, multiplier, new_worker_balance, fish_data,
    MOD_ROLE_IDS, FFMPEG_PATH, FFMPEG_OPTIONS
)
from discord import FFmpegPCMAudio
from yt_dlp import YoutubeDL, DownloadError
import asyncio

logger = logging.getLogger(__name__)
bjplayers = {}
snakeplayers = {}
music_players = {}
music_lock = asyncio.Lock()  # Глобальный Lock для синхронизации

# Проверка FFmpeg
if not os.path.exists(FFMPEG_PATH):
    logger.error(f"[FATAL] FFmpeg не найден: {os.path.abspath(FFMPEG_PATH)}")
    raise RuntimeError("FFmpeg не установлен")
else:
    logger.info(f"[INIT] FFmpeg найден: {os.path.abspath(FFMPEG_PATH)}")

FFmpegPCMAudio.executable = FFMPEG_PATH

# Логирование
def log(message: str, type: str = 'info'):
    if type == 'error':
        logger.error(message)
    elif type == 'debug':
        logger.debug(message)
    else:
        logger.info(message)

#region Утилиты
# Утилиты
def get_online_members(bot):
    return [m.name for m in bot.get_all_members() if m.status != discord.Status.offline]

def replace_mention(message):
    return message.content.replace(
        message.mentions[0].mention, 
        f'@{message.mentions[0].name}'
    ) if message.mentions else message.content

#region Админские команды
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
#endregion

#region Музыкальный плеер
async def get_music_player(guild_id):
    """Получить или создать музыкального плеера для гильдии"""
    async with music_lock:
        if guild_id not in music_players:
            music_players[guild_id] = {
                'queue': [],
                'lock': asyncio.Lock(),
                'voice_channel': None,
                'paused': False,
                'volume': 0.8,
                'now_playing': None,
                'loop_mode': 'none',  # 'none', 'queue', 'one'
                'current_track': None
            }
        return music_players[guild_id]

async def yt_query(query: str):
    # Упрощенные настройки для избежания ошибок
    ytdl_options = {
        'format': 'bestaudio/best',
        'outtmpl': '%(extractor)s-%(id)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
        'force-ipv4': True,
        'cachedir': False,
    }

    try:
        # Обход ошибки импорта через прямое использование низкоуровневых функций
        import yt_dlp
        from yt_dlp import YoutubeDL
        
        # Создаем экземпляр с обработкой ошибок
        ytdl = YoutubeDL(ytdl_options)
        info = ytdl.extract_info(query, download=False)
        ytdl.close()
            
        if 'entries' in info:
            entries = info['entries']
            if not entries:
                raise yt_dlp.DownloadError("🔍 Нет результатов поиска")
            track_info = entries[0]
        else:
            track_info = info

        if not track_info.get('url'):
            raise yt_dlp.DownloadError("🔇 Аудиопоток недоступен")

        return {
            'source': track_info['url'],
            'title': track_info.get('title', 'Без названия')[:200],
            'duration': track_info.get('duration', 0),
            'url': track_info.get('webpage_url', query),
            'author': track_info.get('uploader', 'Неизвестен')[:100],
            'thumbnail': track_info.get('thumbnail') or 
                       f"https://img.youtube.com/vi/{track_info.get('id', '')}/hqdefault.jpg"
        }

    except ImportError as e:
        logger.error(f"[YTDL] Ошибка импорта: {str(e)}")
        raise yt_dlp.DownloadError("❌ Проблема с библиотекой yt-dlp. Попробуйте переустановить.")
    
    except Exception as e:
        logger.error(f"[YTDL] Общая ошибка: {str(e)}")
        raise yt_dlp.DownloadError("⚠️ Ошибка обработки трека")
    
async def yt_playlist_query(query: str, max_tracks: int = 50):
    """Оптимизированная загрузка плейлиста"""
    ytdl_options = {
        'format': 'bestaudio/best',
        'outtmpl': '%(extractor)s-%(id)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': False,
        'nocheckcertificate': True,
        'ignoreerrors': True,  # Игнорируем ошибки для приватных видео
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,  # Только метаданные, без информации о форматах
        'playlistend': max_tracks,  # Ограничиваем количество треков
        'source_address': '0.0.0.0',
        'force-ipv4': True,
        'cachedir': False,
    }

    try:
        import yt_dlp
        from yt_dlp import YoutubeDL
        
        ytdl = YoutubeDL(ytdl_options)
        info = await asyncio.to_thread(ytdl.extract_info, query, download=False)
        ytdl.close()

        if not info:
            raise yt_dlp.DownloadError("🔍 Плейлист не найден или пуст")

        tracks = []
        if 'entries' in info:
            for entry in info['entries']:
                if entry and entry.get('url'):
                    try:
                        # Для каждого трека получаем полную информацию отдельно
                        track_info = await yt_query(entry['url'])
                        if track_info:
                            tracks.append(track_info)
                    except Exception as e:
                        logger.warning(f"[PLAYLIST] Пропуск трека {entry.get('title', 'Unknown')}: {str(e)}")
                        continue

        if not tracks:
            raise yt_dlp.DownloadError("❌ Не удалось загрузить ни одного трека из плейлиста")

        return tracks

    except Exception as e:
        logger.error(f"[PLAYLIST] Ошибка загрузки плейлиста: {str(e)}")
        raise yt_dlp.DownloadError(f"⚠️ Ошибка загрузки плейлиста: {str(e)}")

async def play_music(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    try:
        if not interaction.user.voice:
            return await interaction.followup.send(embed=error_embed("🔇 Подключитесь к голосовому каналу!"))
        
        channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client

        try:
            if voice_client and voice_client.is_connected():
                if voice_client.channel != channel:
                    await voice_client.move_to(channel)
            else:
                voice_client = await channel.connect()
        except discord.ClientException as e:
            return await interaction.followup.send(embed=error_embed(f"❌ Ошибка подключения: {str(e)}"))

        # Определяем тип запроса (плейлист или одиночный трек)
        is_playlist = any(keyword in query.lower() for keyword in ['playlist', 'list='])
        
        try:
            if is_playlist:
                # Отправляем сообщение о начале загрузки плейлиста
                loading_msg = await interaction.followup.send("🔄 Загружаю плейлист... Это может занять некоторое время", ephemeral=True)
                
                tracks = await yt_playlist_query(query)
                
                player = await get_music_player(interaction.guild.id)
                added_count = 0
                async with player['lock']:
                    for track in tracks:
                        track['added_by'] = interaction.user.id
                        player['queue'].append(track)
                        added_count += 1

                # Обновляем сообщение о результате
                await loading_msg.edit(content=f"✅ Добавлено {added_count} треков из плейлиста")
                
            else:
                # Одиночный трек
                track = await yt_query(query)
                track['added_by'] = interaction.user.id

                player = await get_music_player(interaction.guild.id)
                async with player['lock']:
                    player['queue'].append(track)

                await interaction.followup.send(
                    f"🎵 Добавлено в очередь: **{track['title']}**", 
                    ephemeral=True
                )

        except DownloadError as e:
            return await interaction.followup.send(embed=error_embed(f"❌ {str(e)}"))

        # Если ничего не играет, начинаем воспроизведение
        if not voice_client.is_playing():
            await play_next(interaction)

    except Exception as e:
        logger.error(f"[PLAY] Ошибка: {str(e)}")
        await interaction.followup.send(embed=error_embed("⚠️ Ошибка воспроизведения"))

# Добавим отдельную команду для плейлистов
async def play_playlist(interaction: discord.Interaction, playlist_url: str):
    """Отдельная команда для плейлистов"""
    await interaction.response.defer()
    try:
        if not interaction.user.voice:
            return await interaction.followup.send(embed=error_embed("🔇 Подключитесь к голосовому каналу!"))
        
        channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client

        try:
            if voice_client and voice_client.is_connected():
                if voice_client.channel != channel:
                    await voice_client.move_to(channel)
            else:
                voice_client = await channel.connect()
        except discord.ClientException as e:
            return await interaction.followup.send(embed=error_embed(f"❌ Ошибка подключения: {str(e)}"))

        # Отправляем сообщение о начале загрузки
        loading_msg = await interaction.followup.send("🔄 Загружаю плейлист... Это может занять некоторое время")

        try:
            tracks = await yt_playlist_query(playlist_url)
            
            player = await get_music_player(interaction.guild.id)
            added_count = 0
            async with player['lock']:
                for track in tracks:
                    track['added_by'] = interaction.user.id
                    player['queue'].append(track)
                    added_count += 1

            # Обновляем сообщение о результате
            embed = discord.Embed(
                title="✅ Плейлист добавлен",
                description=f"Добавлено {added_count} треков в очередь",
                color=discord.Color.green()
            )
            await loading_msg.edit(content=None, embed=embed)

        except DownloadError as e:
            await loading_msg.edit(content=f"❌ {str(e)}")

        # Если ничего не играет, начинаем воспроизведение
        if not voice_client.is_playing():
            await play_next(interaction)

    except Exception as e:
        logger.error(f"[PLAYLIST] Ошибка: {str(e)}")
        await interaction.followup.send(embed=error_embed("⚠️ Ошибка загрузки плейлиста"))

async def play_music(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    try:
        if not interaction.user.voice:
            return await interaction.followup.send(embed=error_embed("🔇 Подключитесь к голосовому каналу!"))
        
        channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client

        try:
            if voice_client and voice_client.is_connected():
                if voice_client.channel != channel:
                    await voice_client.move_to(channel)
            else:
                voice_client = await channel.connect()
        except discord.ClientException as e:
            return await interaction.followup.send(embed=error_embed(f"❌ Ошибка подключения: {str(e)}"))

        try:
            track = await yt_query(query)
            track['added_by'] = interaction.user.id
        except DownloadError as e:
            return await interaction.followup.send(embed=error_embed(f"❌ {str(e)}"))

        player = await get_music_player(interaction.guild.id)
        async with player['lock']:
            player['queue'].append(track)

        # УБРАНЫ ДУБЛИРУЮЩИЕ ТЕКСТОВЫЕ СООБЩЕНИЯ
        if not voice_client.is_playing():
            await play_next(interaction)
        else:
            # Только ephemeral сообщение для добавления в очередь
            await interaction.followup.send(
                f"🎵 Добавлено в очередь: **{track['title']}**", 
                ephemeral=True
            )

    except Exception as e:
        logger.error(f"[PLAY] Ошибка: {str(e)}")
        await interaction.followup.send(embed=error_embed("⚠️ Ошибка воспроизведения"))

async def play_next(interaction: discord.Interaction):
    try:
        guild = interaction.guild
        player = await get_music_player(guild.id)
        voice = guild.voice_client

        async with player['lock']:
            # Проверяем режим повтора
            if player['loop_mode'] == 'one' and player['current_track']:
                # Повтор одного трека - используем текущий трек
                current = player['current_track']
            elif player['loop_mode'] == 'queue' and player['queue']:
                # Повтор плейлиста - перемещаем текущий трек в конец
                if player['current_track']:
                    player['queue'].append(player['current_track'])
                current = player['queue'].pop(0) if player['queue'] else None
            else:
                # Обычный режим - берем следующий трек
                current = player['queue'].pop(0) if player['queue'] else None
            
            # Сохраняем текущий трек
            player['current_track'] = current

            if not current:
                # Если треков нет, отключаемся
                if voice and voice.is_connected():
                    await voice.disconnect()
                    music_players.pop(guild.id, None)
                return

        if not voice or not voice.is_connected():
            return

        def after_playback(error):
            if error:
                logger.error(f"[FFMPEG] Ошибка: {error}")
            asyncio.run_coroutine_threadsafe(play_next(interaction), interaction.client.loop)

        voice.play(
            FFmpegPCMAudio(
                source=current['source'],
                executable=FFMPEG_PATH,
                **FFMPEG_OPTIONS
            ),
            after=after_playback
        )
        
        # Отправляем embed с информацией о режиме повтора
        embed, view = now_playing_embed(
            title=current['title'],
            url=current['url'],
            duration=current['duration'],
            author=current.get('author', 'Неизвестен'),
            thumbnail=current.get('thumbnail', ''),
            guild_id=guild.id,
            loop_mode=player['loop_mode']
        )
        
        try:
            await interaction.followup.send(embed=embed, view=view)
        except discord.NotFound:
            logger.warning("[PLAYER] Interaction уже завершен, не отправляем embed")

    except Exception as e:
        logger.error(f"[PLAYER] Ошибка: {str(e)}")
        try:
            await interaction.followup.send("⏭ Пропуск трека из-за ошибки", ephemeral=True)
        except:
            pass
        await play_next(interaction)

async def pause_music(interaction: discord.Interaction):
    """Приостановить воспроизведение"""
    if not await check_voice_channel(interaction):
        return
    
    voice_client = interaction.guild.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await interaction.response.send_message("⏸️ Воспроизведение приостановлено")
    else:
        await interaction.response.send_message("⚠️ Нет активного воспроизведения", ephemeral=True)

async def resume_music(interaction: discord.Interaction):
    """Возобновить воспроизведение"""
    if not await check_voice_channel(interaction):
        return
    
    voice_client = interaction.guild.voice_client
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await interaction.response.send_message("▶️ Воспроизведение возобновлено")
    else:
        await interaction.response.send_message("⚠️ Воспроизведение не приостановлено", ephemeral=True)

async def skip_music(interaction: discord.Interaction):
    """Пропустить текущий трек"""
    if not await check_voice_channel(interaction):
        return
    
    voice_client = interaction.guild.voice_client
    if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
        voice_client.stop()
        await interaction.response.send_message("⏭️ Трек пропущен")
    else:
        await interaction.response.send_message("⚠️ Нет активного воспроизведения", ephemeral=True)

async def stop_music(interaction: discord.Interaction):
    """Остановить воспроизведение и очистить очередь"""
    if not await check_voice_channel(interaction):
        return
    
    voice_client = interaction.guild.voice_client
    if voice_client and voice_client.is_connected():
        # Очищаем очередь
        if interaction.guild.id in music_players:
            async with music_players[interaction.guild.id]['lock']:
                music_players[interaction.guild.id]['queue'].clear()
        
        await voice_client.disconnect()
        await interaction.response.send_message("⏹️ Воспроизведение остановлено")
    else:
        await interaction.response.send_message("⚠️ Бот не подключен к голосовому каналу", ephemeral=True)
        
# Добавим команды для управления повтором:
async def loop_queue(interaction: discord.Interaction):
    """Включить/выключить повтор плейлиста"""
    if not await check_voice_channel(interaction):
        return
    
    guild_id = interaction.guild.id
    if guild_id in music_players:
        async with music_players[guild_id]['lock']:
            if music_players[guild_id]['loop_mode'] == 'queue':
                music_players[guild_id]['loop_mode'] = 'none'
                await interaction.response.send_message("🔁 Повтор плейлиста выключен")
            else:
                music_players[guild_id]['loop_mode'] = 'queue'
                await interaction.response.send_message("🔁 Повтор плейлиста включен")
    else:
        await interaction.response.send_message("⚠️ Нет активного плеера", ephemeral=True)

async def loop_one(interaction: discord.Interaction):
    """Включить/выключить повтор текущего трека"""
    if not await check_voice_channel(interaction):
        return
    
    guild_id = interaction.guild.id
    if guild_id in music_players:
        async with music_players[guild_id]['lock']:
            if music_players[guild_id]['loop_mode'] == 'one':
                music_players[guild_id]['loop_mode'] = 'none'
                await interaction.response.send_message("🔂 Повтор трека выключен")
            else:
                music_players[guild_id]['loop_mode'] = 'one'
                await interaction.response.send_message("🔂 Повтор трека включен")
    else:
        await interaction.response.send_message("⚠️ Нет активного плеера", ephemeral=True)

# В functions.py обновим функцию queue_music для использования эмбеда с кнопками:
async def queue_music(interaction: discord.Interaction):
    """Показать очередь треков"""
    if interaction.guild.id in music_players:
        queue = music_players[interaction.guild.id]['queue']
        loop_mode = music_players[interaction.guild.id]['loop_mode']
        embed = queue_embed(queue, loop_mode)  # Теперь возвращает только embed без view
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("⚠️ Очередь пуста", ephemeral=True)

async def shuffle_music(interaction: discord.Interaction):
    """Перемешать очередь"""
    if not await check_voice_channel(interaction):
        return
    
    import random
    guild_id = interaction.guild.id
    if guild_id in music_players:
        async with music_players[guild_id]['lock']:
            queue = music_players[guild_id]['queue']
            if len(queue) > 1:
                random.shuffle(queue)
                await interaction.response.send_message("🔀 Очередь перемешана")
            else:
                await interaction.response.send_message("⚠️ В очереди недостаточно треков", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ Очередь пуста", ephemeral=True)

async def check_voice_channel(interaction: discord.Interaction) -> bool:
    """Проверка что пользователь в голосовом канале с ботом"""
    if not interaction.user.voice:
        await interaction.response.send_message(
            "🔇 Вы должны быть в голосовом канале!", 
            ephemeral=True
        )
        return False

    voice_client = interaction.guild.voice_client
    if not voice_client or not voice_client.is_connected():
        await interaction.response.send_message(
            "🔇 Бот не подключен к голосовому каналу!", 
            ephemeral=True
        )
        return False

    if interaction.user.voice.channel != voice_client.channel:
        await interaction.response.send_message(
            "🔇 Вы должны быть в том же голосовом канале что и бот!", 
            ephemeral=True
        )
        return False

    return True

async def cleanup_inactive_players():
    """Очистка неактивных музыкальных плееров"""
    try:
        current_time = time.time()
        guilds_to_remove = []
        
        for guild_id, player_data in music_players.items():
            # Проверяем, есть ли голосовое подключение и активность
            voice_client = None
            # Получаем голосовой клиент через глобальную переменную
            from main import bot  # Импортируем bot из main
            guild = bot.get_guild(guild_id)
            if guild:
                voice_client = guild.voice_client
            
            # Условия для очистки:
            # 1. Нет голосового подключения И очередь пуста
            # 2. Или прошло более 5 минут с последней активности
            should_remove = (
                (not voice_client or not voice_client.is_connected()) and 
                not player_data['queue']
            )
            
            if should_remove:
                guilds_to_remove.append(guild_id)
        
        # Удаляем отмеченные гильдии
        for guild_id in guilds_to_remove:
            music_players.pop(guild_id, None)
            logger.info(f"[CLEANUP] Удален неактивный плеер для гильдии {guild_id}")
            
    except Exception as e:
        logger.error(f"[CLEANUP] Ошибка очистки: {str(e)}")
#endregion

#region Экономика
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
#endregion

#region Мини-игры
async def bj(ctx, bet: int):
    try:
        if ctx.author.id in bjplayers:
            return await ctx.reply("⚠️ Вы уже в игре!", ephemeral=True)
        
        if not db.is_enought(ctx.author.id, bet):
            return await ctx.reply("❌ Недостаточно средств!", ephemeral=True)

        game = blackjack(ctx.author, bet)
        bjplayers[ctx.author.id] = game
        view = await buttons.bj_buttons(ctx, game)
        await ctx.reply(game.prepare_message(), view=view)

    except Exception as e:
        logger.error(f"[BJ] Ошибка: {str(e)}")
        await ctx.reply("⚠️ Ошибка запуска игры", ephemeral=True)
    finally:
        if ctx.author.id in bjplayers:
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
        await ctx.reply(embed=create_fish_embed(ctx.author, caught_fish))

    except Exception as e:
        logger.error(f"[FISHING] Ошибка: {str(e)}")
        await ctx.reply("🎣 Ошибка рыбалки", ephemeral=True)
#endregion

#region Хелперы
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
#endregion

# Очистка данных при выходе из голосового канала
async def on_voice_state_update(member, before, after):
    if member.bot and not after.channel:
        guild_id = member.guild.id
        if guild_id in music_players:
            music_players.pop(guild_id, None)
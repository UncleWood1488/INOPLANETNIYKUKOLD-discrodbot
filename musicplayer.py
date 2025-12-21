import os
import traceback
import discord
from discord.ext import commands
import yt_dlp
import logging
from embedmusicplayer import *
import asyncio
from config import FFMPEG_PATH, FFMPEG_OPTIONS
from discord import FFmpegPCMAudio
from yt_dlp import YoutubeDL, DownloadError

logger = logging.getLogger(__name__)
music_players = {}
music_lock = asyncio.Lock()

bot = None

def setup_bot(bot_instance):
    global bot
    bot = bot_instance

# Проверка FFmpeg
if not os.path.exists(FFMPEG_PATH):
    logger.error(f"[FATAL] FFmpeg не найден: {os.path.abspath(FFMPEG_PATH)}")
    raise RuntimeError("FFmpeg не установлен")
else:
    logger.info(f"[INIT] FFmpeg найден: {os.path.abspath(FFMPEG_PATH)}")

FFmpegPCMAudio.executable = FFMPEG_PATH

# Улучшенные настройки yt-dlp для решения проблем с сетью
def get_ytdl_options():
    return {
        'format': 'bestaudio/best',
        'outtmpl': '%(extractor)s-%(id)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
        'force-ipv4': True,
        'cachedir': False,
        'retries': 10,
        'fragment_retries': 10,
        'skip_unavailable_fragments': True,
        'extract_flat': False,
        'http_chunk_size': 10485760,
        'continuedl': True,
        'nopart': True,
        'noresizebuffer': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Accept-Encoding': 'gzip,deflate',
            'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
            'Connection': 'keep-alive',
        }
    }

def get_playlist_ytdl_options():
    options = get_ytdl_options()
    options.update({
        'noplaylist': False,
        'extract_flat': True,
        'ignoreerrors': True,
        'playlistend': 50,
    })
    return options

async def yt_query(query: str, max_retries: int = 3):
    """Улучшенная функция запроса с повторными попытками"""
    for attempt in range(max_retries):
        try:
            ytdl_options = get_ytdl_options()
            
            ytdl = YoutubeDL(ytdl_options)
            info = await asyncio.to_thread(ytdl.extract_info, query, download=False)
            
            if not info:
                raise DownloadError("🔍 Нет результатов поиска")

            if 'entries' in info:
                entries = info['entries']
                if not entries:
                    raise DownloadError("🔍 Нет результатов поиска")
                track_info = entries[0]
            else:
                track_info = info

            if not track_info.get('url'):
                raise DownloadError("🔇 Аудиопоток недоступен")

            return {
                'source': track_info['url'],
                'title': track_info.get('title', 'Без названия')[:200],
                'duration': track_info.get('duration', 0),
                'url': track_info.get('webpage_url', query),
                'author': track_info.get('uploader', 'Неизвестен')[:100],
                'thumbnail': track_info.get('thumbnail') or 
                           f"https://img.youtube.com/vi/{track_info.get('id', '')}/hqdefault.jpg"
            }

        except Exception as e:
            logger.warning(f"[YTDL] Попытка {attempt + 1}/{max_retries} не удалась: {str(e)}")
            if attempt == max_retries - 1:
                logger.error(f"[YTDL] Все попытки не удались: {str(e)}")
                raise DownloadError(f"⚠️ Ошибка обработки трека после {max_retries} попыток: {str(e)}")
            await asyncio.sleep(2)

async def yt_playlist_query(query: str, max_tracks: int = 50, max_retries: int = 2):
    """Улучшенная загрузка плейлиста с повторными попытками"""
    for attempt in range(max_retries):
        try:
            ytdl_options = get_playlist_ytdl_options()
            ytdl_options['playlistend'] = max_tracks
            
            ytdl = YoutubeDL(ytdl_options)
            info = await asyncio.to_thread(ytdl.extract_info, query, download=False)

            if not info:
                raise DownloadError("🔍 Плейлист не найден или пуст")

            tracks = []
            if 'entries' in info:
                successful_tracks = 0
                for entry in info['entries']:
                    if entry and entry.get('url') and successful_tracks < max_tracks:
                        try:
                            track_info = await yt_query(entry['url'], max_retries=2)
                            if track_info:
                                tracks.append(track_info)
                                successful_tracks += 1
                        except Exception as e:
                            logger.warning(f"[PLAYLIST] Пропуск трека {entry.get('title', 'Unknown')}: {str(e)}")
                            continue

            if not tracks:
                raise DownloadError("❌ Не удалось загрузить ни одного трека из плейлиста")

            return tracks

        except Exception as e:
            logger.warning(f"[PLAYLIST] Попытка {attempt + 1}/{max_retries} не удалась: {str(e)}")
            if attempt == max_retries - 1:
                logger.error(f"[PLAYLIST] Все попытки не удались: {str(e)}")
                raise DownloadError(f"⚠️ Ошибка загрузки плейлиста после {max_retries} попыток: {str(e)}")
            await asyncio.sleep(2)

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
                'loop_mode': 'none',
                'current_track': None,
                'text_channel': None
            }
        return music_players[guild_id]

async def play_next(guild_id: int = None):
    """Воспроизведение следующего трека"""
    try:
        if guild_id is None:
            return

        guild = bot.get_guild(guild_id)
        if not guild:
            return
            
        player = await get_music_player(guild_id)
        voice = guild.voice_client

        # Проверяем, что голосовое соединение активно
        if not voice or not voice.is_connected():
            if guild_id in music_players:
                music_players.pop(guild_id, None)
            return

        async with player['lock']:
            # ИСПРАВЛЕННАЯ логика выбора следующего трека для режимов повтора
            if player['loop_mode'] == 'one' and player['current_track']:
                # Повтор текущего трека - используем тот же трек
                current = player['current_track']
            elif player['loop_mode'] == 'queue' and player['queue']:
                # Повтор плейлиста - перемещаем текущий трек в конец очереди
                if player['current_track']:
                    player['queue'].append(player['current_track'])
                current = player['queue'].pop(0) if player['queue'] else None
            else:
                # Обычный режим - берем следующий трек из очереди
                current = player['queue'].pop(0) if player['queue'] else None
            
            player['current_track'] = current

            if not current:
                # Если очередь пуста, отключаемся
                if voice and voice.is_connected():
                    await voice.disconnect()
                music_players.pop(guild_id, None)
                return

        # Проверяем соединение перед воспроизведением
        if not voice.is_connected():
            return

        # ИСПРАВЛЕНИЕ: Создаем after_playback внутри функции play_next чтобы иметь доступ к bot.loop
        def after_playback(error):
            if error:
                logger.error(f"[FFMPEG] Ошибка воспроизведения: {error}")
            # Используем run_coroutine_threadsafe вместо create_task
            asyncio.run_coroutine_threadsafe(play_next(guild_id=guild_id), bot.loop)

        # Воспроизведение с обработкой ошибок
        try:
            voice.play(
                FFmpegPCMAudio(
                    source=current['source'],
                    executable=FFMPEG_PATH,
                    **FFMPEG_OPTIONS
                ),
                after=after_playback
            )
            
            # Отправка сообщения о текущем треке в текстовый канал
            embed, view = now_playing_embed(
                title=current['title'],
                url=current['url'],
                duration=current['duration'],
                author=current.get('author', 'Неизвестен'),
                thumbnail=current.get('thumbnail', ''),
                guild_id=guild_id,
                added_by=current.get('added_by_name', 'Неизвестный пользователь'),  # Используем имя вместо ID
                loop_mode=player['loop_mode'],
                queue_length=len(player['queue'])
            )
            
            # Находим текстовый канал для отправки сообщения
            text_channel = None
            if player.get('text_channel'):
                text_channel = guild.get_channel(player['text_channel'])
            if not text_channel:
                text_channel = guild.system_channel or guild.text_channels[0]
            
            # Отправляем новое сообщение для каждого трека
            await text_channel.send(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"[PLAYER] Ошибка воспроизведения: {str(e)}")
            # Пропускаем проблемный трек и пытаемся воспроизвести следующий
            await asyncio.sleep(1)
            await play_next(guild_id=guild_id)

    except Exception as e:
        logger.error(f"[PLAYER] Критическая ошибка: {str(e)}")
        # В случае критической ошибки очищаем плеер
        if guild_id and guild_id in music_players:
            music_players.pop(guild_id, None)

async def play_music(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    try:
        logger.info(f"[PLAY] Запрос от {interaction.user}: {query}")
        
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

        # Сохраняем текстовый канал для отправки уведомлений
        player = await get_music_player(interaction.guild.id)
        player['text_channel'] = interaction.channel.id

        # Определяем тип запроса (плейлист или одиночный трек)
        is_playlist = any(keyword in query.lower() for keyword in ['playlist', 'list='])
        
        try:
            if is_playlist:
                loading_msg = await interaction.followup.send("🔄 Загружаю плейлист... Это может занять некоторое время", ephemeral=True)
                
                tracks = await yt_playlist_query(query)
                
                player = await get_music_player(interaction.guild.id)
                added_count = 0
                async with player['lock']:
                    for track in tracks:
                        track['added_by'] = interaction.user.id
                        track['added_by_name'] = interaction.user.display_name  # Сохраняем имя пользователя
                        player['queue'].append(track)
                        added_count += 1

                await loading_msg.edit(content=f"✅ Добавлено {added_count} треков из плейлиста")
                
            else:
                # Одиночный трек с улучшенной обработкой ошибок
                try:
                    track = await yt_query(query)
                    track['added_by'] = interaction.user.id
                    track['added_by_name'] = interaction.user.display_name  # Сохраняем имя пользователя

                    player = await get_music_player(interaction.guild.id)
                    async with player['lock']:
                        player['queue'].append(track)

                    await interaction.followup.send(
                        f"🎵 Добавлено в очередь: **{track['title']}**", 
                        ephemeral=True
                    )
                except DownloadError as e:
                    return await interaction.followup.send(embed=error_embed(f"❌ {str(e)}"))

        except DownloadError as e:
            return await interaction.followup.send(embed=error_embed(f"❌ {str(e)}"))

        # Если ничего не играет, начинаем воспроизведение
        if not voice_client.is_playing():
            await play_next(guild_id=interaction.guild.id)

    except Exception as e:
        logger.error(f"[PLAY] Критическая ошибка: {str(e)}\n{traceback.format_exc()}")
        await interaction.followup.send(embed=error_embed("⚠️ Критическая ошибка воспроизведения"))

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

        # Сохраняем текстовый канал
        player = await get_music_player(interaction.guild.id)
        player['text_channel'] = interaction.channel.id

        loading_msg = await interaction.followup.send("🔄 Загружаю плейлист... Это может занять некоторое время")

        try:
            tracks = await yt_playlist_query(playlist_url)
            
            player = await get_music_player(interaction.guild.id)
            added_count = 0
            async with player['lock']:
                for track in tracks:
                    track['added_by'] = interaction.user.id
                    track['added_by_name'] = interaction.user.display_name  # Сохраняем имя пользователя
                    player['queue'].append(track)
                    added_count += 1

            embed = discord.Embed(
                title="✅ Плейлист добавлен",
                description=f"Добавлено {added_count} треков в очередь",
                color=discord.Color.green()
            )
            await loading_msg.edit(content=None, embed=embed)

        except DownloadError as e:
            await loading_msg.edit(content=f"❌ {str(e)}")

        if not voice_client.is_playing():
            await play_next(guild_id=interaction.guild.id)

    except Exception as e:
        logger.error(f"[PLAYLIST] Ошибка: {str(e)}")
        await interaction.followup.send(embed=error_embed("⚠️ Ошибка загрузки плейлиста"))

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
        if interaction.guild.id in music_players:
            async with music_players[interaction.guild.id]['lock']:
                music_players[interaction.guild.id]['queue'].clear()
                music_players[interaction.guild.id]['loop_mode'] = 'none'
                music_players[interaction.guild.id]['current_track'] = None
        
        await voice_client.disconnect()
        await interaction.response.send_message("⏹️ Воспроизведение остановлено")
    else:
        await interaction.response.send_message("⚠️ Бот не подключен к голосовому каналу", ephemeral=True)
        
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

async def queue_music(interaction: discord.Interaction):
    """Показать очередь треков"""
    if interaction.guild.id in music_players:
        queue = music_players[interaction.guild.id]['queue']
        loop_mode = music_players[interaction.guild.id]['loop_mode']
        current_track = music_players[interaction.guild.id]['current_track']
        embed = queue_embed(queue, loop_mode, current_track)
        view = QueueView(interaction.guild.id)
        await interaction.response.send_message(embed=embed, view=view)
    else:
        await interaction.response.send_message(embed=empty_queue_embed())

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
    try:
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
    except Exception as e:
        logger.error(f"[VOICE CHECK] Ошибка: {str(e)}")
        await interaction.response.send_message(
            "⚠️ Ошибка проверки голосового канала", 
            ephemeral=True
        )
        return False

async def cleanup_inactive_players():
    """Очистка неактивных музыкальных плееров"""
    try:
        guilds_to_remove = []
        
        for guild_id, player_data in music_players.items():
            guild = bot.get_guild(guild_id)
            if not guild:
                guilds_to_remove.append(guild_id)
                continue
                
            voice_client = guild.voice_client
            
            # Проверяем условия для удаления плеера
            should_remove = (
                (not voice_client or not voice_client.is_connected()) and 
                not player_data['queue']
            )
            
            if should_remove:
                guilds_to_remove.append(guild_id)
        
        # Удаляем неактивные плееры
        for guild_id in guilds_to_remove:
            if guild_id in music_players:
                music_players.pop(guild_id, None)
                logger.info(f"[CLEANUP] Удален неактивный плеер для гильдии {guild_id}")
                
    except Exception as e:
        logger.error(f"[CLEANUP] Ошибка очистки: {str(e)}")
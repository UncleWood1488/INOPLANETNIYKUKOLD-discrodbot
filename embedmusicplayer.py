import discord
from emoji import *
import logging

logger = logging.getLogger(__name__)

# Добавьте в начало файла проверку на случай отсутствия emoji
try:
    from emoji import *
except ImportError:
    # Значения по умолчанию если модуль emoji недоступен
    SPEAKER_EMOJI = "🔊"
    CLOCK_EMOJI = "⏰"
    LOGO_EMOJI = "👤"

def format_duration(seconds):
    """Преобразует секунды в формат ММ:СС или ЧЧ:ММ:СС"""
    if not seconds or seconds < 0:
        return "N/A"
    
    try:
        seconds = int(seconds)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    except (ValueError, TypeError):
        return "N/A"

class MusicControls(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.cooldowns = {}
        self.logger = logging.getLogger(__name__)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Проверка перед выполнением взаимодействия"""
        try:
            # Проверка кулдауна (3 секунды)
            user_id = interaction.user.id
            current_time = discord.utils.utcnow().timestamp()
            
            if user_id in self.cooldowns:
                if current_time - self.cooldowns[user_id] < 3:
                    await interaction.response.send_message(
                        "⏳ Подождите перед следующим действием!", 
                        ephemeral=True
                    )
                    return False
            
            self.cooldowns[user_id] = current_time

            # Проверка что пользователь в голосовом канале
            if not interaction.user.voice:
                await interaction.response.send_message(
                    "🔇 Вы должны быть в голосовом канале!", 
                    ephemeral=True
                )
                return False

            # Проверка что бот в том же канале
            voice_client = interaction.guild.voice_client
            if not voice_client or not voice_client.is_connected():
                await interaction.response.send_message(
                    "🔇 Бот не подключен к голосовом каналу!", 
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
            self.logger.error(f"[MUSIC CONTROLS] Ошибка проверки: {str(e)}")
            await interaction.response.send_message(
                "⚠️ Ошибка проверки прав доступа", 
                ephemeral=True
            )
            return False

    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.secondary, row=0)
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_playing():
            voice_client.pause()
            await interaction.response.send_message(
                "⏸️ Воспроизведение приостановлено", 
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "⚠️ Нет активного воспроизведения", 
                ephemeral=True
            )

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary, row=0)
    async def resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_paused():
            voice_client.resume()
            await interaction.response.send_message(
                "▶️ Воспроизведение возобновлено", 
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "⚠️ Воспроизведение не приостановлено", 
                ephemeral=True
            )

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, row=0)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client
        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            voice_client.stop()
            await interaction.response.send_message(
                "⏭️ Трек пропущен", 
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "⚠️ Нет активного воспроизведения", 
                ephemeral=True
            )

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, row=0)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_connected():
            # Очищаем очередь и сбрасываем режимы повтора
            from musicplayer import music_players
            if interaction.guild.id in music_players:
                async with music_players[interaction.guild.id]['lock']:
                    music_players[interaction.guild.id]['queue'].clear()
                    music_players[interaction.guild.id]['loop_mode'] = 'none'
                    music_players[interaction.guild.id]['current_track'] = None
            
            await voice_client.disconnect()
            await interaction.response.send_message(
                "⏹️ Воспроизведение остановлено", 
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "⚠️ Бот не подключен к голосовому каналу", 
                ephemeral=True
            )

    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.secondary, row=0)
    async def shuffle(self, interaction: discord.Interaction, button: discord.ui.Button):
        from musicplayer import music_players
        import random
        
        guild_id = interaction.guild.id
        if guild_id in music_players:
            async with music_players[guild_id]['lock']:
                queue = music_players[guild_id]['queue']
                if len(queue) > 1:
                    random.shuffle(queue)
                    await interaction.response.send_message("🔀 Очередь перемешана", ephemeral=True)
                else:
                    await interaction.response.send_message("⚠️ В очереди недостаточно треков", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Очередь пуста", ephemeral=True)

    @discord.ui.button(emoji="🔁", style=discord.ButtonStyle.secondary, row=1)
    async def loop_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        from musicplayer import music_players
        
        guild_id = interaction.guild.id
        if guild_id in music_players:
            async with music_players[guild_id]['lock']:
                if music_players[guild_id]['loop_mode'] == 'queue':
                    music_players[guild_id]['loop_mode'] = 'none'
                    await interaction.response.send_message("🔁 Повтор плейлиста выключен", ephemeral=True)
                else:
                    music_players[guild_id]['loop_mode'] = 'queue'
                    await interaction.response.send_message("🔁 Повтор плейлиста включен", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Нет активного плеера", ephemeral=True)

    @discord.ui.button(emoji="🔂", style=discord.ButtonStyle.secondary, row=1)
    async def loop_one(self, interaction: discord.Interaction, button: discord.ui.Button):
        from musicplayer import music_players
        
        guild_id = interaction.guild.id
        if guild_id in music_players:
            async with music_players[guild_id]['lock']:
                if music_players[guild_id]['loop_mode'] == 'one':
                    music_players[guild_id]['loop_mode'] = 'none'
                    await interaction.response.send_message("🔂 Повтор трека выключен", ephemeral=True)
                else:
                    music_players[guild_id]['loop_mode'] = 'one'
                    await interaction.response.send_message("🔂 Повтор трека включен", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Нет активного плеера", ephemeral=True)

    @discord.ui.button(emoji="📋", style=discord.ButtonStyle.primary, row=1)
    async def show_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        from musicplayer import music_players
        
        guild_id = interaction.guild.id
        if guild_id in music_players:
            queue = music_players[guild_id]['queue']
            loop_mode = music_players[guild_id]['loop_mode']
            current_track = music_players[guild_id]['current_track']
            embed = queue_embed(queue, loop_mode, current_track)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Очередь пуста", ephemeral=True)

class QueueView(discord.ui.View):
    """View только для просмотра очереди с кнопкой обновления"""
    def __init__(self, guild_id):
        super().__init__(timeout=60)
        self.guild_id = guild_id

    @discord.ui.button(emoji="🔄", style=discord.ButtonStyle.primary)
    async def refresh_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Обновить вид очереди"""
        from musicplayer import music_players
        
        guild_id = interaction.guild.id
        if guild_id in music_players:
            queue = music_players[guild_id]['queue']
            loop_mode = music_players[guild_id]['loop_mode']
            current_track = music_players[guild_id]['current_track']
            embed = queue_embed(queue, loop_mode, current_track)
            
            # Обновляем сообщение
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("⚠️ Очередь пуста", ephemeral=True)

def now_playing_embed(title, url, duration, author, thumbnail, guild_id, added_by, loop_mode='none', queue_length=0):
    """Создание embed для текущего трека"""
    embed = discord.Embed(
        title=f'{SPEAKER_EMOJI} Сейчас играет',
        description=f"[{title}]({url})",
        color=discord.Color.green()
    )
    
    # Основная информация
    embed.add_field(
        name=f'{CLOCK_EMOJI} Длительность', 
        value=f'`{format_duration(duration)}`', 
        inline=True
    )
    embed.add_field(
        name=f'{LOGO_EMOJI} Автор', 
        value=f'`{author if author else "Неизвестен"}`', 
        inline=True
    )
    embed.add_field(
        name='📋 В очереди',
        value=f'`{queue_length} треков`',
        inline=True
    )
    
    # Информация о режиме повтора
    loop_status = {
        'none': '❌ Выключен',
        'queue': '🔁 Плейлист',
        'one': '🔂 Трек'
    }
    embed.add_field(
        name='🔄 Режим повтора',
        value=f'`{loop_status[loop_mode]}`',
        inline=True
    )
    
    # Кто добавил трек
    embed.add_field(
        name='👤 Добавил',
        value=f'<@{added_by}>',
        inline=True
    )
    
    if thumbnail and thumbnail.startswith(('http://', 'https://')):
        embed.set_thumbnail(url=thumbnail)
    
    embed.set_footer(text="Кнопки управления автоматически отключаются через 3 минуты")
    
    view = MusicControls(guild_id)
    return embed, view

def queue_embed(queue, loop_mode='none', current_track=None):
    """Создание embed для очереди"""
    embed = discord.Embed(
        title=f"📋 Очередь треков [{len(queue)}]",
        color=discord.Color.blue()
    )
    
    # Добавляем информацию о режиме повтора
    loop_status = {
        'none': 'Выключен',
        'queue': '🔁 Плейлист',
        'one': '🔂 Трек'
    }
    embed.add_field(
        name='🔄 Режим повтора',
        value=f'```{loop_status[loop_mode]}```',
        inline=False
    )
    
    # Добавляем текущий трек в начало очереди
    if current_track:
        embed.add_field(
            name="🎵 Сейчас играет",
            value=(
                f"**[{current_track['title']}]({current_track['url']})**\n"
                f"{CLOCK_EMOJI} `{format_duration(current_track['duration'])}` "
                f"Добавил: <@{current_track.get('added_by', 'N/A')}>"
            ),
            inline=False
        )
    
    if queue:
        entries = []
        for i, item in enumerate(queue[:10]):
            entry = (
                f"**{i+1}.** [{item['title'][:50]}{'...' if len(item['title']) > 50 else ''}]({item['url']})\n"
                f"   {CLOCK_EMOJI} `{format_duration(item['duration'])}` "
                f"👤 <@{item.get('added_by', 'N/A')}>\n"
            )
            entries.append(entry)
        
        # Статистика очереди
        total_duration = sum(item['duration'] for item in queue)
        embed.add_field(
            name="📊 Статистика очереди",
            value=(
                f"• Всего треков: {len(queue)}\n"
                f"• Общая длительность: `{format_duration(total_duration)}`"
            ),
            inline=False
        )
        
        embed.description = "\n".join(entries)
        
        if len(queue) > 10:
            embed.set_footer(text=f"Показаны первые 10 из {len(queue)} треков")
    else:
        embed.description = "🎵 Очередь пуста! Добавьте треки командой /play"
        embed.set_thumbnail(url="https://i.imgur.com/zpYzk4A.jpeg")

    return embed

def empty_queue_embed():
    """Embed для пустой очереди"""
    embed = discord.Embed(
        title="📋 Очередь треков",
        description="🎵 Очередь пуста! Добавьте треки командой `/play`",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="💡 Как добавить музыку?",
        value=(
            "• Используйте `/play [название или URL]`\n"
            "• Или `/playlist [URL плейлиста]`\n"
            "• Поддерживаются YouTube, SoundCloud, Spotify"
        ),
        inline=False
    )
    embed.set_thumbnail(url="https://i.imgur.com/zpYzk4A.jpeg")
    return embed

def error_embed(message):
    return discord.Embed(
        title="❌ Ошибка",
        description=message,
        color=discord.Color.red()
    )

def success_embed(title, message):
    """Embed для успешных операций"""
    return discord.Embed(
        title=f"✅ {title}",
        description=message,
        color=discord.Color.green()
    )

def warning_embed(title, message):
    """Embed для предупреждений"""
    return discord.Embed(
        title=f"⚠️ {title}",
        description=message,
        color=discord.Color.orange()
    )

def info_embed(title, message):
    """Embed для информационных сообщений"""
    return discord.Embed(
        title=f"ℹ️ {title}",
        description=message,
        color=discord.Color.blue()
    )

def volume_embed(level):
    return discord.Embed(
        title=f"🔊 Громкость установлена на {level}%",
        color=discord.Color.green()
    )
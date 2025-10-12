import discord
from emoji import *

def format_duration(seconds):
    """Преобразует секунды в формат ММ:СС"""
    if not seconds or seconds < 0:
        return "N/A"
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"

class MusicControls(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.cooldowns = {}

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
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

    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.secondary, row=0)
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_playing():
            voice_client.pause()
            await interaction.response.send_message("⏸️ Воспроизведение приостановлено", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Нет активного воспроизведения", ephemeral=True)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary, row=0)
    async def resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_paused():
            voice_client.resume()
            await interaction.response.send_message("▶️ Воспроизведение возобновлено", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Воспроизведение не приостановлено", ephemeral=True)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary, row=0)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client
        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            voice_client.stop()
            await interaction.response.send_message("⏭️ Трек пропущен", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Нет активного воспроизведения", ephemeral=True)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, row=0)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_connected():
            # Очищаем очередь и сбрасываем режимы повтора
            from functions import music_players
            if interaction.guild.id in music_players:
                async with music_players[interaction.guild.id]['lock']:
                    music_players[interaction.guild.id]['queue'].clear()
                    music_players[interaction.guild.id]['loop_mode'] = 'none'
                    music_players[interaction.guild.id]['current_track'] = None
            
            await voice_client.disconnect()
            await interaction.response.send_message("⏹️ Воспроизведение остановлено", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Бот не подключен к голосовому каналу", ephemeral=True)

    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.secondary, row=0)
    async def shuffle(self, interaction: discord.Interaction, button: discord.ui.Button):
        from functions import music_players
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
        from functions import music_players
        
        guild_id = interaction.guild.id
        if guild_id in music_players:
            async with music_players[guild_id]['lock']:
                if music_players[guild_id]['loop_mode'] == 'queue':
                    music_players[guild_id]['loop_mode'] = 'none'
                    await interaction.response.send_message("🔁 Повтор плейлиста выключен", ephemeral=True)
                else:
                    music_players[guild_id]['loop_mode'] = 'queue'
                    music_players[guild_id]['loop_one'] = False
                    await interaction.response.send_message("🔁 Повтор плейлиста включен", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Нет активного плеера", ephemeral=True)

    @discord.ui.button(emoji="🔂", style=discord.ButtonStyle.secondary, row=1)
    async def loop_one(self, interaction: discord.Interaction, button: discord.ui.Button):
        from functions import music_players
        
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
        from functions import music_players
        
        guild_id = interaction.guild.id
        if guild_id in music_players:
            queue = music_players[guild_id]['queue']
            loop_mode = music_players[guild_id]['loop_mode']
            embed = queue_embed(queue, loop_mode)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Очередь пуста", ephemeral=True)

def now_playing_embed(title, url, duration, author, thumbnail, guild_id, loop_mode='none'):
    embed = discord.Embed(
        title=f'{SPEAKER_EMOJI} Сейчас играет',
        description=f"[{title}]({url})",
        color=discord.Color.green()
    )
    embed.add_field(
        name=f'{CLOCK_EMOJI} Длительность', 
        value=f'```{format_duration(duration)}```', 
        inline=True
    )
    embed.add_field(
        name=f'{LOGO_EMOJI} Автор', 
        value=f'```{author if author else "Неизвестен"}```', 
        inline=True
    )
    
    # Добавляем информацию о режиме повтора
    loop_status = {
        'none': 'Выключен',
        'queue': '🔁 Плейлист',
        'one': '🔂 Трек'
    }
    embed.add_field(
        name=f'🔄 Режим повтора',
        value=f'```{loop_status[loop_mode]}```',
        inline=True
    )
    
    if thumbnail and thumbnail.startswith(('http://', 'https://')):
        embed.set_thumbnail(url=thumbnail)
    
    view = MusicControls(guild_id)
    return embed, view

def queue_embed(queue, loop_mode='none'):
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
    
    if queue:
        entries = []
        for i, item in enumerate(queue[:10]):
            entry = (
                f"**{i+1}.** [{item['title']}]({item['url']})\n"
                f"{CLOCK_EMOJI} `{format_duration(item['duration'])}` "
                f"Добавил: <@{item.get('added_by', 'N/A')}>\n"
            )
            entries.append(entry)
        
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
        embed.description = "Очередь пуста!"
        embed.set_thumbnail(url="https://i.imgur.com/zpYzk4A.jpeg")

    return embed

def error_embed(message):
    return discord.Embed(
        title="❌ Ошибка",
        description=message,
        color=discord.Color.red()
    )

def volume_embed(level):
    return discord.Embed(
        title=f"🔊 Громкость установлена на {level}%",
        color=discord.Color.green()
    )
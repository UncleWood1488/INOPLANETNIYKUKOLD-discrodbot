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

def now_playing_embed(title, url, duration, author, thumbnail):
    embed = discord.Embed(
        title=f'{SPEAKER_EMOJI} Сейчас играет',
        description=f"[{title}]({url})",
        color=discord.Color.green()
    )
    embed.add_field(name=f'{CLOCK_EMOJI} Длительность', value=f'```{format_duration(duration)}```', inline=True)
    embed.add_field(name=f'{LOGO_EMOJI} Автор', value=f'```{author}```' or "```Неизвестен```", inline=True)
    embed.set_thumbnail(url=thumbnail)
    return embed.set_footer(text="Используйте /help для списка команд")

def queue_embed(queue):
    embed = discord.Embed(
        title=f"Очередь треков [{len(queue)}]",
        color=discord.Color.green()
    )
    
    if queue:
        # Форматируем строки с дополнительной информацией
        entries = []
        for i, item in enumerate(queue[:10]):  # Ограничиваем показ первыми 10 треками
            entry = (
                f"**{i+1}.** [{item['title']}]({item['url']})\n"
                f"{CLOCK_EMOJI} `{format_duration(item['duration'])}` "
                f"Добавлено пользователем: <@{item.get('added_by', 0)}>\n"
            )
            entries.append(entry)
        
        # Добавляем информацию о общей длительности
        total_duration = sum(item['duration'] for item in queue)
        embed.add_field(
            name="📊 Статистика очереди",
            value=f"• Всего треков: {len(queue)}\n"
                  f"• Общая длительность: `{format_duration(total_duration)}`",
            inline=False
        )
        
        embed.description = "\n".join(entries)
        
        # Добавляем предупреждение если треков больше 10
        if len(queue) > 10:
            embed.set_footer(text=f"Показаны первые 10 из {len(queue)} треков")
    else:
        embed.description = "Очередь пуста!"
        embed.set_thumbnail(url="https://i.imgur.com/zpYzk4A.jpeg")

    return embed.set_footer(text="Используйте /help для списка команд")

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
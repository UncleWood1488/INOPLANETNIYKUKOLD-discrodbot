import discord

def now_playing_embed(title, url):
    return discord.Embed(
        title="<1335406594200047708> Сейчас играет",
        description=f"[{title}]({url})",
        color=discord.Color.blurple()
    ).set_footer(text="Используйте /help для списка команд")

def queue_embed(queue):
    embed = discord.Embed(
        title="📃 Очередь треков",
        color=discord.Color.gold()
    )
    if queue:
        embed.description = "\n".join([f"{i+1}. {item}" for i, item in enumerate(queue)])
    else:
        embed.description = "Очередь пуста!"
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
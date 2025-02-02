import discord
import traceback
import logging
import functions
from discord.ext import commands
from discord import app_commands
from discord.ext.commands import Greedy
from config import BOT_TOKEN, BOT_PREFIX
from functions import log, get_online_members, replace_mention, on_voice_state_update, handle_play_error
from emoji import *
from random import choice
# from music_cog import setup


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)
bot.remove_command('help')

# async def main():
#     await setup(bot)

# when connected bl0ck
@bot.event
async def on_ready():    
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, 
        name="на тебя!"
    ))

    logging.info('{0:#^60}'.format(''))
    logging.info('{0:*^60}'.format(f'Logged in as: {bot.user.name}'))
    logging.info('{0:*^60}'.format(f'Bot ID: {bot.user.id}'))
    logging.info('{0:#^60}'.format('USER STATS:'))
    logging.info('{0:*^60}'.format(f'All users: {len(bot.users)}'))
    logging.info('{0:*^60}'.format(f'Online: {len(get_online_members(bot))}'))
    
    logging.info('{0:#^60}'.format('SYNCING SLASH COMMANDS:'))
    for guild in bot.guilds:
        bot.tree.clear_commands(guild=guild)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        logging.info('{0:*^60}'.format(f"{guild}: {[i.name for i in synced]}"))
    logging.info('{0:*^60}'.format('Done!'))

@bot.event
async def on_guild_join(guild):
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)

    

# on_message bl0ck
@bot.event
async def on_message(message):
    log(f'{message.guild} - #{message.channel} - @{message.author}: "{replace_mention(message)}"', type='message')
    await bot.process_commands(message)

@bot.event
async def on_error(event, *args, **kwargs):
    user = bot.get_user(303817809253629952)
    if user:
        await user.send(f"```py\n{error_msg}```")
    error_msg = traceback.format_exc()
    log(f'Task error: {event},\n{error_msg}', type='error')
    await bot.get_user(303817809253629952).send(f"```py\n{error_msg}```")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    try:
        await ctx.send(f"❌ Ошибка: {str(error)}", ephemeral=True)
    except discord.errors.NotFound:
        pass

@bot.event
async def on_voice_state_update(member, before, after):
    # Автоотключение при пустом канале
    voice_client = member.guild.voice_client
    if voice_client and len(voice_client.channel.members) == 1:
        await voice_client.disconnect()
        guild_id = member.guild.id
        if guild_id in functions.music_players:  # Исправленная строка
            del functions.music_players[guild_id]
            await voice_client.channel.send("🔌 Бот отключен из-за отсутствия участников")

@bot.hybrid_command(name='check', guild_ids=[537267521565229056])
async def check(ctx):
    """Показать онлайн пользователей"""
    log(f'Check by {ctx.author}', type='debug')
    await ctx.reply(f'```bash\n{get_online_members(bot)}```', ephemeral=True)

# randomizing winner of roulette
@bot.hybrid_command(name='roulette')
@app_commands.describe(members='Участники')
async def _roulette(ctx, members: Greedy[discord.Member]):
    if not members:
        await ctx.reply("Список участников пуст", ephemeral=True)
        return
    winner = choice(members)
    await ctx.reply(f'{winner.mention} победил!')

# work
@bot.hybrid_command(name='work')
async def _work(ctx):
    '''Заработок скуфкоинов'''
    log(f'{ctx.author} /work', type='debug')
    await functions.work(ctx)

# BlackJack
@bot.hybrid_command(name="bj")
@app_commands.describe(bet='Ставка скуфкоины!')
async def _bj(ctx, bet: int):
    '''Блекджек'''
    log(f'{ctx.author} /blackjack: {bet}', type='debug')
    await functions.bj(ctx, bet)

@_bj.error
async def _bj_error(ctx, error):
    log(f'Blackjack {ctx.author}: "{ctx.message.content}" - "{error}"', type='error')
    if isinstance(error, discord.ext.commands.errors.BadArgument):
        return await ctx.reply(f'{ctx.author.mention}, введите ставку nedocoins')
    elif isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
        return await ctx.reply(f'{ctx.author.mention}, введите ставку nedocoins')



# move people to voice channel
@bot.hybrid_command(name='move')
@app_commands.describe(members="Кого переместить")
async def _move(ctx, members: Greedy[discord.Member]):
    '''Переместить участников в свободный голосовой канал
    Нужны права доступа на перемещение участников
    '''
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

@bot.hybrid_command(name="play")
@app_commands.describe(query="Ссылка или название трека")
async def play_command(ctx, query: str):
    await functions.play_music(ctx, query)

@bot.hybrid_command(name="skip")
async def skip_command(ctx):
    await functions.skip_music(ctx)

@bot.hybrid_command(name="pause")
async def pause_command(ctx):
    await functions.pause_music(ctx)

@bot.hybrid_command(name="resume")
async def resume_command(ctx):
    await functions.resume_music(ctx)

@bot.hybrid_command(name="stop")
async def stop_command(ctx):
    await functions.stop_music(ctx)

@bot.hybrid_command(name="queue")
async def queue_command(ctx):
    await functions.show_queue(ctx)

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

# enjoying in game war
#@bot.gybrid_command(name='enjoygw')
#@app_commands.describe(members="Вы теперь призывник, выберите свою сторону.")
#async def _enjoygw(ctx):
#    log(f'enjoygw {ctx.set}'')
#        if #жмет на одну кнопку
#        else message.
#    await functions.enjoy(members)
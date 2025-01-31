import discord
import traceback
import logging
import functions
from discord.ext import commands
from discord import app_commands
from discord.ext.commands import Greedy
from config import BOT_TOKEN, BOT_PREFIX
from functions import log
from emoji import *
from enum import member
from random import choice
from typing import Self

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

# variables bl0ck
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)
bot.remove_command('help')

# when connected bl0ck
@bot.event
async def on_ready():    
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="на тебя!"))

    print('{0:#^60}'.format(''))
    print('{0:*^60}'.format(f'Logged in as: {bot.user.name}'))
    print('{0:*^60}'.format(bot.user.id))

    print('{0:#^60}'.format('USER STATS:'))
    print('{0:*^60}'.format('all users: {0}'.format(len(bot.users))))
    print('{0:*^60}'.format('online: {0}'.format(len(functions.get_online_members(bot)))))
    print('{0:#^60}'.format('online moderators:'))

    print('{0:#^60}'.format('SYNCING SLASH COMMANDS:'))
    # await bot.tree.sync() # sync local, use to clean
    for guild in bot.guilds:
        bot.tree.clear_commands(guild=guild)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print('{0:*^60}'.format(f"{guild}: {[i.name for i in synced]}")) # print name of commands on every guild
    print('{0:*^60}'.format('Done!'))
    print('{0:#^60}'.format(''))

@bot.event
async def on_guild_join(guild):
    bot.tree.copy_global_to(guild)
    await bot.tree.sync(guild)
    

# on_message bl0ck
@bot.event
async def on_message(message):
    log(f'{message.guild} - #{message.channel} - @{message.author}: "{functions.replace_mention(message)}"', type='message')
    return await bot.process_commands(message)

@bot.event
async def on_error(event, *args, **kwargs):
    msg = traceback.format_exc()
    log(f'task error: {event},\n{msg}', type='error')
    await bot.get_user(303817809253629952).send(f"```py\n{msg}```")

@bot.event
async def on_command_error(ctx, err):
    await ctx.reply(f"```bash\nError: {err}```")
    msg = "".join(traceback.format_exception(err))
    log(f'command error: {ctx.message},\n{msg}', type='error')
    await bot.get_user(303817809253629952).send(f"```py\n{msg}```")

@bot.hybrid_command(name='check', guild_ids=[537267521565229056])
async def check(ctx):
    '''Имена всех, кто онлайн'''
    log(f'check by {ctx.author}', type='debug')
    await ctx.reply(f'```bash\n{functions.get_online_members(bot)}```', ephemeral=True)

# randomizing winner of roulette
@bot.hybrid_command(name='roulette')
@app_commands.describe(members='Участники')
async def _roulette(ctx, members: Greedy[discord.Member]):
    '''Выбирает случайного победителя'''
    log(f'roulette by {ctx.author}: {members}', type='debug')
    if not len(members):
        return await ctx.reply("Передан пустой список")

    winner = choice(members)
    await ctx.reply(f'{winner.mention} Победил!')

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
async def _addmoney(ctx):
    '''Добавить денег'''
    log(f'{ctx.author} /addmoney', type='debug')
    await functions.addmoney(ctx)

# @bot.hybrid_command(name='play')
# async def play(self, ctx, args):
#     '''Воспроизвести аудиофайл'''
#     await MusicCog.play(self, ctx, args)

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
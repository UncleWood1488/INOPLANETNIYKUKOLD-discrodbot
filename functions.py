import discord
import time
import db
import buttons

# from snake import Snake
from blackjack import blackjack
from random import *
from emoji import *
from config import pay, cooldown, multiplier, new_worker_balance, fish

bjplayers = {}
snakeplayers = {}


def get_online_members(bot):
    gen = bot.get_all_members()
    members = [next(gen) for i in range(len(bot.users))]
    online_members = [member.name for member in members if member.status != discord.Status.offline]
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
    emb.add_field(name = '🍉Список команд', value = '/check - список людей на сервере онлайн\n /roullete - рулетка с игроком\n /work - работа\n /bj - блекджек\n /move - переместить кого либо\n /balance - проверить баланс\n ❗__НЕ РАБОЧИЕ КОМАНДЫ__❗\n ~~/fishing (рыбалка)~~\n ~~/svogamehelp (помощь по игре сво)~~\n ~~/musichelp (помощь по музыке)~~ \n ~~/shop (магазин)~~')
    await ctx.reply(embed=emb, ephemeral=True)

# #МУЗЫКАЛЬНЫЙ ПЛЕЕР


#БАЛАНС
async def balance(ctx):
    emb = discord.Embed(title = '```🍉IONOTEKA BANK🍉```', colour = discord.Color.brand_green())
    emb.set_author(name = ctx.author.name, icon_url = ctx.author.avatar.url)
    if db.balance(ctx.author.id) <= 4:
        emb.add_field(name = 'Ваш баланс:', value = f'{db.balance(ctx.author.id)} скуфкоина <:skufcoin:1248834544233353227>', )
        return await ctx.reply(embed=emb, ephemeral=True)
    emb.add_field(name = 'Ваш баланс:', value = f'{db.balance(ctx.author.id)} скуфкоинов <:skufcoin:1248834544233353227>', )
    await ctx.reply(embed=emb, ephemeral=True)

#ВЫДАТЬ ДЕНЬГИ
# async def addmoney(ctx, member,):
#     print(member)
#     if not ctx.guild.get_role(406211889228546048, 406212152316395574, 406212396806569984, 430721367592140803) in ctx.author.roles and not ctx.author.guild_permissions.move_members:
#         return await ctx.reply(f'Недостаточно прав на исполнение команды.')
    
#     if not db.is_member_exists(member)['coins']:
#         return await ctx.reply(f'Данный участник ещё не работал, напишите команду /work чтобы зарегистрировать свой счёт в банке сервера')
#     db.add_money(member, coins)
#     await ctx.reply(f'{ctx.author.mention} выдал {member} {coins} <:skufcoin:1248834544233353227>')

#РАБОТА
async def work(ctx):
    member = ctx.author.id

    if not db.is_member_exists(member)['coins']:
        db.register(member)
        return await ctx.reply(f' Новый работник! Вам выдали начальный капитал: {new_worker_balance} скуфкоинов <:skufcoin:1248834544233353227>')
    
    if db.is_cooldown(member, 'work'):
        cd = db.get_cooldown(member, 'work')
        return await ctx.reply(f'{ctx.author.mention} устал и не может работать, кулдаун: {cd}')
    
    db.update_balance(member, pay['work'] * multiplier)
    db.set_cooldown(member, 'work', cooldown['work'])
    await ctx.reply(f'{ctx.author.mention} сходил на работу! +100 <:skufcoin:1248834544233353227>')

#МАГАЗИН
async def shop(ctx):
    emb = discord.Embed(title= 'Магазин', colour = discord.Color.gold(), )
    emb.set_author(name = ctx.bot.application.name, icon_url = ctx.bot.application.icon)
    emb.add_field(name = 'Ваш баланс:', value = f'{db.balance(ctx.author.id)} скуфкоинов <:skufcoin:1248834544233353227>', )
    emb.add_field(name = db.fishing(), value = '')
    await ctx.reply(embed=emb, ephemeral=True)

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
#Нужно добавить обновление бд
async def fishing(ctx):
    member = ctx.author.id
    
    if not db.balance(member):  # Если пользователь не зарегистрирован
        db.register(member)
        return await ctx.reply(f'Новый рыбачок! Вам выдали начальный капитал: 100 скуфкоинов <:skufcoin:1248834544233353227>')
    
    if db.is_cooldown(member, 'fishing'):
        return await ctx.reply(f'{ctx.author.mention} устал и не может рыбачить, кулдаун: 1 час')
    
    # Ловля рыбы
    fish_reward = randint(10, 50)
    db.update(member, fish_reward)
    db.set_cooldown(member, 'fishing')
    
    emb = discord.Embed(title='Рыбалка', color=discord.Color.blue())
    emb.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
    emb.add_field(name="Ты поймал:", value=f"🐟 Рыба (+{fish_reward} скуфкоинов)")
    await ctx.reply(embed=emb)



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
    

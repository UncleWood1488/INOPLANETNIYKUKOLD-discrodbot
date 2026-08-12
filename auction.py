import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime, timedelta
import db
from functions import log
from emoji import SKUFCOIN_EMOJI

class Auction(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_auctions = {}
        self.load_auctions()
        self.check_auctions.start()

    def load_auctions(self):
        if os.path.exists('auctions_data.json'):
            with open('auctions_data.json', 'r') as f:
                data = json.load(f)
                self.active_auctions = {int(k): v for k, v in data.items()}
                log(f"[AUCTION] Загружено {len(self.active_auctions)} аукционов")

    def save_auctions(self):
        with open('auctions_data.json', 'w') as f:
            json.dump(self.active_auctions, f, indent=4, default=str)

    @commands.hybrid_command(name='start_auction', description='Начать аукцион')
    async def start_auction(self, ctx, item: str, start_price: int, duration_minutes: int):
        """!start_auction <предмет> <старт. цена> <минуты>"""
        if ctx.channel.id in self.active_auctions:
            await ctx.reply("❌ В этом канале уже идёт аукцион!", ephemeral=True)
            return

        if start_price <= 0 or duration_minutes <= 0:
            await ctx.reply("❌ Цена и длительность должны быть положительными", ephemeral=True)
            return

        if not db.is_user_exists(ctx.author.id):
            db.register_user(ctx.author.id)

        end_time = datetime.utcnow() + timedelta(minutes=duration_minutes)
        auction_data = {
            'item': item,
            'current_price': start_price,
            'last_bidder': None,
            'last_bidder_name': None,
            'end_time': end_time.isoformat(),
            'channel_id': ctx.channel.id,
            'message_id': None,
            'started_by': ctx.author.id
        }
        self.active_auctions[ctx.channel.id] = auction_data
        self.save_auctions()

        embed = discord.Embed(
            title="🔨 **Начинается аукцион!**",
            description=f"**Лот:** {item}\n**Стартовая цена:** {start_price} {SKUFCOIN_EMOJI}\n**Длительность:** {duration_minutes} мин.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Аукцион закончится в {end_time.strftime('%H:%M:%S')} UTC")
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)

        msg = await ctx.reply(embed=embed)
        self.active_auctions[ctx.channel.id]['message_id'] = msg.id
        self.save_auctions()

        log(f"[AUCTION] {ctx.author} начал аукцион на {item} в #{ctx.channel}")

    @commands.hybrid_command(name='bid', description='Сделать ставку')
    async def bid(self, ctx, price: int):
        auction = self.active_auctions.get(ctx.channel.id)
        if not auction:
            await ctx.reply("❌ В этом канале нет активного аукциона.", ephemeral=True)
            return

        if datetime.utcnow() > datetime.fromisoformat(auction['end_time']):
            await self.end_auction(ctx.channel)
            await ctx.reply("⏰ Аукцион уже закончился.", ephemeral=True)
            return

        if price <= auction['current_price']:
            await ctx.reply(f"❌ Ставка должна быть выше текущей цены ({auction['current_price']} {SKUFCOIN_EMOJI})!", ephemeral=True)
            return

        if not db.is_user_exists(ctx.author.id):
            db.register_user(ctx.author.id)

        balance = db.get_balance(ctx.author.id)
        if balance < price:
            await ctx.reply(f"❌ Недостаточно средств! У вас {balance} {SKUFCOIN_EMOJI}", ephemeral=True)
            return

        auction['current_price'] = price
        auction['last_bidder'] = ctx.author.id
        auction['last_bidder_name'] = ctx.author.display_name
        self.save_auctions()

        try:
            msg = await ctx.channel.fetch_message(auction['message_id'])
            embed = msg.embeds[0]
            embed.description = f"**Лот:** {auction['item']}\n**Текущая цена:** {price} {SKUFCOIN_EMOJI}\n**Последний ставщик:** {ctx.author.mention}"
            await msg.edit(embed=embed)
        except Exception as e:
            log(f"[AUCTION] Ошибка обновления сообщения: {e}", type='error')

        await ctx.reply(f"✅ Ставка {price} {SKUFCOIN_EMOJI} принята от {ctx.author.mention}!")

    async def end_auction(self, channel):
        auction = self.active_auctions.pop(channel.id, None)
        if not auction:
            return

        self.save_auctions()
        winner_id = auction['last_bidder']
        price = auction['current_price']

        embed = discord.Embed(
            title="🏆 **Аукцион завершён!**",
            color=discord.Color.gold()
        )

        if winner_id:
            winner = channel.guild.get_member(winner_id)
            if winner:
                winner_mention = winner.mention
                winner_name = winner.display_name
            else:
                winner_mention = f"<@{winner_id}>"
                winner_name = auction.get('last_bidder_name', 'Неизвестный')

            current_balance = db.get_balance(winner_id)
            if current_balance >= price:
                db.update_balance(winner_id, -price)
                embed.description = f"**Лот:** {auction['item']}\n**Победитель:** {winner_mention}\n**Цена продажи:** {price} {SKUFCOIN_EMOJI}"
                log(f"[AUCTION] Снято {price} с {winner_id} за {auction['item']}")
            else:
                embed.description = f"**Лот:** {auction['item']}\n**Победитель:** {winner_mention}\n**Цена продажи:** {price} {SKUFCOIN_EMOJI}\n⚠️ **У победителя недостаточно средств! Продажа отменена.**"
        else:
            embed.description = f"**Лот:** {auction['item']}\n**Победитель:** никто\n**Аукцион закрыт без продажи.**"

        await channel.send(embed=embed)
        log(f"[AUCTION] Аукцион завершён в #{channel.name}")

    @tasks.loop(seconds=10)
    async def check_auctions(self):
        now = datetime.utcnow()
        for channel_id, auction in list(self.active_auctions.items()):
            end_time = datetime.fromisoformat(auction['end_time'])
            if now >= end_time:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await self.end_auction(channel)

    @check_auctions.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    @commands.hybrid_command(name='cancel_auction', description='Отменить аукцион')
    async def cancel_auction(self, ctx):
        auction = self.active_auctions.get(ctx.channel.id)
        if not auction:
            await ctx.reply("❌ В этом канале нет активного аукциона.", ephemeral=True)
            return

        if ctx.author.id != auction['started_by'] and not ctx.author.guild_permissions.manage_guild:
            await ctx.reply("❌ Вы не можете отменить этот аукцион.", ephemeral=True)
            return

        del self.active_auctions[ctx.channel.id]
        self.save_auctions()
        await ctx.reply("✅ Аукцион отменён.")
        log(f"[AUCTION] {ctx.author} отменил аукцион в #{ctx.channel}")

async def setup(bot):
    await bot.add_cog(Auction(bot))
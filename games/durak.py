import discord
from discord.ext import commands
import random
from typing import List, Dict, Tuple

class Card:
    def __init__(self, suit: str, rank: str):
        self.suit = suit
        self.rank = rank
        self.value = self.get_value()

    def get_value(self) -> int:
        values = {'6': 6, '7': 7, '8': 8, '9': 9, '10': 10,
                  'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        return values[self.rank]

    def __repr__(self):
        return f"{self.rank}{self.suit}"

class Deck:
    def __init__(self):
        self.suits = ['♠', '♥', '♦', '♣']
        self.ranks = ['6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.cards = [Card(suit, rank) for suit in self.suits for rank in self.ranks]
        self.trump = None
        self.shuffle()

    def shuffle(self):
        random.shuffle(self.cards)
        if self.cards:
            self.trump = self.cards[-1].suit

    def draw(self, n: int) -> List[Card]:
        return [self.cards.pop() for _ in range(n)] if len(self.cards) >= n else []

class Player:
    def __init__(self, user: discord.User):
        self.user = user
        self.hand: List[Card] = []
        self.is_attacking = False

    def add_cards(self, cards: List[Card]):
        self.hand.extend(cards)
        self.sort_hand()

    def sort_hand(self):
        self.hand.sort(key=lambda card: (card.suit != deck.trump, card.value))

class Game:
    def __init__(self, channel: discord.TextChannel, players: List[Player]):
        self.channel = channel
        self.players = players
        self.deck = Deck()
        self.table: Dict[Card, Card] = {}
        self.current_player = 0
        self.trump_suit = self.deck.trump
        self.attacker_index = 0
        self.defender_index = 1
        self.game_over = False

        # Раздать начальные карты
        for player in self.players:
            player.add_cards(self.deck.draw(6))

    async def start_turn(self):
        await self.channel.send(f"Ход игрока {self.players[self.attacker_index].user.mention}! Атакуйте!")

    async def check_win_condition(self):
        for player in self.players:
            if not player.hand and not self.deck.cards:
                await self.channel.send(f"Игрок {player.user.mention} победил!")
                self.game_over = True
                return True
        return False

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)
active_games: Dict[int, Game] = {}

@bot.command(name='start_fool')
async def start_game(ctx: commands.Context, opponent: discord.Member):
    if ctx.channel.id in active_games:
        await ctx.send("Игра уже идет в этом канале!")
        return

    players = [Player(ctx.author), Player(opponent)]
    game = Game(ctx.channel, players)
    active_games[ctx.channel.id] = game

    await ctx.send(
        f"Игра началась между {ctx.author.mention} и {opponent.mention}!\n"
        f"Козырь: {game.trump_suit}\n"
        f"Введите !play [номер_карты] для атаки или защиты"
    )
    await game.start_turn()

@bot.command(name='play')
async def play_card(ctx: commands.Context, card_index: int):
    game = active_games.get(ctx.channel.id)
    if not game:
        await ctx.send("Сначала начните игру командой !start_fool @оппонент")
        return

    player_index = next((i for i, p in enumerate(game.players) if p.user == ctx.author), None)
    if player_index is None:
        await ctx.send("Вы не участник этой игры!")
        return

    player = game.players[player_index]
    card_index -= 1  # Для удобства пользователя (нумерация с 1)

    if 0 <= card_index < len(player.hand):
        played_card = player.hand[card_index]
        # Простая логика для первого хода
        if not game.table:
            del player.hand[card_index]
            game.table[played_card] = None
            await ctx.send(f"{ctx.author.mention} атакует картой {played_card}!")
            await game.channel.send(f"{game.players[game.defender_index].user.mention}, защищайтесь!")
        else:
            await ctx.send("Логика защиты пока не реализована!")
    else:
        await ctx.send("Неверный номер карты!")

@bot.command(name='hand')
async def show_hand(ctx: commands.Context):
    game = active_games.get(ctx.channel.id)
    if not game:
        return

    player = next((p for p in game.players if p.user == ctx.author), None)
    if not player:
        return

    hand = "\n".join([f"{i+1}. {card}" for i, card in enumerate(player.hand)])
    await ctx.send(f"Ваши карты:\n{hand}")

@bot.event
async def on_ready():
    print(f'Бот {bot.user} готов к работе!')

# Запуск бота
bot.run('YOUR_BOT_TOKEN')
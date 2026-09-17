import discord
import db
import random
import math
from emoji import *

class blackjack():
    def __init__(self, author, bet: int = 0):
        self.author = author
        self.bet = bet
        self.hand = []
        self.dealer_hand = []
        self.dealer_msg_val = 0
        self.reason = ''
        self.embed = None
        self.view = None
        db.update_balance(self.author.id, -self.bet)
        
        [self._claim_card() for i in range(2)]
        [self._claim_card(dealer=True) for i in range(2)]
        
        if type(self.dealer_hand[0]) == int:
            self.dealer_msg_val = self.dealer_hand[0]
        elif self.dealer_hand[0] == 'A':
            self.dealer_msg_val = 11
        else:
            self.dealer_msg_val = 10
            
        player_sum = self._validate_sum()
        dealer_sum = self._validate_sum(dealer=True)
        
        if player_sum == 21 and dealer_sum != 21:
            self.reason = 'ftw'
            pay = math.ceil(self.bet * 2.5)
            db.update_balance(self.author.id, pay)

    def _claim_card(self, *, dealer: bool = False):
        cards = ('A', 'K', 'Q', 'J', 10, 9, 8, 7, 6, 5, 4, 3, 2)
        card = random.choice(cards)
        if dealer:
            return self.dealer_hand.append(card)
        return self.hand.append(card)

    def _validate_sum(self, *, dealer: bool = False):
        sum_val = 0
        hand = self.hand
        if dealer:
            hand = self.dealer_hand

        for card in hand:
            if type(card) == int:
                sum_val += card
            elif card in ['K', 'Q', 'J']:
                sum_val += 10
        
        aces_count = hand.count('A')
        for i in range(aces_count):
            if sum_val + 11 <= 21:
                sum_val += 11
            else:
                sum_val += 1
                
        return sum_val

    def is_playing(self):
        return self.reason == ''

    def _get_card_emoji(self, card):
        """Получить кастомное эмодзи для карты из emoji.py"""
        suits = ['clubs', 'diamonds', 'hearts', 'spades']
        suit = random.choice(suits)
        
        card_keys = {
            'A': 'ace',
            '2': '2',
            '3': '3',
            '4': '4',
            '5': '5',
            '6': '6',
            '7': '7',
            '8': '8',
            '9': '9',
            '10': '10',
            'J': 'jack',
            'Q': 'queen',
            'K': 'king'
        }
        
        card_key = card_keys.get(card, str(card))
        emoji_key = f"{card_key}_of_{suit}"
        
        return BJ_CARD_EMOJIS.get(emoji_key, f"{card}")

    def _format_hand(self, hand, hide_second=False):
        """Форматирует руку для отображения"""
        if hide_second and len(hand) >= 2:
            first_card = self._get_card_emoji(hand[0])
            return f"{first_card} ❓"
        
        cards = [self._get_card_emoji(card) for card in hand]
        return " ".join(cards)

    def prepare_message(self):
        """Создает embed с информацией об игре"""
        sum_val = self._validate_sum()
        dealer_sum = self._validate_sum(dealer=True)
        
        embed = discord.Embed(
            title="🃏 Blackjack",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="💰 Ставка",
            value=f"{self.bet} {SKUFCOIN_EMOJI}",
            inline=False
        )
        
        player_hand = self._format_hand(self.hand)
        embed.add_field(
            name=f"🎯 Ваши карты (сумма: {sum_val})",
            value=player_hand,
            inline=False
        )
        
        if self.is_playing():
            dealer_hand = self._format_hand(self.dealer_hand, hide_second=True)
            embed.add_field(
                name=f"🎯 Карты дилера (сумма: {self.dealer_msg_val})",
                value=dealer_hand,
                inline=False
            )
            embed.set_footer(text=f"{self.author.name}, сделайте ход!")
        else:
            dealer_hand = self._format_hand(self.dealer_hand)
            embed.add_field(
                name=f"🎯 Карты дилера (сумма: {dealer_sum})",
                value=dealer_hand,
                inline=False
            )
            
            if self.reason == 'ftw':
                win_amount = math.ceil(self.bet * 1.5)
                embed.color = discord.Color.gold()
                embed.description = f"🎉 **BLACKJACK!** Вы выиграли {win_amount} {SKUFCOIN_EMOJI}!"
            elif self.reason == 'win':
                embed.color = discord.Color.green()
                embed.description = f"✅ Вы выиграли {self.bet} {SKUFCOIN_EMOJI}!"
            elif self.reason == 'lose':
                embed.color = discord.Color.red()
                embed.description = f"❌ Вы проиграли {self.bet} {SKUFCOIN_EMOJI}!"
            elif self.reason == 'tie':
                embed.color = discord.Color.greyple()
                embed.description = f"🤝 Ничья! Ставка возвращена!"
        
        return embed

    def hit(self):
        if not self.is_playing():
            return self.prepare_message()
            
        self._claim_card()
        player_sum = self._validate_sum()
        
        if player_sum > 21:
            self.reason = 'lose'
        elif player_sum == 21 or len(self.hand) >= 5:
            self._dealer_play()
        elif len(self.hand) >= 5 and player_sum <= 21:
            self.reason = 'win'
            db.update_balance(self.author.id, self.bet * 2)
            
        return self.prepare_message()

    def _dealer_play(self):
        dealer_sum = self._validate_sum(dealer=True)
        player_sum = self._validate_sum()
        
        while dealer_sum < 17 and len(self.dealer_hand) < 5:
            self._claim_card(dealer=True)
            dealer_sum = self._validate_sum(dealer=True)
        
        if dealer_sum > 21:
            self.reason = 'win'
            db.update_balance(self.author.id, self.bet * 2)
        elif dealer_sum == player_sum:
            self.reason = 'tie'
            db.update_balance(self.author.id, self.bet)
        elif dealer_sum > player_sum:
            self.reason = 'lose'
        else:
            self.reason = 'win'
            db.update_balance(self.author.id, self.bet * 2)

    def stay(self):
        if not self.is_playing():
            return self.prepare_message()
            
        self._dealer_play()
        return self.prepare_message()


class BJView(discord.ui.View):
    """Кнопки для игры в блекджек"""
    def __init__(self, user_id, game, timeout=30):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.game = game
        self.message = None
        self.bjplayers = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Это не ваша игра!", 
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Взять", style=discord.ButtonStyle.success, emoji="👊")
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.game.is_playing():
            await interaction.response.edit_message(
                embed=self.game.prepare_message(),
                view=None
            )
            return
        
        embed = self.game.hit()
        
        if self.game.is_playing():
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=None)
            if self.bjplayers and interaction.user.id in self.bjplayers:
                del self.bjplayers[interaction.user.id]

    @discord.ui.button(label="Достаточно", style=discord.ButtonStyle.danger, emoji="✋")
    async def stay_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.game.is_playing():
            await interaction.response.edit_message(
                embed=self.game.prepare_message(),
                view=None
            )
            return
        
        embed = self.game.stay()
        await interaction.response.edit_message(embed=embed, view=None)
        
        if self.bjplayers and interaction.user.id in self.bjplayers:
            del self.bjplayers[interaction.user.id]

    async def on_timeout(self):
        if self.game and self.game.is_playing():
            embed = self.game.stay()
            if self.message:
                try:
                    await self.message.edit(embed=embed, view=None)
                except:
                    pass
        elif self.message:
            try:
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)
            except:
                pass
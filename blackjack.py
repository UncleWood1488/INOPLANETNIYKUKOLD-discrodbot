import db
import random
import math
import functions

class blackjack():
    def __init__(self, author, bet: int=0):
        self.author = author
        self.bet = bet
        self.hand = []
        self.dealer_hand = []
        self.dealer_msg_val = 0 # Сумма карт диллера, показывающаяся в сообщении
        self.reason = ''
        db.updatemoney(self.author.id, -self.bet)
        # claiming cards
        [self._claim_card() for i in range(2)]
        [self._claim_card(dealer=True) for i in range(2)]
        # setting up self.dealer_msg_val
        if type(self.dealer_hand[0]) == int:
            self.dealer_msg_val = self.dealer_hand[0]
        elif self.dealer_hand[0] == 'A':
            self.dealer_msg_val = 11
        else:
            self.dealer_msg_val = 10
        # check first turn win
        if self._validate_sum() == 21 != self._validate_sum(dealer=True):
            self.reason = 'ftw' # first turn win
            pay = math.ceil(self.bet * 2.5) # 1.5 bet multiplier
            return db.updatemoney(self.author.id, pay)

    def _claim_card(self, *, dealer: bool=False):
        cards = ('A', 'K', 'Q', 'J', 10, 9, 8, 7, 6, 5, 4, 3, 2)
        card = random.choice(cards)
        if dealer:
            functions.log(f'Blackjack {self.author} Dealer {card}', type='debug') # ---
            return self.dealer_hand.append(card)
        return self.hand.append(card)

    def _validate_sum(self, *, dealer: bool=False):
        sum = 0
        hand = self.hand
        if dealer:
            hand = self.dealer_hand

        for card in hand:
            if type(card) == int:
                sum += card; continue
            if card in ['K', 'Q', 'J']:
                sum += 10; continue
        for i in range(hand.count('A')): # for each A
            if sum + 11 > 21:
                sum += 1; continue
            sum += 11
        return sum

    def is_playing(self):
        if (self.reason == ''):
            return True
        return False

    def prepare_message(self):
        sum = self._validate_sum()
        mention = self.author.mention
        if self.is_playing():
            return f'```{self.author.name}, Твои карты: {self.hand}, сумма: {sum}\n\
Карты диллера: [{self.dealer_hand[0]}, ?], сумма: {self.dealer_msg_val},```\
{mention}, Взять ещё карту или достаточно?'
        elif self.reason == 'ftw': # first turn win
            return f'```{self.author.name}, Твои карты: {self.hand}, сумма: {sum}, \n\
Карты диллера: [{self.dealer_hand}]`, сумма {self.dealer_msg_val}.```\
{mention} выиграл {math.ceil(self.bet*1.5)} nedocoins!'
        elif self.reason == 'lose':
            return f'```{self.author.name}, Твои карты: {self.hand}, сумма: {sum}, \n\
Карты диллера: [{self.dealer_hand}]`, сумма {self._validate_sum(dealer=True)},```\
{mention}, Ты проиграл!`'
        elif self.reason == 'win':
            return f'```{self.author.name}, Твои карты: {self.hand}, сумма: {sum}, \n\
Карты диллера: [{self.dealer_hand}]`, сумма {self._validate_sum(dealer=True)}.```\
{mention} выиграл {self.bet} nedocoins!'
        elif self.reason == 'tie':
            return f'```{self.author.name}, Твои карты: {self.hand}, сумма: {sum}, \n\
Карты диллера: [{self.dealer_hand}]`, сумма {self._validate_sum(dealer=True)}.```\
{mention}, Это ничья!'

    def hit(self):
        self._claim_card()
        if self._validate_sum() > 21:
            self.reason = 'lose'
        elif len(self.hand) >= 5:
            self.reason = 'win'
        return self.prepare_message()

    def stay(self): # !recursive function!
        sum = self._validate_sum()
        dealer_sum = self._validate_sum(dealer=True)

        if not self.is_playing(): # protection
            return self.prepare_message()
        # overclaiming check
        elif sum > 21:
            self.reason = 'lose'
            return self.prepare_message()
        elif dealer_sum > 21:
            self.reason = 'win'
            db.updatemoney(self.author.id, self.bet*2)
            return self.prepare_message()
        # 5-card hand check
        elif len(self.hand) >= 5:
            self.reason = 'win'
            db.updatemoney(self.author.id, self.bet*2)
            return self.prepare_message()
        elif len(self.dealer_hand) >= 5:
            self.reason = 'lose'
            return self.prepare_message()

        elif sum == dealer_sum > 17: #      tie check
            self.reason = 'tie'
            db.updatemoney(self.author.id, self.bet)
            return self.prepare_message()
        elif sum < dealer_sum: #            classic lose check
            self.reason = 'lose'
            return self.prepare_message()
        else:
            self._claim_card(dealer=True) # game continues, dealer need more cards
            return self.stay() #            recursive function

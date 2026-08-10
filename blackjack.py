import db
import random
import math

class blackjack():
    def __init__(self, author, bet: int=0):
        self.author = author
        self.bet = bet
        self.hand = []
        self.dealer_hand = []
        self.dealer_msg_val = 0  # Сумма карт дилера, показывающаяся в сообщении
        self.reason = ''
        # Списание ставки при создании игры
        db.update_balance(self.author.id, -self.bet)
        
        # Раздача карт
        [self._claim_card() for i in range(2)]
        [self._claim_card(dealer=True) for i in range(2)]
        
        # Установка значения для показа дилера
        if type(self.dealer_hand[0]) == int:
            self.dealer_msg_val = self.dealer_hand[0]
        elif self.dealer_hand[0] == 'A':
            self.dealer_msg_val = 11
        else:
            self.dealer_msg_val = 10
            
        # Проверка победы на первом ходу (Blackjack)
        player_sum = self._validate_sum()
        dealer_sum = self._validate_sum(dealer=True)
        
        if player_sum == 21 and dealer_sum != 21:
            self.reason = 'ftw'  # first turn win
            pay = math.ceil(self.bet * 2.5)  # 2.5x ставка (1.5x выигрыш + возврат ставки)
            db.update_balance(self.author.id, pay)
        elif player_sum == 21 and dealer_sum == 21:
            self.reason = 'tie'  # ничья на первом ходу
            db.update_balance(self.author.id, self.bet)  # возврат ставки

    def _claim_card(self, *, dealer: bool=False):
        cards = ('A', 'K', 'Q', 'J', 10, 9, 8, 7, 6, 5, 4, 3, 2)
        card = random.choice(cards)
        if dealer:
            # Вместо functions.log можно использовать logger, но для простоты оставим print или удалим
            # functions.log(f'Blackjack {self.author} Dealer {card}', type='debug')
            return self.dealer_hand.append(card)
        return self.hand.append(card)

    def _validate_sum(self, *, dealer: bool=False):
        sum_val = 0
        hand = self.hand
        if dealer:
            hand = self.dealer_hand

        # Сначала считаем все карты кроме тузов
        for card in hand:
            if type(card) == int:
                sum_val += card
            elif card in ['K', 'Q', 'J']:
                sum_val += 10
        
        # Затем обрабатываем тузы
        aces_count = hand.count('A')
        for i in range(aces_count):
            if sum_val + 11 <= 21:
                sum_val += 11
            else:
                sum_val += 1
                
        return sum_val

    def is_playing(self):
        return self.reason == ''

    def prepare_message(self):
        sum_val = self._validate_sum()
        mention = self.author.mention
        
        if self.is_playing():
            return (
                f'```{self.author.name}, Твои карты: {self.hand}, сумма: {sum_val}\n'
                f'Карты дилера: [{self.dealer_hand[0]}, ?], сумма: {self.dealer_msg_val}```\n'
                f'{mention}, Взять ещё карту или достаточно?'
            )
        elif self.reason == 'ftw':  # first turn win
            dealer_sum = self._validate_sum(dealer=True)
            win_amount = math.ceil(self.bet * 1.5)  # Чистый выигрыш
            return (
                f'```{self.author.name}, Твои карты: {self.hand}, сумма: {sum_val}\n'
                f'Карты дилера: {self.dealer_hand}, сумма: {dealer_sum}```\n'
                f'{mention} выиграл {win_amount} скуфкоинов! 🎉'
            )
        elif self.reason == 'lose':
            dealer_sum = self._validate_sum(dealer=True)
            return (
                f'```{self.author.name}, Твои карты: {self.hand}, сумма: {sum_val}\n'
                f'Карты дилера: {self.dealer_hand}, сумма: {dealer_sum}```\n'
                f'{mention}, Ты проиграл {self.bet} скуфкоинов! 💸'
            )
        elif self.reason == 'win':
            dealer_sum = self._validate_sum(dealer=True)
            return (
                f'```{self.author.name}, Твои карты: {self.hand}, сумма: {sum_val}\n'
                f'Карты дилера: {self.dealer_hand}, сумма: {dealer_sum}```\n'
                f'{mention} выиграл {self.bet} скуфкоинов! 🎉'
            )
        elif self.reason == 'tie':
            dealer_sum = self._validate_sum(dealer=True)
            return (
                f'```{self.author.name}, Твои карты: {self.hand}, сумма: {sum_val}\n'
                f'Карты дилера: {self.dealer_hand}, сумма: {dealer_sum}```\n'
                f'{mention}, Это ничья! Ставка возвращена. 🤝'
            )

    def hit(self):
        """Игрок берет еще одну карту"""
        if not self.is_playing():
            return self.prepare_message()
            
        self._claim_card()
        player_sum = self._validate_sum()
        
        if player_sum > 21:
            self.reason = 'lose'
        elif player_sum == 21 or len(self.hand) >= 5:
            # Если 21 или 5 карт - автоматически выигрыш
            self._dealer_play()
        elif len(self.hand) >= 5 and player_sum <= 21:
            # 5 карт и не перебор - автоматический выигрыш
            self.reason = 'win'
            db.update_balance(self.author.id, self.bet * 2)
            
        return self.prepare_message()

    def _dealer_play(self):
        """Логика игры дилера"""
        dealer_sum = self._validate_sum(dealer=True)
        player_sum = self._validate_sum()
        
        # Дилер добирает карты пока сумма меньше 17
        while dealer_sum < 17 and len(self.dealer_hand) < 5:
            self._claim_card(dealer=True)
            dealer_sum = self._validate_sum(dealer=True)
        
        # Определение результата после хода дилера
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
        """Игрок останавливается"""
        if not self.is_playing():
            return self.prepare_message()
            
        # Запускаем логику дилера
        self._dealer_play()
        return self.prepare_message()
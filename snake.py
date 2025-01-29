# import random
# import db
# import config
# import math

# class Snake():
#     def __init__(self, author):
#         self.map = [
#             [0, 0, 0, 0, 0, 0, 0], # 0 - empty
#             [0, 0, 0, 0, 0, 0, 0], # 1 - head
#             [0, 0, 0, 0, 0, 0, 0], # 2 - player
#             [0, 0, 0, 0, 0, 0, 0], # 3 - tail
#             [0, 0, 0, 0, 0, 0, 0], # 4 - apple
#             [0, 0, 0, 0, 0, 0, 0]
#         ]
#         self.author = author
#         self.status = 'playing' # playing, lose, win
#         self.add_size = 0
#         self.head = [0, 1] # x, y
#         self.apple = [] # x, y
#         self.body = [] # [x, y], [x, y]
#         self.generate_apple()
#         self.move('stay')
#         self.paid = 0
#         self.pay = config.pay['snake']

#     def generate_apple(self):
#         free_y = []
#         for i in range(len(self.map)):
#          if self.map[i].count(0):
#             free_y.append(i)
#         if not free_y:
#             self.status = 'win'
#             self.paid = self.pay
#             db.updatemoney(self.author.id, self.pay)
#             return
#         y = random.choice(free_y)

#         free_x = []
#         for i in range(len(self.map[y])):
#             if self.map[y][i] == 0:
#                 free_x.append(i)
#         x = random.choice(free_x)

#         self.apple = [x, y]
#         self.map[y][x] = 4

#     def move(self, side):
#         if self.status != 'playing':
#             return self.prepare_message()
#         match side:
#             case 'up':
#                 x = 0; y = 1
#             case 'down':
#                 x = 0; y = -1
#             case 'right':
#                 x = 1; y = 0
#             case 'left':
#                 x = -1; y = 0
#             case 'stay':
#                 x = 0; y = 0

#         self.map[self.head[1]][self.head[0]] = 0
#         self.body.append(self.head.copy())
#         if not self.add_size:
#             self.map[self.body[0][1]][self.body[0][0]] = 0
#             self.body = self.body[1::]
#         if self.add_size:
#             self.add_size -= 1
#         for pos in self.body:
#             self.map[pos[1]][pos[0]] = 2
#         if self.body:
#             self.map[self.body[0][1]][self.body[0][0]] = 3 # draw tail

#         self.head[0] += x
#         self.head[1] -= y
#         if self.head[0] < 0:
#             self.head[0] = 6
#         if self.head[0] > 6:
#             self.head[0] = 0
#         if self.head[1] < 0:
#             self.head[1] = 5
#         if self.head[1] > 5:
#             self.head[1] = 0
#         if self.map[self.head[1]][self.head[0]] not in [0,4]:
#             self.status = 'lose'
#             self.paid = math.ceil((len(self.body) / 42) * (self.pay / 2))
#             db.updatemoney(self.author.id, self.paid)
#             self.prepare_message()

#         self.map[self.head[1]][self.head[0]] = 1

#         if self.head == self.apple:
#             self.generate_apple()
#             self.add_size = 1

#         return self.prepare_message()


#     def prepare_message(self):
#         msg = ''
#         for row in self.map:
#             msg += f'{row}\n'

#         msg = msg.replace('0', '▪️')
#         msg = msg.replace('1', '🔵')
#         msg = msg.replace('2', '🟩')
#         msg = msg.replace('3', '🟢')
#         msg = msg.replace('4', '🍎')
#         msg = msg.replace('[', '')
#         msg = msg.replace(']', '')
#         msg = msg.replace(',', '')
#         msg = msg.replace(' ', '')

#         match self.status:
#             case 'win':
#                 msg += f'You win {self.paid} nedocoins!\n'
#                 msg = msg.replace('🔵', '👑')
#             case 'lose':
#                 msg += f'You lose, you earned {self.paid} nedocoins!\n'
#                 msg = msg.replace('🔵', '💀')

#         return msg

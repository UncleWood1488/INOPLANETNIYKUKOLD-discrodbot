from db import *
from math import ceil
from random import choice
import functions


class svogame():
    def __init__(self, author, bet=0):
        self.id = author.id
        self.nation = str(author.name)
        self.mention = author.mention
        self.player = author
        self.hp = {}
        self.weapon = []
        self.money = 0
        self.armor = []
        self.vehicle = []
        self.hegrenade = []
        self.sgrenade = []
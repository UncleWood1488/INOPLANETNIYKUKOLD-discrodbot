import discord
import randomgame
from config import BOT_API_KEY

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

f = open("swastika.txt", "r")
print(f.read()) 

@client.event
async def on_ready():
    print("Ready!")

@client.event
async def on_message(message):
    if message.content.lower().startswith("свастика"):
        await message.reply(f.read())

@client.event
async def on_message(message):
    if message.content.lower().startswith("обама"):
        await message.channel.send("ЧМО")

@client.event
async def on_message(message):
    if message.content.startswith("рандом"):
        def randomgame():
            pass

        
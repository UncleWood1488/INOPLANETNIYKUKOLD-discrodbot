# import requests
# import datetime
# import pytz

# def changetz(date: str) -> str:
#     date_time = datetime.datetime.strptime(date[0:16], '%Y-%m-%dT%H:%M')
#     date_time = pytz.timezone('UTC').localize(date_time)
#     date_time = date_time.astimezone(pytz.timezone('Europe/Moscow'))
#     return datetime.datetime.strftime(date_time, "%Y.%m.%d %H:%M")

# last_egs_message_id = None
# async def egs_parse(bot, news_channel_id):
#     global last_egs_message_id
#     r = requests.get("https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=ru&country=RU&allowCountries=RU")
#     msg = '**Распродажи EPIC GAMES:**\n**'
#     for el in r.json()['data']['Catalog']['searchStore']['elements']:
#         title = el['title']
#         if not el['promotions']:
#             continue
#         if el['promotions']['promotionalOffers'] not in ["", None, []] and el['promotions']['promotionalOffers'][0]['promotionalOffers'][0]['endDate'] != None: # текущая распродажа
#             enddate = el['promotions']['promotionalOffers'][0]['promotionalOffers'][0]['endDate']
#             enddate = changetz(enddate)
#             msg += f'```bash\n Раздача "{title}" до "{enddate}"```'
#         else:
#             startdate = el['promotions']['upcomingPromotionalOffers'][0]['promotionalOffers'][0]['startDate']
#             startdate = changetz(startdate)
#             msg += f'```bash\n Начиная с "{startdate}" начнется раздача "{title}"```'
#     msg += '**'

#     channel = bot.get_channel(news_channel_id)
#     try:
#         if not last_egs_message_id:
#             last_egs_message_id = channel.last_message_id
#         last_egs_message = await channel.get_partial_message(last_egs_message_id).fetch()
#         if last_egs_message.content != msg:
#             msgid = await channel.send(msg)
#             last_egs_message_id = msgid.id
#     except:
#         msgid = await channel.send(msg)
#         last_egs_message_id = msgid.id

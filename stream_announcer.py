# stream_announcer.py
"""
Автоматический анонсер стримов на VK Video Live для Discord.
Проверяет статус эфира:
  1. Публичный API VK Video Live (заголовок + игра + статус)
  2. Парсинг HTML страницы канала (fallback)
  3. (Опционально) Авторизованный API, если задан VK_ACCESS_TOKEN

Аватарка — только локальная.
Не требует команд. Просто фоновый процесс.
"""

import os
import re
import asyncio
import aiohttp
import logging
import discord

logger = logging.getLogger(__name__)

# ---------------- НАСТРОЙКИ ----------------
STREAM_CHANNEL_ID = 407729828767203329   # Канал для анонсов
VKVIDEO_USERNAME = "unclewood"           # Ник на VK Video Live
CHECK_INTERVAL = 120                     # Секунды между проверками

# Цвет эмбеда — фиолетовый Twitch
EMBED_COLOR = 0x9146FF

# --- Локальная аватарка ---
# Путь можно переопределить через переменную окружения STREAM_AVATAR_PATH.
LOCAL_AVATAR_PATH = os.getenv(
    "STREAM_AVATAR_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "stream_avatar.png")
)

VK_STREAM_URL = f"https://live.vkvideo.ru/{VKVIDEO_USERNAME}"
VK_API_URL = f"https://api.live.vkvideo.ru/v1/channel/{VKVIDEO_USERNAME}/stream/slot/default"

# Токен можно положить в переменную окружения VK_ACCESS_TOKEN,
# если публичный API перестанет отдавать данные.
VK_ACCESS_TOKEN = os.getenv("VK_ACCESS_TOKEN")

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "Origin": "https://live.vkvideo.ru",
    "Referer": VK_STREAM_URL,
}


# ---------------- ПОЛУЧЕНИЕ ДАННЫХ ----------------

async def _fetch_stream_data(session: aiohttp.ClientSession) -> dict | None:
    """Запрашивает сырые данные о стриме."""
    headers = dict(_HEADERS)
    if VK_ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {VK_ACCESS_TOKEN}"

    try:
        async with session.get(
            VK_API_URL,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as r:
            if r.status != 200:
                logger.warning(f"[STREAM] API вернул HTTP {r.status}")
                return None
            payload = await r.json()
            return payload.get("data") or {}

    except asyncio.TimeoutError:
        logger.warning("[STREAM] API: таймаут")
        return None
    except Exception as e:
        logger.error(f"[STREAM] API: ошибка — {e}")
        return None


def _extract_category(stream: dict, channel: dict) -> str:
    """
    Пытается вытащить название игры/категории из разных полей ответа.
    VK Video Live может отдавать её под разными именами — пробуем все.
    """
    # 1) Прямые строковые поля
    for key in (
        "category", "categoryName", "category_name",
        "game", "gameName", "game_name",
    ):
        val = stream.get(key) or channel.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()

    # 2) Вложенные объекты — часто вида {"id":..., "name":...} или {"title":...}
    for key in ("category", "game", "categoryInfo", "gameInfo"):
        obj = stream.get(key) or channel.get(key)
        if isinstance(obj, dict):
            for inner in ("name", "title", "displayName"):
                val = obj.get(inner)
                if isinstance(val, str) and val.strip():
                    return val.strip()

    return ""


def _parse_stream_data(data: dict) -> dict:
    """Извлекает из ответа API заголовок, игру и статус эфира."""
    stream = data.get("stream") or {}
    channel = data.get("channel") or {}

    is_online = bool(stream.get("isOnline"))
    is_ended = bool(stream.get("isEnded", True))

    title = (
        stream.get("title")
        or stream.get("name")
        or stream.get("displayName")
        or channel.get("title")
        or channel.get("name")
        or ""
    )

    category = _extract_category(stream, channel)

    return {
        "is_live": is_online and not is_ended,
        "is_online": is_online,
        "is_ended": is_ended,
        "title": title.strip() if isinstance(title, str) else "",
        "category": category,
    }


async def _check_via_html(session: aiohttp.ClientSession) -> bool | None:
    """Парсинг HTML страницы канала — ищем маркеры live/offline."""
    try:
        async with session.get(
            VK_STREAM_URL,
            headers=_HEADERS,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as r:
            if r.status != 200:
                return None
            html = (await r.text()).lower()

            offline_markers = [
                '"isonline":false',
                '"status":"offline"',
                '"broadcast_status":"offline"',
                '"livestreamstatus":"offline"',
            ]
            for m in offline_markers:
                if m in html:
                    logger.info(f"[STREAM] HTML: найден оффлайн-маркер: {m}")
                    return False

            live_markers = [
                '"isonline":true',
                '"is_live":true',
                '"islive":true',
                '"status":"live"',
                '"broadcast_status":"live"',
                '"livestreamstatus":"live"',
                'live_hls',
                'live_dash',
            ]
            for m in live_markers:
                if m in html:
                    logger.info(f"[STREAM] HTML: найден live-маркер: {m}")
                    return True

            viewer_match = re.search(r'"viewers?"\s*:\s*(\d+)', html)
            if viewer_match:
                viewers = int(viewer_match.group(1))
                logger.info(f"[STREAM] HTML: viewers={viewers}")
                return viewers > 0

            logger.info("[STREAM] HTML: маркеры не найдены")
            return None

    except Exception as e:
        logger.error(f"[STREAM] HTML: ошибка — {e}")
        return None


async def get_stream_info() -> dict:
    """
    Возвращает словарь:
    {
        'is_live': bool,
        'title': str,
        'category': str,
        'is_online': bool,
        'is_ended': bool,
    }
    """
    async with aiohttp.ClientSession() as session:
        data = await _fetch_stream_data(session)

        if data is not None:
            info = _parse_stream_data(data)
            logger.info(
                f"[STREAM] API: online={info['is_online']}, ended={info['is_ended']}, "
                f"title='{info['title']}', category='{info['category']}'"
            )

            if info["is_live"]:
                return info

            html = await _check_via_html(session)
            if html is True:
                logger.info("[STREAM] API сказал оффлайн, но HTML нашёл live-маркеры")
                info["is_live"] = True
            return info

        html = await _check_via_html(session)
        return {
            "is_live": html is True,
            "is_online": html is True,
            "is_ended": html is not True,
            "title": "",
            "category": "",
        }


# ---------------- ЭМБЕД ----------------

def create_announcement_embed(stream_info: dict) -> discord.Embed:
    title = stream_info.get("title") or ""
    category = stream_info.get("category") or ""

    embed = discord.Embed(
        title="🔴СТРИМ НАЧАЛСЯ!",
        description=f"**{title}**" if title else None,
        color=EMBED_COLOR,
        url=VK_STREAM_URL,
        timestamp=discord.utils.utcnow(),
    )

    if category:
        embed.add_field(
            name="Игра",
            value=category,
            inline=False,
        )

    embed.add_field(
        name="VK Video Live",
        value=f"[Смотреть трансляцию]({VK_STREAM_URL})",
        inline=False,
    )
    return embed


# ---------------- КЛАСС-АННОНСЕР ----------------

class StreamAnnouncer:
    """
    Фоновый анонсер. Создаётся один раз, запускается в on_ready.
    """

    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.announced = False
        self._task = None

    def start(self):
        if self._task and not self._task.done():
            logger.info("[STREAM] Задача уже запущена")
            return
        self._task = asyncio.create_task(self._loop())
        logger.info("[STREAM] ✅ Задача анонсера запущена")

    async def _loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                await self._tick()
            except Exception as e:
                logger.error(f"[STREAM] Ошибка в цикле: {e}", exc_info=True)
            await asyncio.sleep(CHECK_INTERVAL)

    async def _tick(self):
        info = await get_stream_info()
        is_live = info["is_live"]
        logger.info(f"[STREAM] is_live={is_live}, announced={self.announced}")

        if is_live and not self.announced:
            channel = self.bot.get_channel(STREAM_CHANNEL_ID)
            if channel is None:
                logger.error(f"[STREAM] ❌ Канал {STREAM_CHANNEL_ID} не найден")
                return

            perms = channel.permissions_for(channel.guild.me)
            if not (perms.send_messages and perms.embed_links):
                logger.error(
                    f"[STREAM] ❌ Нет прав в #{channel.name}: "
                    f"send_messages={perms.send_messages}, embed_links={perms.embed_links}"
                )
                return

            try:
                await self._send_announcement(channel, info)
                self.announced = True
                logger.info("[STREAM] ✅ Анонс отправлен")
            except discord.Forbidden:
                logger.error("[STREAM] ❌ Discord запретил отправку (Forbidden)")
            except discord.HTTPException as e:
                logger.error(f"[STREAM] ❌ HTTP-ошибка: {e}")

        elif not is_live and self.announced:
            self.announced = False
            logger.info("[STREAM] Стрим завершён, флаг сброшен")

    async def _send_announcement(self, channel: discord.TextChannel, info: dict):
        embed = create_announcement_embed(info)

        if os.path.isfile(LOCAL_AVATAR_PATH):
            filename = os.path.basename(LOCAL_AVATAR_PATH)
            file = discord.File(LOCAL_AVATAR_PATH, filename=filename)
            embed.set_thumbnail(url=f"attachment://{filename}")
            logger.info(f"[STREAM] Отправляю с локальной аватаркой: {LOCAL_AVATAR_PATH}")
            await channel.send(embed=embed, file=file)
        else:
            logger.warning(
                f"[STREAM] ⚠️ Локальная аватарка не найдена: {LOCAL_AVATAR_PATH}. "
                f"Отправляю без картинки."
            )
            await channel.send(embed=embed)
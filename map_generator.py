import io
import discord
from config import MAP_SETTINGS
from db import get_all_player_positions, get_player_position

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️ Pillow не установлен. Функции карты будут отключены.")

class MapGenerator:
    def __init__(self):
        if not PIL_AVAILABLE:
            raise RuntimeError("Pillow не установлен. Установите: pip install Pillow")
        
        self.grid_size = MAP_SETTINGS['grid_size']
        self.cell_size = MAP_SETTINGS['cell_size']
        self.view_radius = MAP_SETTINGS['view_radius']
    
    def generate_full_map(self, player_positions=None):
        if not PIL_AVAILABLE:
            raise RuntimeError("Pillow не установлен")
            
        img_size = self.grid_size * self.cell_size
        img = Image.new('RGB', (img_size, img_size), color='white')
        draw = ImageDraw.Draw(img)
        
        for i in range(self.grid_size + 1):
            draw.line([(i * self.cell_size, 0), (i * self.cell_size, img_size)], fill='gray', width=1)
            draw.line([(0, i * self.cell_size), (img_size, i * self.cell_size)], fill='gray', width=1)
            
            if i % 5 == 0:
                draw.text((i * self.cell_size + 2, 2), str(i), fill='black')
                draw.text((2, i * self.cell_size + 2), str(i), fill='black')
        
        if player_positions:
            for player_id, (x, y) in player_positions.items():
                center_x = x * self.cell_size + self.cell_size // 2
                center_y = y * self.cell_size + self.cell_size // 2
                
                draw.ellipse([
                    center_x - 5, center_y - 5,
                    center_x + 5, center_y + 5
                ], fill='red')
                
        return img
    
    def generate_player_view(self, player_x, player_y, view_radius=None):
        if not PIL_AVAILABLE:
            raise RuntimeError("Pillow не установлен")
            
        if view_radius is None:
            view_radius = self.view_radius
            
        view_size = view_radius * 2 + 1
        img_size = view_size * self.cell_size
        
        img = Image.new('RGB', (img_size, img_size), color='white')
        draw = ImageDraw.Draw(img)
        
        for dx in range(-view_radius, view_radius + 1):
            for dy in range(-view_radius, view_radius + 1):
                grid_x = player_x + dx
                grid_y = player_y + dy
                
                if 0 <= grid_x < self.grid_size and 0 <= grid_y < self.grid_size:
                    cell_color = 'lightblue' if (grid_x + grid_y) % 2 == 0 else 'white'
                else:
                    cell_color = 'darkgray'
                
                x1 = (dx + view_radius) * self.cell_size
                y1 = (dy + view_radius) * self.cell_size
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size
                
                draw.rectangle([x1, y1, x2, y2], fill=cell_color, outline='gray')
                
                if dx == 0 and dy == 0:
                    draw.text((x1 + 2, y1 + 2), f"{grid_x},{grid_y}", fill='black')
        
        center = img_size // 2
        draw.ellipse([
            center - 8, center - 8,
            center + 8, center + 8
        ], fill='red')
        
        draw.text((10, 10), "N", fill='black')
        draw.text((img_size - 15, 10), "E", fill='black')
        draw.text((10, img_size - 20), "W", fill='black')
        draw.text((img_size - 15, img_size - 20), "S", fill='black')
        
        return img

    def image_to_file(self, image, filename="map.png"):
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return discord.File(img_bytes, filename=filename)

map_generator = MapGenerator() if PIL_AVAILABLE else None

async def generate_full_map_embed():
    if not PIL_AVAILABLE:
        embed = discord.Embed(
            title="❌ Функция карты недоступна",
            description="Установите Pillow: `pip install Pillow`",
            color=discord.Color.red()
        )
        return embed, None
    
    try:
        player_positions = get_all_player_positions()
        image = map_generator.generate_full_map(player_positions)
        file = map_generator.image_to_file(image, "full_map.png")
        
        embed = discord.Embed(
            title="🗺️ Полная карта игры",
            description="Обзор всей игровой территории",
            color=discord.Color.blue()
        )
        embed.set_image(url="attachment://full_map.png")
        embed.add_field(
            name="Игроков на карте",
            value=f"{len(player_positions)}",
            inline=True
        )
        
        return embed, file
    except Exception as e:
        embed = discord.Embed(
            title="❌ Ошибка генерации карты",
            description=str(e),
            color=discord.Color.red()
        )
        return embed, None

async def generate_player_map_embed(user_id, user_name):
    if not PIL_AVAILABLE:
        embed = discord.Embed(
            title="❌ Функция карты недоступна",
            description="Установите Pillow: `pip install Pillow`",
            color=discord.Color.red()
        )
        return embed, None
    
    try:
        x, y = get_player_position(user_id)
        image = map_generator.generate_player_view(x, y)
        file = map_generator.image_to_file(image, "player_map.png")
        
        embed = discord.Embed(
            title=f"📍 Позиция {user_name}",
            color=discord.Color.green()
        )
        embed.set_image(url="attachment://player_map.png")
        embed.add_field(
            name="Координаты",
            value=f"X: {x}, Y: {y}",
            inline=True
        )
        embed.add_field(
            name="Область видимости",
            value=f"{MAP_SETTINGS['view_radius']} клеток",
            inline=True
        )
        
        return embed, file
    except Exception as e:
        embed = discord.Embed(
            title="❌ Ошибка генерации карты",
            description=str(e),
            color=discord.Color.red()
        )
        return embed, None
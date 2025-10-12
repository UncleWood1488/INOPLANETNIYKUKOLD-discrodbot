import discord
from discord import Interaction
from discord.ui import View, Button
from db import sellfish, get_balance, get_fishing_stats, update_balance
from config import fish_data
from embedshop import create_category_embed, create_main_embed, create_sell_fish_embed, FISH_PRICES
from threading import Lock

sell_lock = Lock()

class SellFishButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.green,
            label="Продать всю рыбу",
            row=2
        )

    async def callback(self, interaction: Interaction):
        with sell_lock:
            fish_stats = get_fishing_stats(interaction.user.id)
            total = sum(count * FISH_PRICES[fish] for fish, count in fish_stats.items())
        
        if total <= 0:
            await interaction.response.send_message("У вас нет рыбы!", ephemeral=True)
            return
        
        update_balance(interaction.user.id, total)
        sellfish(interaction.user.id)
        
        await interaction.response.edit_message(
            embed=create_sell_fish_embed(interaction.user),
            view=ShopView(interaction.user)
        )

class ShopView(View):
    def __init__(self, user):
        super().__init__(timeout=30)
        self.user = user
        self.current_page = 1
        self.message = None  # Добавляем атрибут message

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)

    @discord.ui.button(label="Рыбалка 🎣", style=discord.ButtonStyle.primary, row=0)
    async def fishing_category(self, interaction: Interaction, button: Button):
        self.current_page = 1
        await self.update_embed(interaction)

    @discord.ui.button(label="Улучшения ⚙️", style=discord.ButtonStyle.success, row=0)
    async def upgrades_category(self, interaction: Interaction, button: Button):
        self.current_page = 2
        await self.update_embed(interaction)

    @discord.ui.button(label="Продать рыбу 💰", style=discord.ButtonStyle.secondary, row=0)
    async def sell_fish_page(self, interaction: Interaction, button: Button):
        self.current_page = 3
        self.clear_items()
        self.add_item(self.fishing_category)
        self.add_item(self.upgrades_category)
        self.add_item(self.sell_fish_page)
        self.add_item(self.back_button)
        self.add_item(self.close)
        self.add_item(SellFishButton())

        fish_stats = get_fishing_stats(self.user.id)
        if sum(fish_stats.values()) == 0:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Ошибка",
                    description="У вас нет рыбы для продажи!",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return

        await self.update_embed(interaction)

    @discord.ui.button(label="Назад 🔙", style=discord.ButtonStyle.gray, row=1)
    async def back_button(self, interaction: Interaction, button: Button):
        await interaction.response.edit_message(embed=create_main_embed(self.user), view=self)

    @discord.ui.button(label="Закрыть ❌", style=discord.ButtonStyle.red)
    async def close(self, interaction: Interaction, button: Button):
        try:
            await interaction.message.delete()
        except (discord.NotFound, discord.Forbidden):
            pass
        except Exception as e:
            print(f"[ERROR] Close shop: {str(e)}")
            await interaction.response.send_message("❌ Не удалось закрыть магазин!", ephemeral=True)
        finally:
            self.stop()

    async def update_embed(self, interaction: Interaction):
        embed = create_category_embed(interaction.user, self.current_page)
        await interaction.response.edit_message(embed=embed, view=self)
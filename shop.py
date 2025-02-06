import discord
from db import sellfish, get_balance, get_fishing_stats
from discord.ui import View, Button
from config import fish_data
from embedshop import create_category_embed, create_main_embed
from threading import Lock
sell_lock = Lock()


class ShopView(View):
    def __init__(self, user):
        super().__init__(timeout=30)
        self.user = user
        self.current_page = 1

    async def on_timeout(self):
        # Disable buttons after timeout
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

    @discord.ui.button(label="Рыбалка 🎣", style=discord.ButtonStyle.primary, row=0)
    async def fishing_category(self, interaction, button):
        self.current_page = 1
        await self.update_embed(interaction)

    @discord.ui.button(label="Улучшения ⚙️", style=discord.ButtonStyle.success, row=0)
    async def upgrades_category(self, interaction, button):
        self.current_page = 2
        await self.update_embed(interaction)

    @discord.ui.button(label="Назад 🔙", style=discord.ButtonStyle.gray, row=1)
    async def back_button(self, interaction, button):
        await interaction.response.edit_message(embed=create_main_embed(self.user), view=self)

    @discord.ui.button(label="Закрыть ❌", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.message.delete()
        except discord.NotFound:
            await interaction.response.send_message(
                "Сообщение уже удалено!", 
                ephemeral=True, 
                delete_after=5
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "Недостаточно прав для удаления!",
                ephemeral=True,
                delete_after=10
            )
        except Exception as e:
            print(f"[ERROR] Close shop: {str(e)}")
            await interaction.response.send_message(
                "Ошибка при закрытии магазина!",
                ephemeral=True,
                delete_after=10
            )
    @discord.ui.button(label="Продать рыбу 💰", style=discord.ButtonStyle.secondary, row=2)
    async def sell_fish_button(self, interaction):
        await interaction.response.defer()
        with sell_lock:
            fish_stats = get_fishing_stats(self.user.id)
        
        # Проверяем, есть ли рыба
        fish_stats = get_fishing_stats(self.user.id)
        total_fish = sum(fish_stats.values())
        
        if total_fish == 0:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Ошибка",
                    description="У вас нет рыбы для продажи!",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return
        
        # Продажа рыбы
        sellfish(self.user.id)
        balance = get_balance(self.user.id)
        
        # Обновляем сообщение
        embed = create_category_embed(self.user, self.current_page)
        await interaction.followup.send(
            embed=embed,
            view=self
        )

    async def update_embed(self, interaction):
        embed = create_category_embed(interaction.user, self.current_page)
        await interaction.response.edit_message(embed=embed, view=self)
    
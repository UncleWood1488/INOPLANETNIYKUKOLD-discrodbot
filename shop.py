import discord
from discord.ui import View, Button
from embedshop import create_category_embed, create_main_embed


class ShopView(View):
    def __init__(self, user):
        super().__init__(timeout=30)
        self.user = user
        self.current_page = 1

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

    async def update_embed(self, interaction):
        embed = create_category_embed(interaction.user, self.current_page)
        await interaction.response.edit_message(embed=embed, view=self)
    
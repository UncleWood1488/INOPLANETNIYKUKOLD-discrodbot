import discord
from discord import Interaction
from discord.ui import View, Button
from db import (
    sellfish, get_balance, get_fishing_stats, update_balance,
    get_upgrade, set_upgrade, get_all_upgrades, get_lootboxes
)
from config import fish_data
from embedshop import create_category_embed, create_main_embed, create_sell_fish_embed, FISH_PRICES
from threading import Lock
import functions

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
            fish_only = {k: v for k, v in fish_stats.items() if k in FISH_PRICES}
            total = sum(count * FISH_PRICES[fish] for fish, count in fish_only.items())
        
        if total <= 0:
            await interaction.response.send_message("У вас нет рыбы!", ephemeral=True)
            return
        
        update_balance(interaction.user.id, total)
        sellfish(interaction.user.id)
        
        embed = create_sell_fish_embed(interaction.user)
        await interaction.response.edit_message(embed=embed, view=self.view)


class ShopView(View):
    def __init__(self, user):
        super().__init__(timeout=30)
        self.user = user
        self.current_page = 0
        self.message = None
        self.rebuild_view(self.current_page)

    def rebuild_view(self, page: int):
        self.clear_items()
        self.current_page = page

        self.add_item(self.create_fishing_button())
        self.add_item(self.create_upgrades_button())
        self.add_item(self.create_sell_button())
        self.add_item(self.create_lootbox_button())

        self.add_item(self.create_close_button())

        if page != 0:
            self.add_item(self.create_back_button())

        if page == 1:
            upgrades = get_all_upgrades(self.user.id)
            self.add_item(self.create_upgrade_button('net', 'Сеть', 500, upgrades.get('net', 0)))
            self.add_item(self.create_upgrade_button('pro_rod', 'Удочка PRO', 1000, upgrades.get('pro_rod', 0)))
            self.add_item(self.create_placeholder_button('Заглушка 1'))
            self.add_item(self.create_placeholder_button('Заглушка 2'))

        elif page == 2:
            upgrades = get_all_upgrades(self.user.id)
            self.add_item(self.create_upgrade_button('improved_bag', 'Улучшенная сумка', 750, upgrades.get('improved_bag', 0)))
            self.add_item(self.create_upgrade_button('golden_pickaxe', 'Золотая кирка', 1500, upgrades.get('golden_pickaxe', 0)))
            self.add_item(self.create_placeholder_button('Заглушка 3'))
            self.add_item(self.create_placeholder_button('Заглушка 4'))

        elif page == 3:
            self.add_item(SellFishButton())

    def create_fishing_button(self):
        button = Button(label="Рыбалка 🎣", style=discord.ButtonStyle.primary, row=0)
        async def callback(interaction):
            if interaction.user.id != self.user.id:
                return await interaction.response.defer()
            self.rebuild_view(1)
            embed = create_category_embed(self.user, 1)
            await interaction.response.edit_message(embed=embed, view=self)
        button.callback = callback
        return button

    def create_upgrades_button(self):
        button = Button(label="Улучшения ⚙️", style=discord.ButtonStyle.success, row=0)
        async def callback(interaction):
            if interaction.user.id != self.user.id:
                return await interaction.response.defer()
            self.rebuild_view(2)
            embed = create_category_embed(self.user, 2)
            await interaction.response.edit_message(embed=embed, view=self)
        button.callback = callback
        return button

    def create_sell_button(self):
        button = Button(label="Продать рыбу 💰", style=discord.ButtonStyle.secondary, row=0)
        async def callback(interaction):
            if interaction.user.id != self.user.id:
                return await interaction.response.defer()
            fish_stats = get_fishing_stats(self.user.id)
            fish_only = {k: v for k, v in fish_stats.items() if k in FISH_PRICES}
            if sum(fish_only.values()) == 0:
                await interaction.response.send_message("У вас нет рыбы для продажи!", ephemeral=True)
                return
            self.rebuild_view(3)
            embed = create_category_embed(self.user, 3)
            await interaction.response.edit_message(embed=embed, view=self)
        button.callback = callback
        return button

    def create_lootbox_button(self):
        button = Button(label="Открыть лутбокс 📦", style=discord.ButtonStyle.blurple, row=0)
        async def callback(interaction):
            if interaction.user.id != self.user.id:
                return await interaction.response.defer()
            
            lootboxes = get_lootboxes(self.user.id)
            if lootboxes <= 0:
                await interaction.response.send_message("У вас нет лутбоксов!", ephemeral=True)
                return
            
            success, message = await functions.open_lootbox(self.user.id)
            if success:
                self.rebuild_view(0)
                embed = create_main_embed(self.user)
                await interaction.response.edit_message(embed=embed, view=self)
                await interaction.followup.send(f"📦 Результат: {message}", ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        button.callback = callback
        return button

    def create_back_button(self):
        button = Button(label="Назад 🔙", style=discord.ButtonStyle.gray, row=1)
        async def callback(interaction):
            if interaction.user.id != self.user.id:
                return await interaction.response.defer()
            self.rebuild_view(0)
            embed = create_main_embed(self.user)
            await interaction.response.edit_message(embed=embed, view=self)
        button.callback = callback
        return button

    def create_close_button(self):
        button = Button(label="Закрыть ❌", style=discord.ButtonStyle.red, row=1)
        async def callback(interaction):
            try:
                await interaction.message.delete()
            except:
                pass
            self.stop()
        button.callback = callback
        return button

    def create_upgrade_button(self, upgrade_name: str, label: str, price: int, owned: int):
        if owned:
            button = Button(label=f"{label} (Куплено)", style=discord.ButtonStyle.secondary, disabled=True, row=2)
            async def cb(interaction):
                await interaction.response.defer()
            button.callback = cb
        else:
            button = Button(label=f"{label} - {price}💰", style=discord.ButtonStyle.primary, row=2)
            async def cb(interaction):
                await self.handle_upgrade(interaction, upgrade_name, price)
            button.callback = cb
        return button

    def create_placeholder_button(self, label: str):
        button = Button(label=label, style=discord.ButtonStyle.secondary, disabled=True, row=3)
        async def cb(interaction):
            await interaction.response.send_message("⏳ Этот апгрейд в разработке!", ephemeral=True)
        button.callback = cb
        return button

    async def handle_upgrade(self, interaction: Interaction, upgrade_name: str, price: int):
        if interaction.user.id != self.user.id:
            return await interaction.response.defer()

        balance = get_balance(self.user.id)
        if balance < price:
            return await interaction.response.send_message("❌ Недостаточно средств!", ephemeral=True)

        if get_upgrade(self.user.id, upgrade_name) == 1:
            return await interaction.response.send_message("❌ Апгрейд уже куплен!", ephemeral=True)

        update_balance(self.user.id, -price)
        set_upgrade(self.user.id, upgrade_name, 1)

        self.rebuild_view(self.current_page)
        embed = create_category_embed(self.user, self.current_page)
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)
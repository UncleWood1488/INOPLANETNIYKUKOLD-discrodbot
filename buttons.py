import discord

#=========================================================================================================БЛЕКДЖЕК
async def bj_buttons(ctx, bjplayers):
    async def button_hit_callback(interaction):
        if ctx.author.id != interaction.user.id:
            return await interaction.response.defer()
        if interaction.user.id not in bjplayers:
            return await interaction.response.defer()
        if not bjplayers[interaction.user.id].is_playing():
            return await interaction.response.defer()
        
        msg = bjplayers[interaction.user.id].hit()
        if bjplayers[interaction.user.id].is_playing(): # рисовать кнопки, если после hit партия не завершена
            return await interaction.response.edit_message(content=msg)
        bj_buttons.stop()
        await interaction.response.edit_message(content=msg, view=None)

    async def button_stay_callback(interaction):
        if ctx.author.id != interaction.user.id:
            return await interaction.response.defer()
        if interaction.user.id not in bjplayers:
            return await interaction.response.defer()
        if not bjplayers[interaction.user.id].is_playing():
            return await interaction.response.defer()
        bj_buttons.stop()
        
        await interaction.response.edit_message(content=bjplayers[interaction.user.id].stay(), view=None)

    async def buttons_timeout():
        await ctx.reply('```Response timeout, clicking "Stay":```' + bjplayers[ctx.author.id].stay())

    bj_buttons = discord.ui.View()
    button_hit = discord.ui.Button(label="Hit!", style=discord.ButtonStyle.green, emoji="👊")
    button_stay = discord.ui.Button(label="Stay!", style=discord.ButtonStyle.red, emoji="✋")

    bj_buttons.on_timeout = buttons_timeout
    button_hit.callback = button_hit_callback
    button_stay.callback = button_stay_callback
    
    bj_buttons.add_item(button_hit)
    bj_buttons.add_item(button_stay)

    return bj_buttons
#=========================================================================================================БЛЕКДЖЕК
#=========================================================================================================ЗМЕЙКА
async def snake_buttons(ctx, snakeplayers):
    async def button_up_callback(interaction):
        if ctx.author.id != interaction.user.id:
            return await interaction.response.defer()
        if interaction.user.id not in snakeplayers:
            return await interaction.response.defer()
        if not snakeplayers[interaction.user.id].status == 'playing':
            return await interaction.response.defer()
        
        msg = snakeplayers[interaction.user.id].move('up')
        if snakeplayers[interaction.user.id].status == 'playing': # рисовать кнопки, если партия продолжается
            return await interaction.response.edit_message(content=msg)
        await interaction.response.edit_message(content=msg, view=None)

    async def button_down_callback(interaction):
        if ctx.author.id != interaction.user.id:
            return await interaction.response.defer()
        if interaction.user.id not in snakeplayers:
            return await interaction.response.defer()
        if not snakeplayers[interaction.user.id].status == 'playing':
            return await interaction.response.defer()
        
        msg = snakeplayers[interaction.user.id].move('down')
        if snakeplayers[interaction.user.id].status == 'playing': # рисовать кнопки, если партия продолжается
            return await interaction.response.edit_message(content=msg)
        await interaction.response.edit_message(content=msg, view=None)

    async def button_left_callback(interaction):
        if ctx.author.id != interaction.user.id:
            return await interaction.response.defer()
        if interaction.user.id not in snakeplayers:
            return await interaction.response.defer()
        if not snakeplayers[interaction.user.id].status == 'playing':
            return await interaction.response.defer()
        
        msg = snakeplayers[interaction.user.id].move('left')
        if snakeplayers[interaction.user.id].status == 'playing': # рисовать кнопки, если партия продолжается
            return await interaction.response.edit_message(content=msg)
        await interaction.response.edit_message(content=msg, view=None)

    async def button_right_callback(interaction):
        if ctx.author.id != interaction.user.id:
            return await interaction.response.defer()
        if interaction.user.id not in snakeplayers:
            return await interaction.response.defer()
        if not snakeplayers[interaction.user.id].status == 'playing':
            return await interaction.response.defer()
        
        msg = snakeplayers[interaction.user.id].move('right')
        if snakeplayers[interaction.user.id].status == 'playing': # рисовать кнопки, если партия продолжается
            return await interaction.response.edit_message(content=msg)
        await interaction.response.edit_message(content=msg, view=None)

    async def button_nothing_callback(interaction):
        return await interaction.response.defer()

    async def buttons_timeout():
        await ctx.reply('```Response timeout```')

    snake_buttons = discord.ui.View(timeout=None)
    button_nothing1 = discord.ui.Button(emoji="▪️", style=discord.ButtonStyle.gray, row=0)
    button_nothing2 = discord.ui.Button(emoji="▪️", style=discord.ButtonStyle.gray, row=0)
    button_up = discord.ui.Button(style=discord.ButtonStyle.blurple, emoji="⬆", row=0)
    button_down = discord.ui.Button(style=discord.ButtonStyle.blurple, emoji="⬇", row=1)
    button_left = discord.ui.Button(style=discord.ButtonStyle.blurple, emoji="⬅", row=1)
    button_right = discord.ui.Button(style=discord.ButtonStyle.blurple, emoji="➡", row=1)
    
    snake_buttons.on_timeout = buttons_timeout
    button_nothing1.callback = button_nothing_callback
    button_nothing2.callback = button_nothing_callback
    button_up.callback = button_up_callback
    button_down.callback = button_down_callback
    button_left.callback = button_left_callback
    button_right.callback = button_right_callback
    
    snake_buttons.add_item(button_nothing1)
    snake_buttons.add_item(button_up)
    snake_buttons.add_item(button_nothing2)
    snake_buttons.add_item(button_left)
    snake_buttons.add_item(button_down)
    snake_buttons.add_item(button_right)

    return snake_buttons
#=========================================================================================================ЗМЕЙКА
import discord

async def snake_buttons(ctx, snakeplayers):
    async def button_up_callback(interaction):
        if ctx.author.id != interaction.user.id:
            return await interaction.response.defer()
        if interaction.user.id not in snakeplayers:
            return await interaction.response.defer()
        game = snakeplayers[interaction.user.id]
        if game.status != 'playing':
            return await interaction.response.defer()
        
        msg = game.move('up')
        if game.status == 'playing':
            await interaction.response.edit_message(content=msg)
        else:
            del snakeplayers[interaction.user.id]
            await interaction.response.edit_message(content=msg, view=None)

    async def button_down_callback(interaction):
        if ctx.author.id != interaction.user.id:
            return await interaction.response.defer()
        if interaction.user.id not in snakeplayers:
            return await interaction.response.defer()
        game = snakeplayers[interaction.user.id]
        if game.status != 'playing':
            return await interaction.response.defer()
        
        msg = game.move('down')
        if game.status == 'playing':
            await interaction.response.edit_message(content=msg)
        else:
            del snakeplayers[interaction.user.id]
            await interaction.response.edit_message(content=msg, view=None)

    async def button_left_callback(interaction):
        if ctx.author.id != interaction.user.id:
            return await interaction.response.defer()
        if interaction.user.id not in snakeplayers:
            return await interaction.response.defer()
        game = snakeplayers[interaction.user.id]
        if game.status != 'playing':
            return await interaction.response.defer()
        
        msg = game.move('left')
        if game.status == 'playing':
            await interaction.response.edit_message(content=msg)
        else:
            del snakeplayers[interaction.user.id]
            await interaction.response.edit_message(content=msg, view=None)

    async def button_right_callback(interaction):
        if ctx.author.id != interaction.user.id:
            return await interaction.response.defer()
        if interaction.user.id not in snakeplayers:
            return await interaction.response.defer()
        game = snakeplayers[interaction.user.id]
        if game.status != 'playing':
            return await interaction.response.defer()
        
        msg = game.move('right')
        if game.status == 'playing':
            await interaction.response.edit_message(content=msg)
        else:
            del snakeplayers[interaction.user.id]
            await interaction.response.edit_message(content=msg, view=None)

    async def button_nothing_callback(interaction):
        return await interaction.response.defer()

    async def buttons_timeout():
        if ctx.author.id in snakeplayers:
            del snakeplayers[ctx.author.id]
        await ctx.reply('```Response timeout```')

    view = discord.ui.View(timeout=None)
    button_nothing1 = discord.ui.Button(emoji="▪️", style=discord.ButtonStyle.gray, row=0)
    button_nothing2 = discord.ui.Button(emoji="▪️", style=discord.ButtonStyle.gray, row=0)
    button_up = discord.ui.Button(style=discord.ButtonStyle.blurple, emoji="⬆", row=0)
    button_down = discord.ui.Button(style=discord.ButtonStyle.blurple, emoji="⬇", row=1)
    button_left = discord.ui.Button(style=discord.ButtonStyle.blurple, emoji="⬅", row=1)
    button_right = discord.ui.Button(style=discord.ButtonStyle.blurple, emoji="➡", row=1)
    
    view.on_timeout = buttons_timeout
    button_nothing1.callback = button_nothing_callback
    button_nothing2.callback = button_nothing_callback
    button_up.callback = button_up_callback
    button_down.callback = button_down_callback
    button_left.callback = button_left_callback
    button_right.callback = button_right_callback
    
    view.add_item(button_nothing1)
    view.add_item(button_up)
    view.add_item(button_nothing2)
    view.add_item(button_left)
    view.add_item(button_down)
    view.add_item(button_right)

    return view
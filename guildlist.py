import discord
guild_ids = [696082479752413274, 671985595903508490]
slash_guilds = []
for i in guild_ids:
    slash_guilds.append(discord.Object(i))

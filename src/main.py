# ----- required imports -----

from dotenv import load_dotenv
import os
import discord
import asyncio
from discord import app_commands
from discord.ext import commands  
from src.api import SteamAPI
from src.cache import cache

# ----- environment initialization -----

load_dotenv()

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)  

# ----- event handlers -----

@bot.command()
async def clear_guild_commands(ctx):
    guild = ctx.guild
    await bot.tree.clear_commands(guild=guild)
    await bot.tree.sync(guild=guild)
    await ctx.send("Cleared all guild commands.")

@bot.tree.command(name="compare", description="Compare multiplayer games")
async def compare_games(interaction: discord.Interaction, user1: discord.Member, user2: discord.Member):
    await interaction.response.defer()
    try:
        steam_id1 = user1.steam_id
        steam_id2 = user2.steam_id
        common_games = await find_common_games(steam_id1, steam_id2)
        embed = discord.Embed(title="🎮 Common Multiplayer Games")
        embed.add_field(name="Co-op Games", value="\n".join(g['name'] for g in common_games[:25]))
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await handle_error(interaction, e)

@bot.tree.command(name="cache_stats", description="Show Redis cache statistics")
async def cache_stats(interaction: discord.Interaction):
    stats = await cache.raw("info", "memory")
    await interaction.response.send_message(
        f"**Cache Stats**\n{stats.decode()[:1000]}",
        ephemeral=True
    )

async def find_common_games(steam_id1, steam_id2):
    games1, games2 = await asyncio.gather(
        SteamAPI.get_owned_games(steam_id1),
        SteamAPI.get_owned_games(steam_id2)
    )
    return [g for g in games1 if g in games2]

async def handle_error(interaction, error):
    await interaction.followup.send(
        f"❌ Error: {str(error)}",
        ephemeral=True
    )

@bot.event
async def on_ready():
    print(f'Bot connected as {bot.user}')
    try:
        GUILD_ID = os.getenv('DISCORD_GUILD_ID')
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            await bot.tree.clear_commands(guild=guild)
            await bot.tree.sync(guild=guild)
            print("Cleared all guild commands.")
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"Synced {len(synced)} commands to guild {GUILD_ID}.")
        else:
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} commands globally.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

# ----- execution code -----

if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))
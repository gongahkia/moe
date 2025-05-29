from dotenv import load_dotenv
import os
import discord
from discord import app_commands
from src.api import SteamAPI
from src.cache import cache

load_dotenv()

intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

@tree.command(name="compare", description="Compare multiplayer games")
async def compare_games(interaction: discord.Interaction, user1: discord.Member, user2: discord.Member):
    await interaction.response.defer()
    
    try:
        # Steam ID resolution logic here
        common_games = await find_common_games(steam_id1, steam_id2)
        
        embed = discord.Embed(title="🎮 Common Multiplayer Games")
        embed.add_field(name="Co-op Games", value="\n".join(g['name'] for g in common_games[:25]))
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await handle_error(interaction, e)

@tree.command(name="cache_stats", description="Show Redis cache statistics")
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
        synced = await tree.sync()
        print(f"Synced {len(synced)} commands globally.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))
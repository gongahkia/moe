# ----- required imports -----

from dotenv import load_dotenv
import os
import discord
import asyncio
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from typing import List, Optional
import json

from src.api import SteamAPI
from src.cache import cache
from src.database import db
from src.ai_recommendations import ai_engine
from src.price_tracker import price_tracker
from src.matchmaking import matchmaking

# ----- environment initialization -----

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# ----- helper functions -----

async def get_steam_id_from_user(discord_id: int) -> Optional[str]:
    """Get Steam ID for a Discord user from database"""
    return await db.get_steam_id(discord_id)

async def find_common_games(steam_ids: List[str]) -> List[dict]:
    """Find games common to all provided Steam IDs"""
    if not steam_ids:
        return []

    # Get games for all users in parallel
    games_lists = await asyncio.gather(
        *[SteamAPI.get_owned_games(sid) for sid in steam_ids]
    )

    # Find intersection
    if not games_lists:
        return []

    # Start with first user's games
    common_appids = {game['appid'] for game in games_lists[0]}

    # Intersect with other users' games
    for games in games_lists[1:]:
        user_appids = {game['appid'] for game in games}
        common_appids &= user_appids

    # Return full game data for common games
    common_games = [
        game for game in games_lists[0]
        if game['appid'] in common_appids
    ]

    return sorted(common_games, key=lambda x: x.get('playtime_forever', 0), reverse=True)

def format_game_list(games: List[dict], limit: int = 25) -> str:
    """Format game list for Discord embed"""
    if not games:
        return "No games found"

    lines = []
    for i, game in enumerate(games[:limit], 1):
        name = game.get('name', 'Unknown')
        playtime = game.get('playtime_forever', 0) / 60
        lines.append(f"{i}. **{name}** ({playtime:.1f}h)")

    if len(games) > limit:
        lines.append(f"\n...and {len(games) - limit} more games")

    return "\n".join(lines)

async def handle_error(interaction: discord.Interaction, error: Exception):
    """Handle errors gracefully"""
    error_msg = f"❌ Error: {str(error)}"
    try:
        if interaction.response.is_done():
            await interaction.followup.send(error_msg, ephemeral=True)
        else:
            await interaction.response.send_message(error_msg, ephemeral=True)
    except:
        print(f"Error sending error message: {error}")

# ----- event handlers -----

@bot.event
async def on_ready():
    """Bot startup handler"""
    print(f'Bot connected as {bot.user}')

    # Initialize database
    await db.initialize()
    print("Database initialized")

    # Sync commands
    try:
        GUILD_ID = os.getenv('DISCORD_GUILD_ID')
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"Synced {len(synced)} commands to guild {GUILD_ID}")
        else:
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} commands globally")
    except Exception as e:
        print(f"Error syncing commands: {e}")

# ----- user registration commands -----

@bot.tree.command(name="register", description="Link your Discord account to Steam")
@app_commands.describe(steam_id="Your Steam ID or vanity URL")
async def register(interaction: discord.Interaction, steam_id: str):
    """Register user with Steam ID"""
    await interaction.response.defer(ephemeral=True)

    try:
        # Try to resolve vanity URL if needed
        if not steam_id.isdigit():
            resolved_id = await SteamAPI.resolve_vanity_url(steam_id)
            if not resolved_id:
                await interaction.followup.send(
                    "❌ Could not resolve Steam ID. Please provide a valid Steam ID or vanity URL.",
                    ephemeral=True
                )
                return
            steam_id = resolved_id

        # Get Steam profile to validate
        summaries = await SteamAPI.get_player_summaries([steam_id])
        if not summaries:
            await interaction.followup.send(
                "❌ Could not find Steam profile. Please check your Steam ID.",
                ephemeral=True
            )
            return

        steam_username = summaries[0].get('personaname', 'Unknown')

        # Register user
        success = await db.register_user(
            interaction.user.id,
            steam_id,
            steam_username
        )

        if success:
            # Cache their games
            games = await SteamAPI.get_owned_games(steam_id)
            await db.cache_user_games(steam_id, games)

            embed = discord.Embed(
                title="✅ Registration Successful",
                description=f"Linked to Steam account: **{steam_username}**",
                color=discord.Color.green()
            )
            embed.add_field(name="Games Found", value=str(len(games)))
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(
                "❌ Registration failed. Please try again.",
                ephemeral=True
            )

    except Exception as e:
        await handle_error(interaction, e)

@bot.tree.command(name="unregister", description="Unlink your Steam account")
async def unregister(interaction: discord.Interaction):
    """Unregister user"""
    await interaction.response.defer(ephemeral=True)

    try:
        success = await db.unregister_user(interaction.user.id)
        if success:
            await interaction.followup.send(
                "✅ Successfully unlinked your Steam account.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "❌ You are not registered.",
                ephemeral=True
            )
    except Exception as e:
        await handle_error(interaction, e)

@bot.tree.command(name="profile", description="View a user's Steam profile and gaming stats")
@app_commands.describe(user="User to view (defaults to yourself)")
async def profile(interaction: discord.Interaction, user: Optional[discord.Member] = None):
    """View user profile"""
    await interaction.response.defer()

    try:
        target_user = user or interaction.user
        user_data = await db.get_user(target_user.id)

        if not user_data:
            await interaction.followup.send(
                f"❌ {target_user.mention} is not registered. Use `/register` first.",
                ephemeral=True
            )
            return

        steam_id = user_data['steam_id']

        # Get Steam profile
        summaries = await SteamAPI.get_player_summaries([steam_id])
        if not summaries:
            await interaction.followup.send("❌ Could not fetch Steam profile.", ephemeral=True)
            return

        profile = summaries[0]

        # Get games
        games = await SteamAPI.get_owned_games(steam_id)
        total_playtime = sum(g.get('playtime_forever', 0) for g in games) / 60  # Convert to hours

        # Get recent games
        recent_games = await SteamAPI.get_recently_played_games(steam_id)

        # Create embed
        embed = discord.Embed(
            title=f"🎮 Steam Profile: {profile.get('personaname', 'Unknown')}",
            color=discord.Color.blue()
        )

        if 'avatarfull' in profile:
            embed.set_thumbnail(url=profile['avatarfull'])

        embed.add_field(name="Games Owned", value=str(len(games)), inline=True)
        embed.add_field(name="Total Playtime", value=f"{total_playtime:.1f} hours", inline=True)
        embed.add_field(name="Registered", value=user_data['registered_at'][:10], inline=True)

        # Top 5 games
        if games:
            top_games = sorted(games, key=lambda x: x.get('playtime_forever', 0), reverse=True)[:5]
            top_games_text = "\n".join([
                f"{i}. {g['name']} - {g.get('playtime_forever', 0)/60:.1f}h"
                for i, g in enumerate(top_games, 1)
            ])
            embed.add_field(name="Top 5 Games", value=top_games_text, inline=False)

        # Recent activity
        if recent_games:
            recent_text = "\n".join([
                f"• {g['name']} ({g.get('playtime_2weeks', 0)/60:.1f}h recently)"
                for g in recent_games[:3]
            ])
            embed.add_field(name="Recent Activity", value=recent_text, inline=False)

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await handle_error(interaction, e)

# ----- game comparison commands -----

@bot.tree.command(name="compare", description="Find shared multiplayer games between users")
@app_commands.describe(user1="First user", user2="Second user")
async def compare(interaction: discord.Interaction, user1: discord.Member, user2: discord.Member):
    """Compare games between two users"""
    await interaction.response.defer()

    try:
        # Get Steam IDs
        steam_id1 = await get_steam_id_from_user(user1.id)
        steam_id2 = await get_steam_id_from_user(user2.id)

        if not steam_id1:
            await interaction.followup.send(
                f"❌ {user1.mention} is not registered. Use `/register` first.",
                ephemeral=True
            )
            return

        if not steam_id2:
            await interaction.followup.send(
                f"❌ {user2.mention} is not registered. Use `/register` first.",
                ephemeral=True
            )
            return

        # Find common games
        common_games = await find_common_games([steam_id1, steam_id2])

        if not common_games:
            await interaction.followup.send(
                f"❌ No shared games found between {user1.mention} and {user2.mention}."
            )
            return

        # Create embed
        embed = discord.Embed(
            title=f"🎮 Shared Games: {user1.display_name} & {user2.display_name}",
            description=f"Found **{len(common_games)}** shared games!",
            color=discord.Color.green()
        )

        embed.add_field(
            name="Top Games by Playtime",
            value=format_game_list(common_games, 20),
            inline=False
        )

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await handle_error(interaction, e)

@bot.tree.command(name="compare_group", description="Find shared games for a group (3-10 players)")
@app_commands.describe(
    user1="User 1",
    user2="User 2",
    user3="User 3 (optional)",
    user4="User 4 (optional)",
    user5="User 5 (optional)"
)
async def compare_group(
    interaction: discord.Interaction,
    user1: discord.Member,
    user2: discord.Member,
    user3: Optional[discord.Member] = None,
    user4: Optional[discord.Member] = None,
    user5: Optional[discord.Member] = None
):
    """Compare games for a group of users"""
    await interaction.response.defer()

    try:
        users = [u for u in [user1, user2, user3, user4, user5] if u]

        # Get Steam IDs
        steam_ids = []
        for user in users:
            steam_id = await get_steam_id_from_user(user.id)
            if not steam_id:
                await interaction.followup.send(
                    f"❌ {user.mention} is not registered. Use `/register` first.",
                    ephemeral=True
                )
                return
            steam_ids.append(steam_id)

        # Find common games
        common_games = await find_common_games(steam_ids)

        if not common_games:
            await interaction.followup.send(
                f"❌ No shared games found among the group."
            )
            return

        # Create embed
        user_names = ", ".join([u.display_name for u in users])
        embed = discord.Embed(
            title=f"🎮 Group Games ({len(users)} players)",
            description=f"Found **{len(common_games)}** games everyone owns!",
            color=discord.Color.gold()
        )

        embed.add_field(name="Players", value=user_names, inline=False)
        embed.add_field(
            name="Shared Games",
            value=format_game_list(common_games, 20),
            inline=False
        )

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await handle_error(interaction, e)

# ----- AI recommendation commands -----

@bot.tree.command(name="recommend", description="Get AI-powered game recommendations")
@app_commands.describe(user1="First user", user2="Second user (optional)", context="Context (e.g., 'chill', 'competitive')")
async def recommend(
    interaction: discord.Interaction,
    user1: discord.Member,
    user2: Optional[discord.Member] = None,
    context: Optional[str] = None
):
    """Get AI recommendations"""
    await interaction.response.defer()

    try:
        users = [user1, user2] if user2 else [user1]

        # Get Steam IDs
        steam_ids = []
        for user in users:
            steam_id = await get_steam_id_from_user(user.id)
            if not steam_id:
                await interaction.followup.send(
                    f"❌ {user.mention} is not registered.",
                    ephemeral=True
                )
                return
            steam_ids.append(steam_id)

        # Get shared games
        if len(steam_ids) > 1:
            games = await find_common_games(steam_ids)
        else:
            games = await SteamAPI.get_owned_games(steam_ids[0])

        if not games:
            await interaction.followup.send("❌ No games found.")
            return

        # Get AI recommendation
        recommendation = await ai_engine.get_game_recommendations(
            games,
            context=context
        )

        embed = discord.Embed(
            title="🤖 AI Game Recommendations",
            description=recommendation,
            color=discord.Color.purple()
        )

        if context:
            embed.set_footer(text=f"Context: {context}")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await handle_error(interaction, e)

@bot.tree.command(name="ask", description="Ask Moe a question about games")
@app_commands.describe(question="Your question")
async def ask(interaction: discord.Interaction, question: str):
    """Ask AI a question"""
    await interaction.response.defer()

    try:
        # Get user's gaming data for context
        user_data = await db.get_user(interaction.user.id)
        context_data = None

        if user_data:
            games = await SteamAPI.get_owned_games(user_data['steam_id'])
            context_data = {
                'user': user_data,
                'game_count': len(games),
                'top_games': [g['name'] for g in games[:10]]
            }

        answer = await ai_engine.answer_gaming_question(question, context_data)

        embed = discord.Embed(
            title="🤖 Moe's Answer",
            description=answer,
            color=discord.Color.blue()
        )

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await handle_error(interaction, e)

# ----- game night scheduler commands -----

@bot.tree.command(name="schedule_night", description="Schedule a game night")
@app_commands.describe(
    game_name="Name of the game",
    date="Date (YYYY-MM-DD)",
    time="Time (HH:MM in 24h format)"
)
async def schedule_night(
    interaction: discord.Interaction,
    game_name: str,
    date: str,
    time: str
):
    """Schedule a game night"""
    await interaction.response.defer()

    try:
        # Parse datetime
        datetime_str = f"{date} {time}"
        scheduled_time = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")

        # Create event in database
        event_id = await db.create_game_event(
            guild_id=interaction.guild_id,
            game_name=game_name,
            scheduled_time=scheduled_time,
            created_by=interaction.user.id
        )

        embed = discord.Embed(
            title="📅 Game Night Scheduled!",
            description=f"**{game_name}**",
            color=discord.Color.green()
        )
        embed.add_field(name="When", value=f"{date} at {time}", inline=False)
        embed.add_field(name="Created by", value=interaction.user.mention, inline=False)
        embed.add_field(
            name="RSVP",
            value="React with ✅ if you're coming!",
            inline=False
        )

        message = await interaction.followup.send(embed=embed)
        await message.add_reaction("✅")
        await message.add_reaction("❌")
        await message.add_reaction("❔")

    except ValueError:
        await interaction.followup.send(
            "❌ Invalid date/time format. Use YYYY-MM-DD for date and HH:MM for time.",
            ephemeral=True
        )
    except Exception as e:
        await handle_error(interaction, e)

@bot.tree.command(name="my_events", description="View your upcoming game nights")
async def my_events(interaction: discord.Interaction):
    """View user's scheduled events"""
    await interaction.response.defer(ephemeral=True)

    try:
        events = await db.get_upcoming_events(interaction.guild_id)

        if not events:
            await interaction.followup.send("No upcoming events scheduled.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📅 Upcoming Game Nights",
            color=discord.Color.blue()
        )

        for event in events[:10]:
            embed.add_field(
                name=event['game_name'],
                value=f"📆 {event['scheduled_time']}\n👤 <@{event['created_by']}>",
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        await handle_error(interaction, e)

# ----- price tracking commands -----

@bot.tree.command(name="deals", description="Show current game deals")
async def deals(interaction: discord.Interaction):
    """Show current deals"""
    await interaction.response.defer()

    try:
        current_deals = await price_tracker.get_current_deals(limit=10)

        if not current_deals:
            await interaction.followup.send("No deals found at the moment.")
            return

        embed = discord.Embed(
            title="💰 Current Game Deals",
            color=discord.Color.gold()
        )

        for deal in current_deals[:10]:
            title = deal.get('title', 'Unknown')
            price_new = deal.get('price_new', 0)
            price_old = deal.get('price_old', 0)
            cut = deal.get('price_cut', 0)

            embed.add_field(
                name=title,
                value=f"~~${price_old:.2f}~~ → **${price_new:.2f}** ({cut}% off)",
                inline=False
            )

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await handle_error(interaction, e)

@bot.tree.command(name="watch", description="Get notified when a game goes on sale")
@app_commands.describe(game_name="Name of the game", target_price="Target price (optional)")
async def watch(interaction: discord.Interaction, game_name: str, target_price: Optional[float] = None):
    """Add price watch"""
    await interaction.response.defer(ephemeral=True)

    try:
        # Check if user is registered
        user = await db.get_user(interaction.user.id)
        if not user:
            await interaction.followup.send(
                "❌ Please register first with `/register`.",
                ephemeral=True
            )
            return

        # Get current price
        current_price_data = await price_tracker.get_game_price(game_name)
        current_price = None

        if current_price_data:
            prices = current_price_data.get('list', [])
            if prices:
                current_price = min(p.get('price_new', float('inf')) for p in prices)

        # Add alert
        await db.add_price_alert(
            discord_id=interaction.user.id,
            appid=0,  # We'll need to look this up
            game_name=game_name,
            target_price=target_price,
            current_price=current_price
        )

        msg = f"✅ Now watching **{game_name}**"
        if target_price:
            msg += f"\nYou'll be notified when it drops to ${target_price:.2f} or below"
        if current_price:
            msg += f"\nCurrent price: ${current_price:.2f}"

        await interaction.followup.send(msg, ephemeral=True)

    except Exception as e:
        await handle_error(interaction, e)

# ----- statistics commands -----

@bot.tree.command(name="stats", description="View gaming statistics")
@app_commands.describe(user="User to view stats for (defaults to yourself)")
async def stats(interaction: discord.Interaction, user: Optional[discord.Member] = None):
    """View gaming stats"""
    await interaction.response.defer()

    try:
        target_user = user or interaction.user
        user_data = await db.get_user(target_user.id)

        if not user_data:
            await interaction.followup.send(
                f"❌ {target_user.mention} is not registered.",
                ephemeral=True
            )
            return

        steam_id = user_data['steam_id']

        # Get games
        games = await SteamAPI.get_owned_games(steam_id)
        total_playtime = sum(g.get('playtime_forever', 0) for g in games) / 60

        # Calculate stats
        played_games = [g for g in games if g.get('playtime_forever', 0) > 0]
        avg_playtime = total_playtime / len(played_games) if played_games else 0

        # Get top games
        top_games = sorted(games, key=lambda x: x.get('playtime_forever', 0), reverse=True)[:5]

        embed = discord.Embed(
            title=f"📊 Gaming Stats: {target_user.display_name}",
            color=discord.Color.blue()
        )

        embed.add_field(name="Total Games", value=str(len(games)), inline=True)
        embed.add_field(name="Games Played", value=str(len(played_games)), inline=True)
        embed.add_field(name="Total Playtime", value=f"{total_playtime:.0f}h", inline=True)
        embed.add_field(name="Avg Playtime", value=f"{avg_playtime:.1f}h", inline=True)

        # Top 5 games
        top_games_text = "\n".join([
            f"{i}. **{g['name']}** - {g.get('playtime_forever', 0)/60:.1f}h"
            for i, g in enumerate(top_games, 1)
        ])
        embed.add_field(name="Top 5 Games", value=top_games_text, inline=False)

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await handle_error(interaction, e)

# ----- matchmaking and friend finder commands -----

@bot.tree.command(name="match_me", description="Find server members with similar gaming interests")
async def match_me(interaction: discord.Interaction):
    """Find compatible gaming partners"""
    await interaction.response.defer()

    try:
        # Check if user is registered
        user_data = await db.get_user(interaction.user.id)
        if not user_data:
            await interaction.followup.send(
                "❌ Please register first with `/register`.",
                ephemeral=True
            )
            return

        # Get all registered guild members
        guild_members = [m.id for m in interaction.guild.members if not m.bot]

        # Find matches
        matches = await matchmaking.find_best_matches(
            interaction.user.id,
            guild_members,
            limit=5
        )

        if not matches:
            await interaction.followup.send(
                "❌ No matches found. Make sure other server members are registered!"
            )
            return

        embed = discord.Embed(
            title=f"🤝 Your Best Gaming Matches",
            description=f"Based on library overlap and gaming preferences",
            color=discord.Color.gold()
        )

        for i, (member_id, compat) in enumerate(matches, 1):
            member = await interaction.guild.fetch_member(member_id)
            stars = "⭐" * int(compat['score'] / 20)

            embed.add_field(
                name=f"{i}. {member.display_name} - {compat['score']}% {stars}",
                value=(
                    f"📚 {compat['shared_games']} shared games\n"
                    f"📊 {compat['library_overlap']}% library overlap"
                ),
                inline=False
            )

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await handle_error(interaction, e)

@bot.tree.command(name="compatibility", description="Check gaming compatibility with another user")
@app_commands.describe(user="User to check compatibility with")
async def compatibility(interaction: discord.Interaction, user: discord.Member):
    """Check compatibility with specific user"""
    await interaction.response.defer()

    try:
        # Check if both users are registered
        user1_steam = await db.get_steam_id(interaction.user.id)
        user2_steam = await db.get_steam_id(user.id)

        if not user1_steam:
            await interaction.followup.send(
                "❌ You need to register first with `/register`.",
                ephemeral=True
            )
            return

        if not user2_steam:
            await interaction.followup.send(
                f"❌ {user.mention} is not registered.",
                ephemeral=True
            )
            return

        # Calculate compatibility
        compat = await matchmaking.calculate_compatibility(user1_steam, user2_steam)

        # Format message
        message = matchmaking.format_compatibility_message(
            interaction.user.display_name,
            user.display_name,
            compat
        )

        embed = discord.Embed(
            title="🤝 Gaming Compatibility",
            description=message,
            color=discord.Color.blue()
        )

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await handle_error(interaction, e)

@bot.tree.command(name="find_players", description="Find who in the server owns a specific game")
@app_commands.describe(game_name="Name of the game")
async def find_players(interaction: discord.Interaction, game_name: str):
    """Find players who own a specific game"""
    await interaction.response.defer()

    try:
        # Get all guild members
        guild_members = [m.id for m in interaction.guild.members if not m.bot]

        # Find players
        results = await matchmaking.find_players_for_game(game_name, guild_members)

        if not results:
            await interaction.followup.send(
                f"❌ No one in this server owns **{game_name}**."
            )
            return

        embed = discord.Embed(
            title=f"🎮 Players who own {game_name}",
            description=f"Found {len(results)} players",
            color=discord.Color.green()
        )

        for i, (member_id, game_data) in enumerate(results[:10], 1):
            member = await interaction.guild.fetch_member(member_id)
            playtime = game_data['playtime']

            embed.add_field(
                name=f"{i}. {member.display_name}",
                value=f"⏱️ {playtime:.1f} hours played",
                inline=False
            )

        if len(results) > 10:
            embed.set_footer(text=f"...and {len(results) - 10} more players")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await handle_error(interaction, e)

@bot.tree.command(name="lfg", description="Post a Looking For Group message")
@app_commands.describe(
    game_name="Name of the game",
    players_needed="Number of players needed",
    description="Additional details (optional)"
)
async def lfg(
    interaction: discord.Interaction,
    game_name: str,
    players_needed: int = 1,
    description: Optional[str] = None
):
    """Post LFG"""
    await interaction.response.defer()

    try:
        # Create LFG post
        post_id = await db.create_lfg_post(
            guild_id=interaction.guild_id,
            discord_id=interaction.user.id,
            game_name=game_name,
            description=description,
            players_needed=players_needed
        )

        embed = discord.Embed(
            title="🎮 Looking For Group",
            color=discord.Color.blue()
        )

        embed.add_field(name="Game", value=game_name, inline=True)
        embed.add_field(name="Players Needed", value=str(players_needed), inline=True)
        embed.add_field(name="Posted by", value=interaction.user.mention, inline=False)

        if description:
            embed.add_field(name="Details", value=description, inline=False)

        embed.set_footer(text="React with 🎯 to join!")

        message = await interaction.followup.send(embed=embed)
        await message.add_reaction("🎯")

    except Exception as e:
        await handle_error(interaction, e)

@bot.tree.command(name="lfg_board", description="View all active LFG posts")
async def lfg_board(interaction: discord.Interaction):
    """View LFG board"""
    await interaction.response.defer()

    try:
        posts = await db.get_active_lfg_posts(interaction.guild_id)

        if not posts:
            await interaction.followup.send("No active LFG posts right now.")
            return

        embed = discord.Embed(
            title="🎮 Looking For Group Board",
            description=f"{len(posts)} active posts",
            color=discord.Color.blue()
        )

        for post in posts[:10]:
            poster = await interaction.guild.fetch_member(post['discord_id'])
            value = f"👤 {poster.mention}\n👥 {post['players_needed']} needed"

            if post['description']:
                value += f"\n💭 {post['description']}"

            embed.add_field(
                name=post['game_name'],
                value=value,
                inline=False
            )

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await handle_error(interaction, e)

# ----- utility commands -----

@bot.tree.command(name="cache", description="Show Redis cache statistics")
async def cache_stats(interaction: discord.Interaction):
    """Show cache stats"""
    try:
        stats = await cache.raw("info", "memory")
        await interaction.response.send_message(
            f"**Cache Stats**\n```{stats.decode()[:1000]}```",
            ephemeral=True
        )
    except Exception as e:
        await handle_error(interaction, e)

@bot.tree.command(name="help", description="Show all available commands")
async def help_command(interaction: discord.Interaction):
    """Show help"""
    embed = discord.Embed(
        title="🤖 Moe Bot - Help",
        description="Your Discord server's AI gaming companion",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="👤 User Registration",
        value="`/register` - Link your Steam account\n"
              "`/unregister` - Unlink your Steam account\n"
              "`/profile` - View your or another user's profile",
        inline=False
    )

    embed.add_field(
        name="🎮 Game Comparison",
        value="`/compare` - Find shared games between 2 users\n"
              "`/compare_group` - Find shared games for 3-5 users",
        inline=False
    )

    embed.add_field(
        name="🤖 AI Features",
        value="`/recommend` - Get AI game recommendations\n"
              "`/ask` - Ask Moe any gaming question",
        inline=False
    )

    embed.add_field(
        name="📅 Game Nights",
        value="`/schedule_night` - Schedule a game night\n"
              "`/my_events` - View upcoming events",
        inline=False
    )

    embed.add_field(
        name="💰 Deals & Prices",
        value="`/deals` - View current game deals\n"
              "`/watch` - Get alerts for price drops",
        inline=False
    )

    embed.add_field(
        name="🤝 Matchmaking",
        value="`/match_me` - Find compatible players\n"
              "`/compatibility` - Check compatibility with someone\n"
              "`/find_players` - Who owns a specific game\n"
              "`/lfg` - Post Looking For Group\n"
              "`/lfg_board` - View LFG board",
        inline=False
    )

    embed.add_field(
        name="📊 Statistics",
        value="`/stats` - View gaming statistics\n"
              "`/cache` - View cache statistics",
        inline=False
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ----- execution code -----

if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))

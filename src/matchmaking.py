# ----- required imports -----

from typing import List, Dict, Any, Tuple
from src.api import SteamAPI
from src.database import db
import asyncio

# ----- class definitions -----

class MatchmakingEngine:
    """Find compatible players and match users based on gaming preferences"""

    async def calculate_compatibility(
        self,
        user1_steam_id: str,
        user2_steam_id: str
    ) -> Dict[str, Any]:
        """
        Calculate compatibility score between two users

        Returns:
            Dictionary with compatibility score and breakdown
        """
        # Get games for both users
        games1, games2 = await asyncio.gather(
            SteamAPI.get_owned_games(user1_steam_id),
            SteamAPI.get_owned_games(user2_steam_id)
        )

        if not games1 or not games2:
            return {'score': 0, 'details': 'Insufficient data'}

        # Calculate various compatibility factors
        library_overlap = self._calculate_library_overlap(games1, games2)
        playtime_similarity = self._calculate_playtime_similarity(games1, games2)
        shared_games_count = len([g for g in games1 if g['appid'] in {g2['appid'] for g2 in games2}])

        # Weighted average
        compatibility_score = (
            library_overlap * 0.4 +
            playtime_similarity * 0.3 +
            min(shared_games_count / 20, 1.0) * 0.3
        ) * 100

        return {
            'score': round(compatibility_score, 1),
            'shared_games': shared_games_count,
            'library_overlap': round(library_overlap * 100, 1),
            'playtime_similarity': round(playtime_similarity * 100, 1)
        }

    def _calculate_library_overlap(
        self,
        games1: List[Dict],
        games2: List[Dict]
    ) -> float:
        """Calculate percentage of library overlap"""
        if not games1 or not games2:
            return 0.0

        appids1 = {g['appid'] for g in games1}
        appids2 = {g['appid'] for g in games2}

        intersection = len(appids1 & appids2)
        union = len(appids1 | appids2)

        return intersection / union if union > 0 else 0.0

    def _calculate_playtime_similarity(
        self,
        games1: List[Dict],
        games2: List[Dict]
    ) -> float:
        """Calculate similarity in playtime patterns"""
        # Get shared games
        appids1 = {g['appid']: g.get('playtime_forever', 0) for g in games1}
        appids2 = {g['appid']: g.get('playtime_forever', 0) for g in games2}

        shared_appids = set(appids1.keys()) & set(appids2.keys())

        if not shared_appids:
            return 0.0

        # Calculate correlation of playtime for shared games
        similarities = []
        for appid in shared_appids:
            time1 = appids1[appid]
            time2 = appids2[appid]

            # Both played = high similarity
            if time1 > 60 and time2 > 60:  # Both played > 1 hour
                # More similar if playtimes are closer
                max_time = max(time1, time2)
                min_time = min(time1, time2)
                similarity = min_time / max_time if max_time > 0 else 1.0
                similarities.append(similarity)

        return sum(similarities) / len(similarities) if similarities else 0.0

    async def find_best_matches(
        self,
        discord_id: int,
        guild_members: List[int],
        limit: int = 5
    ) -> List[Tuple[int, Dict[str, Any]]]:
        """
        Find best gaming matches from a list of Discord IDs

        Args:
            discord_id: User's Discord ID
            guild_members: List of Discord IDs to check against
            limit: Max number of matches to return

        Returns:
            List of (discord_id, compatibility_data) tuples sorted by score
        """
        # Get user's Steam ID
        user_steam_id = await db.get_steam_id(discord_id)
        if not user_steam_id:
            return []

        # Get Steam IDs for all guild members
        matches = []

        for member_id in guild_members:
            if member_id == discord_id:
                continue

            member_steam_id = await db.get_steam_id(member_id)
            if not member_steam_id:
                continue

            # Calculate compatibility
            compatibility = await self.calculate_compatibility(
                user_steam_id,
                member_steam_id
            )

            matches.append((member_id, compatibility))

        # Sort by compatibility score
        matches.sort(key=lambda x: x[1]['score'], reverse=True)

        return matches[:limit]

    async def find_players_for_game(
        self,
        game_name: str,
        guild_members: List[int]
    ) -> List[Tuple[int, Dict[str, Any]]]:
        """
        Find guild members who own and play a specific game

        Args:
            game_name: Name of the game to search for
            guild_members: List of Discord IDs to check

        Returns:
            List of (discord_id, game_data) tuples
        """
        results = []

        for member_id in guild_members:
            steam_id = await db.get_steam_id(member_id)
            if not steam_id:
                continue

            # Get their games
            games = await SteamAPI.get_owned_games(steam_id)

            # Search for the game
            for game in games:
                if game_name.lower() in game.get('name', '').lower():
                    results.append((member_id, {
                        'game': game.get('name'),
                        'appid': game.get('appid'),
                        'playtime': game.get('playtime_forever', 0) / 60
                    }))
                    break

        # Sort by playtime
        results.sort(key=lambda x: x[1]['playtime'], reverse=True)

        return results

    def format_compatibility_message(
        self,
        user1_name: str,
        user2_name: str,
        compatibility: Dict[str, Any]
    ) -> str:
        """Format compatibility data into a readable message"""
        score = compatibility['score']
        stars = "⭐" * int(score / 20)

        message = f"**{user1_name}** & **{user2_name}**: {score}% compatible {stars}\n\n"
        message += f"📚 {compatibility['shared_games']} shared games\n"
        message += f"📊 {compatibility['library_overlap']}% library overlap\n"
        message += f"🎮 {compatibility['playtime_similarity']}% playtime similarity\n"

        if score >= 80:
            message += "\n✨ Excellent match! You have very similar gaming tastes."
        elif score >= 60:
            message += "\n👍 Great match! Plenty of games to play together."
        elif score >= 40:
            message += "\n👌 Good match! You have some common interests."
        else:
            message += "\n🤝 Different tastes, but might discover new games together!"

        return message

# ----- global matchmaking engine instance -----

matchmaking = MatchmakingEngine()

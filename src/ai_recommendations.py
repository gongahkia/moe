# ----- required imports -----

from typing import List, Dict, Any, Optional
import os
import json

# ----- environment initialization -----

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# ----- class definitions -----

class AIRecommendationEngine:
    """AI-powered game recommendation engine using Claude or GPT"""

    def __init__(self):
        self.anthropic_key = ANTHROPIC_API_KEY
        self.openai_key = OPENAI_API_KEY
        self.use_anthropic = bool(ANTHROPIC_API_KEY)

    async def get_game_recommendations(
        self,
        shared_games: List[Dict[str, Any]],
        user_preferences: Dict[str, Any] = None,
        context: str = None
    ) -> str:
        """
        Generate AI-powered game recommendations

        Args:
            shared_games: List of games all users have
            user_preferences: Optional user preferences and playtime data
            context: Optional context like "chill", "competitive", etc.

        Returns:
            Formatted recommendation text
        """
        if self.use_anthropic:
            return await self._get_anthropic_recommendations(
                shared_games, user_preferences, context
            )
        elif self.openai_key:
            return await self._get_openai_recommendations(
                shared_games, user_preferences, context
            )
        else:
            return self._get_fallback_recommendations(shared_games)

    async def _get_anthropic_recommendations(
        self,
        shared_games: List[Dict[str, Any]],
        user_preferences: Dict[str, Any],
        context: str
    ) -> str:
        """Get recommendations using Anthropic Claude"""
        try:
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=self.anthropic_key)

            # Build the prompt
            prompt = self._build_recommendation_prompt(
                shared_games, user_preferences, context
            )

            message = await client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            return message.content[0].text

        except Exception as e:
            print(f"Error getting Anthropic recommendations: {e}")
            return self._get_fallback_recommendations(shared_games)

    async def _get_openai_recommendations(
        self,
        shared_games: List[Dict[str, Any]],
        user_preferences: Dict[str, Any],
        context: str
    ) -> str:
        """Get recommendations using OpenAI GPT"""
        try:
            import openai

            openai.api_key = self.openai_key

            # Build the prompt
            prompt = self._build_recommendation_prompt(
                shared_games, user_preferences, context
            )

            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are Moe, a friendly gaming companion bot that helps friends find games to play together."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"Error getting OpenAI recommendations: {e}")
            return self._get_fallback_recommendations(shared_games)

    def _build_recommendation_prompt(
        self,
        shared_games: List[Dict[str, Any]],
        user_preferences: Dict[str, Any],
        context: str
    ) -> str:
        """Build the AI prompt for recommendations"""
        games_list = []
        for game in shared_games[:20]:  # Limit to top 20 games
            game_info = f"- {game.get('name', 'Unknown')}"
            if 'playtime_forever' in game:
                hours = game['playtime_forever'] / 60
                game_info += f" ({hours:.1f} hours played)"
            if 'genres' in game:
                game_info += f" - Genres: {', '.join(game['genres'])}"
            games_list.append(game_info)

        prompt = f"""You are Moe, a friendly Discord bot that helps gaming communities find games to play together.

Context: {context if context else 'Friends looking for a game to play together'}

Shared Games Library:
{chr(10).join(games_list)}

"""

        if user_preferences:
            prompt += f"\nUser Preferences:\n"
            if 'preferred_genres' in user_preferences:
                prompt += f"- Preferred genres: {', '.join(user_preferences['preferred_genres'])}\n"
            if 'recent_games' in user_preferences:
                prompt += f"- Recently played: {', '.join(user_preferences['recent_games'])}\n"

        prompt += """
Please recommend 2-3 games from their shared library that would be great to play together right now.
For each recommendation:
1. Explain why it's a good choice given the context
2. Mention any relevant gameplay features
3. Suggest how many players should join

Keep your response friendly, concise (under 300 words), and enthusiastic!
"""

        return prompt

    def _get_fallback_recommendations(
        self,
        shared_games: List[Dict[str, Any]]
    ) -> str:
        """Fallback recommendations when AI is unavailable"""
        if not shared_games:
            return "No shared games found!"

        # Sort by playtime
        sorted_games = sorted(
            shared_games,
            key=lambda x: x.get('playtime_forever', 0),
            reverse=True
        )

        recommendations = ["Here are some games you both own:\n"]

        for i, game in enumerate(sorted_games[:5], 1):
            name = game.get('name', 'Unknown')
            playtime = game.get('playtime_forever', 0) / 60
            recommendations.append(
                f"{i}. **{name}** - {playtime:.1f} hours played"
            )

        return "\n".join(recommendations)

    async def answer_gaming_question(
        self,
        question: str,
        user_data: Dict[str, Any] = None
    ) -> str:
        """
        Answer natural language questions about gaming

        Args:
            question: User's question
            user_data: Context about users and their games

        Returns:
            AI-generated answer
        """
        if self.use_anthropic:
            return await self._answer_with_anthropic(question, user_data)
        elif self.openai_key:
            return await self._answer_with_openai(question, user_data)
        else:
            return "AI recommendations are not configured. Please set ANTHROPIC_API_KEY or OPENAI_API_KEY."

    async def _answer_with_anthropic(
        self,
        question: str,
        user_data: Dict[str, Any]
    ) -> str:
        """Answer questions using Claude"""
        try:
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=self.anthropic_key)

            context = ""
            if user_data:
                context = f"\nContext about the users:\n{json.dumps(user_data, indent=2)}\n"

            prompt = f"""You are Moe, a friendly Discord bot that helps gaming communities.
{context}
User question: {question}

Please provide a helpful, friendly response. Keep it concise and actionable."""

            message = await client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=800,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            return message.content[0].text

        except Exception as e:
            print(f"Error with Anthropic: {e}")
            return "I'm having trouble processing that right now. Please try again later!"

    async def _answer_with_openai(
        self,
        question: str,
        user_data: Dict[str, Any]
    ) -> str:
        """Answer questions using GPT"""
        try:
            import openai

            openai.api_key = self.openai_key

            context = ""
            if user_data:
                context = f"\nContext about the users:\n{json.dumps(user_data, indent=2)}\n"

            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are Moe, a friendly Discord bot that helps gaming communities find games to play together."},
                    {"role": "user", "content": f"{context}\n\nUser question: {question}"}
                ],
                max_tokens=800,
                temperature=0.7
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"Error with OpenAI: {e}")
            return "I'm having trouble processing that right now. Please try again later!"

# ----- global AI engine instance -----

ai_engine = AIRecommendationEngine()

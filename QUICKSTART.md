# Moe Bot - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites

- Python 3.10 or higher
- Discord Bot Token ([Get one here](https://discord.com/developers/applications))
- Steam API Key ([Get one here](https://steamcommunity.com/dev/apikey))
- Redis (optional, for caching)
- Anthropic or OpenAI API Key (optional, for AI features)

---

## Step 1: Clone and Setup

```bash
# Navigate to project directory
cd moe

# Create virtual environment
python3 -m venv myenv
source myenv/bin/activate  # Windows: myenv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Step 2: Configure Environment

```bash
# Copy example environment file
cp .env.example src/.env

# Edit with your credentials
nano src/.env  # or use your favorite editor
```

**Minimum Required Configuration**:
```env
DISCORD_TOKEN=your_discord_bot_token_here
STEAM_API_KEY=your_steam_api_key_here
REDIS_URL=redis://localhost:6379/0
DATABASE_PATH=./data/moe.db
```

**Optional (for AI features)**:
```env
ANTHROPIC_API_KEY=your_anthropic_key_here
# OR
OPENAI_API_KEY=your_openai_key_here
```

---

## Step 3: Setup Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application or select existing one
3. Go to **Bot** tab
4. Enable these **Privileged Gateway Intents**:
   - ✅ Presence Intent
   - ✅ Server Members Intent
   - ✅ Message Content Intent

5. Go to **OAuth2 → URL Generator**
6. Select scopes:
   - ✅ `bot`
   - ✅ `applications.commands`

7. Select bot permissions:
   - ✅ Send Messages
   - ✅ View Channels
   - ✅ Read Message History
   - ✅ Use Slash Commands
   - ✅ Add Reactions

8. Copy the generated URL and invite bot to your server

---

## Step 4: Start Redis (Optional but Recommended)

### Using Docker:
```bash
docker run -d -p 6379:6379 redis:alpine
```

### Using Docker Compose:
```bash
docker-compose up -d redis
```

### macOS (Homebrew):
```bash
brew install redis
brew services start redis
```

### Skip Redis:
If you don't want to use Redis, the bot will still work but without caching. API calls will be slower and you may hit rate limits.

---

## Step 5: Run the Bot

```bash
python -m src.main
```

You should see:
```
Bot connected as YourBotName#1234
Database initialized
Synced X commands globally
```

---

## Step 6: Test Basic Commands

In your Discord server:

### 1. Register Your Steam Account
```
/register YOUR_STEAM_ID
```

Find your Steam ID:
- Steam profile URL: `steamcommunity.com/id/VANITY_NAME` → use `VANITY_NAME`
- Or use your numeric Steam ID (17 digits starting with 7656119...)

### 2. View Your Profile
```
/profile
```

### 3. Compare Games with a Friend
```
/compare @friend1 @friend2
```

### 4. Get AI Recommendations (if configured)
```
/recommend @yourself context:chill
```

### 5. View All Commands
```
/help
```

---

## 🐳 Docker Setup (Alternative)

### Full Stack with Docker Compose

```bash
# Build and start all services
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop services
docker-compose down
```

---

## Troubleshooting

### Commands not appearing?
1. Make sure bot has `applications.commands` scope
2. Wait up to 1 hour for global sync, or:
3. Add `DISCORD_GUILD_ID` to `.env` for instant guild sync

### "Could not find Steam profile"?
- Make sure Steam profile is **public**
- Check Steam ID is correct (17 digits or vanity URL)

### Redis connection error?
- Ensure Redis is running: `redis-cli ping` should return `PONG`
- Check `REDIS_URL` in `.env` matches your Redis setup

### Database errors?
- Ensure `data/` directory exists
- Check write permissions on `data/` folder

### AI features not working?
- Verify `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` is set
- Check API key is valid and has credits
- Bot will fall back to simple recommendations if AI unavailable

---

## Next Steps

1. **Invite More Users**: Get your server members to `/register`
2. **Try AI Features**: Use `/ask` and `/recommend` with AI enabled
3. **Schedule Game Night**: Use `/schedule_night` to organize sessions
4. **Find Matches**: Use `/match_me` to find compatible players
5. **Track Deals**: Use `/watch` to monitor game prices

---

## Useful Commands Quick Reference

| Command | Description | Example |
|---------|-------------|---------|
| `/register <id>` | Link Steam account | `/register gaben` |
| `/compare @user1 @user2` | Find shared games | `/compare @alice @bob` |
| `/recommend @user` | AI game suggestions | `/recommend @alice context:chill` |
| `/match_me` | Find compatible players | `/match_me` |
| `/schedule_night` | Plan gaming session | `/schedule_night Dota 2 2025-11-15 20:00` |
| `/deals` | View current sales | `/deals` |
| `/stats @user` | View gaming stats | `/stats @alice` |
| `/help` | Show all commands | `/help` |

---

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/gongahkia/moe/issues)
- **Documentation**: See `README.md` and `IMPLEMENTATION.md`
- **Discord**: Join our community (coming soon)

---

## Pro Tips

💡 **Use vanity URLs**: `/register gaben` is easier than numeric IDs

💡 **Enable AI**: Set `ANTHROPIC_API_KEY` for much better recommendations

💡 **Guild sync**: Add `DISCORD_GUILD_ID` to `.env` for instant command updates

💡 **Price alerts**: Use `/watch` without target price to track any sale

💡 **Group games**: Use `/compare_group` for 3+ players instead of multiple `/compare`

---

*Ready to game? Type `/help` in Discord to get started!* 🎮

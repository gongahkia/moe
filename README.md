[![](https://img.shields.io/badge/moe_1.0.0-passing-dark_green)](https://github.com/gongahkia/moe/releases/tag/1.0.0)
[![](https://img.shields.io/badge/moe_2.0.0-passing-green)](https://github.com/gongahkia/moe/releases/tag/2.0.0)

# `Moe`

Discord bot that suggests Multiplayer [Steam](https://store.steampowered.com/) Games you can play with friends by comparing your [Steam Libraries](https://steam.fandom.com/wiki/Steam_Library) per [genre](https://store.steampowered.com/tag/browse/#global_492).

<div align="center">
    <img src="./asset/reference/moe-profile.png" width=65%>
</div>

## Stack

* *Backend*: [Python](https://www.python.org/)
* *Package*: [Docker](https://www.docker.com/)
* *Database*: [SQLite](https://www.sqlite.org/), [aiosqlite](https://github.com/omnilib/aiosqlite)
* *Cache*: [Redis](https://redis.io/)
* *AI*: [Anthropic Claude](https://www.anthropic.com/), [OpenAI GPT](https://openai.com/) 
* *Testing*: [pytest](https://pytest.org/) 
* *API*: [Discord Developer API](https://discord.com/developers/docs/reference), [Steam Web API](https://steamcommunity.com/dev), [IsThereAnyDeal API](https://isthereanydeal.com/)

## Commands

### User Management

| Command | Description |
| :--- | :--- |
| `/register <steam_id>` | Link your Discord account to Steam (supports Steam ID or vanity URL) |
| `/unregister` | Unlink your Steam account from Discord |
| `/profile [@user]` | View your or another user's Steam profile, gaming stats, top games, and recent activity |

### Game Comparison

| Command | Description |
| :--- | :--- | 
| `/compare <user1> <user2>` | Find shared multiplayer Steam games between two Discord server members | 
| `/compare_group <user1> <user2> [user3] [user4] [user5]` | Find games that 3-5 players all own together |

### AI Features

| Command | Description |
| :--- | :--- |
| `/recommend <user1> [user2] [context]` | Get AI-powered game recommendations based on your libraries and preferences (requires AI API key) |
| `/ask <question>` | Ask Moe any gaming-related question in natural language |

### Game Night Scheduler
| Command | Description |
| :--- | :--- |
| `/schedule_night <game> <date> <time>` | Schedule a gaming session with automatic RSVP reactions |
| `/my_events` | View all upcoming game nights in your server |

### Deals & Price Tracking
| Command | Description |
| :--- | :--- |
| `/deals` | Show current game deals and sales from multiple stores |
| `/watch <game> [target_price]` | Get notified when a game goes on sale or hits your target price |

### Matchmaking & Friend Finder
| Command | Description |
| :--- | :--- |
| `/match_me` | Find server members with similar gaming interests and compatible libraries |
| `/compatibility <user>` | Check gaming compatibility score with another user |
| `/find_players <game>` | See who in your server owns a specific game |
| `/lfg <game> <players_needed> [description]` | Post a "Looking For Group" message |
| `/lfg_board` | View all active LFG posts in your server |

### Statistics & Analytics
| Command | Description | 
| :--- | :--- | 
| `/stats [@user]` | View comprehensive gaming statistics (total playtime, games owned, top 5 games) |
| `/cache` | Show current Redis cache statistics | 

### Help
| Command | Description |
| :--- | :--- |
| `/help` | Display all available commands with descriptions |

## Architecture

![](./asset/reference/architecture.png)

## Usage

The below instructions are for locally hosting `Moe`.

1. Create a [Discord application](https://discord.com/developers/applications) and a bot for that application.

2. Enable the following permissions under *Priviledged Gateway Intents* in the Bot tab.
    1. Presence Intent
    2. Server Members Intent
    3. Message Content Intent
    4. Application Commands Intent

3. Enable the following permissions under *Bot Permissions* in the Bot tab.
    1. Send Messages
    2. View Channel
    3. Read Message History
    4. Use Slash Commands
    5. Add Reactions

4. Create a `.env` file in the `./src/` directory with your configuration:

**Minimum Required Configuration:**

```env
DISCORD_TOKEN=your_discord_bot_token_here
STEAM_API_KEY=your_steam_api_key_here
REDIS_URL=redis://localhost:6379/0
DATABASE_PATH=./data/moe.db
```

**Optional Configuration (for AI features):**

```env
# Add ONE of the following for AI-powered recommendations
ANTHROPIC_API_KEY=your_anthropic_api_key_here
# OR
OPENAI_API_KEY=your_openai_api_key_here
```

**For Faster Command Sync:**

```env
DISCORD_GUILD_ID=your_discord_server_id_here
```

See `.env.example` for a complete template.

5. Install dependencies and run:

**Using Make (Recommended):**

```console
$ make install          # Install dependencies
$ make run-local        # Run the bot
```

**Manual Installation:**

```console
$ python3 -m venv myenv
$ source myenv/bin/activate  # On Windows: myenv\Scripts\activate
$ pip install -r requirements.txt
$ python -m src.main
```

**Using Docker:**

```console
$ docker-compose up --build
```

6. **First Time Setup**: Once the bot is running, use `/register <your_steam_id>` in Discord to link your Steam account.

### Command Sync

- Note that it can take up to an hour to propagate `Moe`'s [Application Commands](https://discord.com/developers/docs/interactions/application-commands) with [Global Sync](https://stackoverflow.com/questions/76692316/how-to-sync-commands-globally-with-discord-py).
- To circumvent this issue and instantly sync commands, add your `DISCORD_GUILD_ID` to the `.env` file as shown above.

## Reference

The name `Moe` is in reference to [Moseph "Moe" Mastro Giovanni](https://adventuretime.fandom.com/wiki/Moev), the founder of [MO Co.](https://adventuretime.fandom.com/wiki/MO_Co.) and the creator of [BMO](https://adventuretime.fandom.com/wiki/BMO) and all other [MOs](https://adventuretime.fandom.com/wiki/MOshttps://adventuretime.fandom.com/wiki/MOs). Moe first makes an appearance in the [Be More](https://adventuretime.fandom.com/wiki/Be_Morehttps://adventuretime.fandom.com/wiki/Be_More) episode of the completed [Cartoon Network](https://en.wikipedia.org/wiki/Cartoon_Network) series [Adventure Time](https://adventuretime.fandom.com/wiki/Adventure_Time_Wikihttps://adventuretime.fandom.com/wiki/Adventure_Time_Wiki).

![](./asset/logo/moe.jpg)

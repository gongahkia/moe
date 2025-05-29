[![](https://img.shields.io/badge/moe_1.0.0-passing-green)](https://github.com/gongahkia/moe/releases/tag/1.0.0) 

# `Moe`

Discord bot that suggests Multiplayer [Steam](https://store.steampowered.com/) Games you can play with friends by comparing your [Steam Libraries](https://steam.fandom.com/wiki/Steam_Library) per [genre](https://store.steampowered.com/tag/browse/#global_492).

<div align="center">
    <img src="./asset/reference/moe-profile.png" width=65%>
</div>

## Stack

* *Backend*: [Python](https://www.python.org/)
* *Package*: [Docker](https://www.docker.com/https://www.docker.com/)
* *Cache*: [Redis](https://redis.io/)
* *API*: [Discord Developer API](https://discord.com/developers/docs/reference), [Steam Web API](https://steamcommunity.com/dev)

## Commands

| Command | Description | Example |
| :--- | :--- | :---: |
| `/cache` | Show current Redis cache statistics | ![](./asset/reference/cache-1.png) <br> ![](./asset/reference/cache-2.png)|
| `/compare <server_member_1> <server_member_2>` | Finds and categorizes shared multiplayer Steam games between two Discord server members | ![](./asset/reference/compare-1.png) <br> ![](./asset/reference/compare-2.png) |

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
4. Place your Discord bot token, Steam API key and Redis URL in a `.env` file within `./src/`.

```env
DISCORD_TOKEN=XXX
STEAM_API_KEY=XXX
REDIS_URL=redis://redis:6379/0
```

5. Run the following.

```console
$ python3 -m venv myenv
$ source myenv source/bin/activate
$ pip install -r requirements.txt
```

6. Then run either of the following.

```console
$ docker-compose build && docker-compose up
```

```console
$ make config
$ make
```

7. Note that it can take up to an hour to propogate `Moe`'s [Application Commands](https://discord.com/developers/docs/interactions/application-commands) with [Global Sync](https://stackoverflow.com/questions/76692316/how-to-sync-commands-globally-with-discord-py). 
8. To circumvent this issue, instantly sync `Moe`'s [Application Commands](https://discord.com/developers/docs/interactions/application-commands) by placing your Discord bot token, Discord Guild ID, Steam API key and Redis URL in a `.env` file within `./src/`.

```env
DISCORD_TOKEN=XXX
DISCORD_GUILD_ID=XXX
STEAM_API_KEY=XXX
REDIS_URL=redis://redis:6379/0
```

## Other notes

...

## Reference

The name `Moe` is in reference to [Moseph "Moe" Mastro Giovanni](https://adventuretime.fandom.com/wiki/Moev), the founder of [MO Co.](https://adventuretime.fandom.com/wiki/MO_Co.) and the creator of [BMO](https://adventuretime.fandom.com/wiki/BMO) and all other [MOs](https://adventuretime.fandom.com/wiki/MOshttps://adventuretime.fandom.com/wiki/MOs). Moe first makes an appearance in the [Be More](https://adventuretime.fandom.com/wiki/Be_Morehttps://adventuretime.fandom.com/wiki/Be_More) episode of the completed [Cartoon Network](https://en.wikipedia.org/wiki/Cartoon_Network) series [Adventure Time](https://adventuretime.fandom.com/wiki/Adventure_Time_Wikihttps://adventuretime.fandom.com/wiki/Adventure_Time_Wiki).

![](./asset/logo/moe.jpg)

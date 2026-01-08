# seeding-reward-bot
Discord Bot for encouraging and rewarding seeding for select games.

Proudly used in:
- [Glow's Battlegrounds Community](https://discord.gg/glows).

## Setup
This section talks about how to deploy the bot to your Discord server.

### Creating the Bot via Discord Developer Portal
The official instructions for creating a Discord Bot are located on the [discord.py home page](https://discordpy.readthedocs.io/en/stable/discord.html).

This bot requires *no* Privileged Gateway Intents.

Currently *no* permissions are required for the bot to operate as only slash commands are used.

### Clone the repo
`cd` to where you'd like to keep this
```
git clone https://github.com/robbmanes/seeding-reward-bot.git
cd seeding-reward-bot
git fetch --tags
git checkout $(git describe --tags $(git rev-list --tags --max-count=1))
```

### Copy example .env and compose files
```
cp example.env .env
cp example-compose.yml compose.yml
```

### Edit .env
Use your favorite editor or try `nano` or `vim`
```
nano .env
```

Add your `DISCORD_TOKEN`, set who the maintainer on discord will be with their id(s) in `MAINTAINER_DISCORD_IDS`

Set the `RCON_URL`'s to wherever your crcon is accessed at

You'll need to make another user account in CRCON for this, set the password to something unguessable and throw it away, perms needed (suggest the only ones the account has) are:
```
api | rcon user | Can add VIP status to players
api | rcon user | Can message players
api | rcon user | Can view get_players endpoint (name, steam ID, VIP status and sessions) for all connected players
api | rcon user | Can view all players with VIP and their expiration timestamps
```

Make an api key for the account and add it to the .env at `RCON_API_KEY`

Change the other settings as wanted in the .env

## Build and start the bot
```
docker compose up --build -d
```

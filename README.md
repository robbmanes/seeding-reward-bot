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

## Development
This section details how to set up a development environment for `seeding-reward-bot`.

### Install Poetry
Building and Development is done with [poetry](https://python-poetry.org/docs/).  Ensure you have install poetry on your local system prior to beginning development:
```shell
$ poetry --version
Poetry version 1.1.12
```

Once `poetry` is installed, ensure you use a virtual environment:
```shell
$ poetry env use python3.10

$ poetry env info

Virtualenv
Python:         3.10.6
Implementation: CPython
Path:           /home/rmanes/.cache/pypoetry/virtualenvs/seeding-reward-bot-tut94FM2-py3.10
Valid:          True

System
Platform: linux
OS:       posix
Python:   /usr
```

To ensure your virtual environment is ready to run the project, make sure to install dependencies:
```shell
$ poetry install
```

### Adding Dependencies
The `poetry` command is capable of adding dependancies like so:
```shell
$ poetry add discord.py
```

The package will be automatically added to the virtual environment as well as the `pyproject.toml`:
```shell
[tool.poetry.dependencies]
python = "^3.10"
"discord.py" = "^2.1.1"
```

### Database Configuration
Currently `sqlite` and `postgres` are the only supported database types.

Only *one* type of database can be configured at a time.  If both are present in configuration, the bot should fail.

#### SQLite configuration
This configuration is very easy and requires little to no configuration.  Simply add the following to your `config.toml` (which is in the default `toml` file already):
```toml
[database.sqlite]
db_file = "seedbot.db"
```

This will create an SQLite database file at the root of the `seeding-reward-bot` project.

### PostgeSQL configuration.
Postgres requires the following configuration defined in the `config.toml` to function:
```toml
[database.postgres]
db_user = "myuser"
db_password = "mypassword"
db_url = "localhost"
db_port = 5432
db_name = "mydb"
```

The above example will equate to a connection string of `postgres://myuser:mypassword/localhost:5432/mydb` to connect to an existing PostgreSQL instance.

### Running seeding-reward-bot
Assuming you have the proper virtual environment configured and currently active, use `poetry` to run `seedbot` like so:
```shell
$ poetry run seedbot
```

# GlowBot
Discord Bot for [Glow's Battlegrounds Community](https://discord.gg/glows).

## Development
This section details how to set up a development environment for Glowbot.

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
Path:           /home/rmanes/.cache/pypoetry/virtualenvs/glowbot1-tut94FM2-py3.10
Valid:          True

System
Platform: linux
OS:       posix
Python:   /usr
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
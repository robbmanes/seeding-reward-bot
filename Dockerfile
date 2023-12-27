FROM docker.io/python:3.11.7-bullseye
RUN useradd glowbot -m && \
    git clone https://github.com/glows-battlegrounds/GlowBot.git /home/glowbot/GlowBot
USER glowbot
WORKDIR /home/glowbot/GlowBot
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    /home/glowbot/.local/bin/poetry install
VOLUME /home/glowbot/config.toml
CMD ["/home/glowbot/.local/bin/poetry", "run", "glowbot-discord"]

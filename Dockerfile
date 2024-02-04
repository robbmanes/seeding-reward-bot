FROM docker.io/python:3.11.7-bullseye
RUN useradd seedbot -m && \
    git clone https://github.com/robbmanes/seeding-reward-bot.git /home/seedbot/seedbot
USER seedbot
WORKDIR /home/seedbot/seedbot
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    /home/seedbot/.local/bin/poetry install
VOLUME /home/seedbot/config.toml
CMD ["/home/seedbot/.local/bin/poetry", "run", "seedbot"]
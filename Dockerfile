FROM docker.io/python:3.11.7-bullseye
RUN useradd seedbot -m && \
    mkdir -p /home/seedbot/seeding_reward_bot
ADD . / /home/seedbot/seeding_reward_bot/
USER seedbot
WORKDIR /home/seedbot/seeding_reward_bot
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    /home/seedbot/.local/bin/poetry install
VOLUME /home/seedbot/config.toml
CMD ["/home/seedbot/.local/bin/poetry", "run", "seedbot"]
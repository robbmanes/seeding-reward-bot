FROM python:3.13
RUN useradd seedbot -m && \
    mkdir -p /home/seedbot/seeding_reward_bot
USER seedbot
WORKDIR /home/seedbot/seeding_reward_bot
RUN curl -sSL https://install.python-poetry.org | python3 -
COPY poetry.lock pyproject.toml .
COPY seeding_reward_bot ./seeding_reward_bot
RUN /home/seedbot/.local/bin/poetry install --only main
CMD ["/home/seedbot/.local/bin/poetry", "run", "seedbot"]

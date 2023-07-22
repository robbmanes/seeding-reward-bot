FROM registry.fedoraproject.org/fedora:latest
RUN useradd glowbot && \
    dnf install poetry git -y && \
    git clone https://github.com/glows-battlegrounds/GlowBot.git /home/glowbot/GlowBot
USER glowbot
WORKDIR /home/glowbot/GlowBot
RUN poetry install
VOLUME /home/glowbot/config.toml
CMD ["/usr/bin/poetry", "run", "glowbot-discord"]
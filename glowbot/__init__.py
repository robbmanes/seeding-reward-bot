from glowbot.bot import Bot
import sys

_version__ = '0.1.0'

def main():
    bot = Bot()
    bot.run(bot.config['bot']['token'])

if __name__ == '__main__':
    sys.exit(main())
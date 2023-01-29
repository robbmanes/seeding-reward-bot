from setuptools import setup

VERSION=0.1

setup(
    name='glowbot',
    version=VERSION,
    description='Glow\'s Battlegrounds Community Discord Bot',
    author='Robb Manes',
    author_email='robbmanes@protonmail.com',
    url='https://github.com/robbmanes/glowbot',
    entry_points={
        'console_scripts': [
            'glowbot = glowbot:main',
        ]
    },
    packages=['glowbot'],
    install_requires=[
        'discord.py',
    ],
    package_data = {
        'glowbot': ['*'],
    }
)
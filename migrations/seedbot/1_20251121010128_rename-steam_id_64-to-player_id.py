from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "hll_player" RENAME COLUMN "steam_id_64" TO "player_id";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "hll_player" RENAME COLUMN "player_id" TO "steam_id_64";"""


MODELS_STATE = (
    "eJztl21P2zAQgP+KlS9jEkPQlZdN26SWdtCpLwjChkAochO3ierYIXYGFeK/z+ckzUvTjg"
    "IqTNqXqrk7n+8eX+6ce0MQ4gy53GqQ0LNd4zO6Nxj2ifpTVm0iAwdBTgESiYdUG+PMaChk"
    "iG2ppCNMBVEihwg79ALpcaakLKIUhNxWhh4bZ6KIeTcRsSQfE+mSUCmurpXYYw65IyJ9DC"
    "bWyCPUKQTrObC3lltyGmhZh8nv2hB2G1o2p5HPMuNgKl3OZtYe0xmNCSMhlgTcyzCC8CG6"
    "JM80ozjSzCQOMbfGISMcUZlL95EMbM6An4pG6ATHsMuH2k59v37wca9+oEx0JDPJ/kOcXp"
    "Z7vFAT6JvGg9ZjiWMLjTHj9puEAkKag3fo4rCaXm5JCaEKvIwwBbaMYSrIIGaF80IUfXxn"
    "UcLGEkq8tru7hNnPxunhceN0Q1m9h2y4Kua4xvuJqhbrAGwGEt6NFSAm5v8mwJ3t7UcAVF"
    "YLAWpdEaDaUZL4HSxC/HE26FdDzC0pgTxnKsErx7PlJqKekNdvE+sSipA1BO0LcUPz8DZ6"
    "jYsy18PuoKkpcCHHofaiHTQVY2iZo0nu5QfBENuTWxw61pyG1/gi23mVX/PLEszwWLOCjC"
    "G/dIwcd7vWCcVT3dfnp0xOvXzSuJRaQWb4t2lj9LhDKApJoLioYlHHgTCKHaAvX78hxxM2"
    "Dx1lQTGsEa4XbBml43u6l/8zbe0zLT4WqwqfSe4W8CsseuW2bJxJgv29esdBIx4iVTcoq/"
    "hndRWzfWEu7yr+NNF0B/2j1LzcaoqdO0GnH1cnni57EvOkMl8Aedx73gkkJA+Jg9Kw3h7u"
    "pNWsWN/FVa8Mu5V0y05LF/hbLm4YQSoeS3o+sYaYYmZXVbnStgiVuBr+IielY1AdjYDJFv"
    "w44G69bafh84hJxEcoYiJQYw4lgSOXR6F49gE1O0fQvYvMz3vNtrosfirfByWXmFp5citj"
    "r3bxxqCbECTCM/QQRnqzcLHqR/mDWO8RUCykxmfZLrEn8/xbCbtq/BXLF7FP/6wXfVcFGP"
    "OGEQuRKua3wJwQhpwojK95oECzFJ7Xojq99pnZ6J0U+lSrYbZBUyv0qFS6sVe67s+coF8d"
    "8xjBI7oc9NvlL4CZnXlpQEw4ktxi/NbCTp5SKk5Fr/vF8PAHUBz9Wg=="
)

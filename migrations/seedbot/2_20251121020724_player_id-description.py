from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        COMMENT ON COLUMN "hll_player"."player_id" IS 'Player ID for the player';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        COMMENT ON COLUMN "hll_player"."player_id" IS 'Steam64Id for the player';"""


MODELS_STATE = (
    "eJztl21P2zAQgP+KlS9jEkPQ8bZpm9TSDjr1BUHYEAhFbuI2UR07xM6gQvz3+ZykeWnaUU"
    "Clk/alau7O57vHlzvnwRCEOAMut+ok9GzX+IweDIZ9ov6UVZvIwEGQU4BE4gHVxjgzGggZ"
    "Ylsq6RBTQZTIIcIOvUB6nCkpiygFIbeVocdGmShi3m1ELMlHRLokVIrrGyX2mEPuiUgfg7"
    "E19Ah1CsF6Duyt5ZacBFrWZvK7NoTdBpbNaeSzzDiYSJezqbXHdEYjwkiIJQH3MowgfIgu"
    "yTPNKI40M4lDzK1xyBBHVObSfSIDmzPgp6IROsER7PKhtrN7sHv4cX/3UJnoSKaSg8c4vS"
    "z3eKEm0DONR63HEscWGmPG7TcJBYQ0A+/IxWE1vdySEkIVeBlhCmwRw1SQQcwK55Uo+vje"
    "ooSNJJR4bW9vAbOf9bOjk/rZhrJ6D9lwVcxxjfcSVS3WAdgMJLwbS0BMzP9NgDvb208AqK"
    "zmAtS6IkC1oyTxO1iE+OO836uGmFtSAnnBVILXjmfLTUQ9IW/WE+sCipA1BO0LcUvz8Da6"
    "9csy16NOv6EpcCFHofaiHTQUY2iZw3Hu5QfBANvjOxw61oyG1/g821mVX/PLEszwSLOCjC"
    "G/dIycdDrWKcUT3ddnp0xOvXjSuJRaQWb4t2ljdLlDKApJoLioYlHHgTCKHaAvX78hxxM2"
    "Dx1lQTGsEa4XbBml43u+l/8zbeUzLT4WqwqfSe7n8CsseuO2bMQvAmo30ZCHSNUNyir+RV"
    "3FbF2ai7uKP0k0nX7vODUvt5pi507Q6cfliafLnsU8qcxXQ/5OICF5SByUhrV+uJNWs2R9"
    "F1e9Mexm0i2TAl/n4oYRpOKxpOcTa4ApZnZVlSttk1CJq+HPc1I6BtXRCJhswY8D7lbbdu"
    "o+j5hEfIgiJgI15lASOHJ5FIoXH1CjfQzdu8j8ottoqcvip/J9UHKJqZUntzT2ahdrBt2E"
    "IBGeoocw0puFi1U/yh/Eao+AYiE1Pst2iT2e5d9M2FXjr1g+j336Z7XoOyrAmDeMWIhUMb"
    "8D5oQw5ERhfM0DBZqm8LIW1e62zs1697TQp5p1swWaWqFHpdKN/dJ1f+oE/WqbJwge0VW/"
    "1yp/AUztzCsDYsKR5BbjdxZ28pRScSp62y+Gxz+hLP1j"
)

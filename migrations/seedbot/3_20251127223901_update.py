from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "hll_player" ALTER COLUMN "discord_id" TYPE BIGINT USING "discord_id"::BIGINT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "hll_player" ALTER COLUMN "discord_id" TYPE TEXT USING "discord_id"::TEXT;"""


MODELS_STATE = (
    "eJztl21P2zAQgP+KlS9jEkMQXlqmbVJLO+jUFgRhQyAUuYnbRDh2iJ0BQvz3+ZykeWlaXg"
    "dM2pequTtf7h6f75xbQxDijrhcaZHIdzzjM7o1GA6I+lNVLSMDh2FBARKJR1Qb49xoJGSE"
    "HamkY0wFUSKXCCfyQ+lzpqQsphSE3FGGPpvkopj5lzGxJZ8Q6ZFIKc7OldhnLrkmInsML+"
    "yxT6hbCtZ34d1absubUMt6TH7XhvC2ke1wGgcsNw5vpMfZ1NpnOqMJYSTCkoB7GcUQPkSX"
    "5plllESamyQhFta4ZIxjKgvpPpCBwxnwU9EIneAE3vLJXNtobDTXtzaaykRHMpU07pL08t"
    "yThZrA0DLutB5LnFhojDm33yQSENIMvB0PR/X0CksqCFXgVYQZsEUMM0EOMS+cF6IY4Gub"
    "EjaRUOLm5uYCZj9bhzt7rcMlZfURsuGqmJMaH6YqM9EB2BwknI1HQEzN/02Aa6urDwCorO"
    "YC1LoyQPVGSZIzWIb442h/WA+xsKQC8pipBM9c35HLiPpCnr9PrAsoQtYQdCDEJS3CWxq0"
    "Tqpcd/r7bU2BCzmJtBftoK0YQ8scXxQOPwhG2Lm4wpFrz2i4yefZzqoCM6hKMMMTzQoyhv"
    "yyMbLX79sHFN/ovj47ZQrqxZPGo9QOc8P7po0x4C6hKCKh4qKKRW0HwihxgL58/YZcXzg8"
    "cpUFxbBGeH64YlS27+le/s+0V59pybbYdfgscj2HX2nRG7dlIzkIqNdBYx4hVTcor/hndR"
    "Wre2It7irBTarp7w93M/Nqqyl37hSdfnw88WzZk5inlfliyD8IJCSPiIuysN4f7rTV1NZ3"
    "25/M7RDldfd3ir+Ku5P2y7TEH1PeafvYNs319Ya5ur7V3NxoNDabq9M+Mqta1FDavV3oKS"
    "XuWZMpzykVlS39gNgjTDFz6qpdaTuESly/BfOcVDZDdTYCJivw44K7120/rYDHTCI+RjET"
    "oRp3KA0ceTyOxLOPRR3x4fGg3VWXxu3qvVByialdJPdo7PUu3hl0C4JEeIoewshuGB5Wfa"
    "m4Ea+7BRQLqfHZjkeci1n+nZRdPf6a5fPYZ39eF31fBZjwhlELkSrmV8CcEIbcOEque6BA"
    "0xSeNxh6g+6R1RoclKZDp2V1QWOWJkMmXdqqXPunTtCvnrWH4BGd7g+71S+BqZ11akBMOJ"
    "bcZvzKxm6RUibORG/75XD3B5XR/EI="
)

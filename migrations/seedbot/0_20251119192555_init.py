from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "hll_player" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "steam_id_64" TEXT NOT NULL,
    "player_name" TEXT,
    "discord_id" TEXT,
    "seeding_time_balance" BIGINT NOT NULL,
    "total_seeding_time" BIGINT NOT NULL,
    "last_seed_check" TIMESTAMPTZ NOT NULL
);
COMMENT ON COLUMN "hll_player"."steam_id_64" IS 'Steam64Id for the player';
COMMENT ON COLUMN "hll_player"."player_name" IS 'Player''s stored name';
COMMENT ON COLUMN "hll_player"."discord_id" IS 'Discord ID for player';
COMMENT ON COLUMN "hll_player"."seeding_time_balance" IS 'Amount of unspent seeding hours';
COMMENT ON COLUMN "hll_player"."total_seeding_time" IS 'Total amount of time player has spent seeding';
COMMENT ON COLUMN "hll_player"."last_seed_check" IS 'Last time the seeder was seen during a seed check';
COMMENT ON TABLE "hll_player" IS 'Model representing a player <=> discord relationship.';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "eJztl21P2zAQx7+KlTdjEkPQlYdN26SWdtCpLQjChkDIcmO3iXDsEDsDhPju8zlJk6YP40"
    "mFSXtTNXdn+38/X87OnaMYowOp1xosDjzf+YzuHEFCZv5UXavIIVFUcoBFkwG3waQIGigd"
    "E08b65BwxYyJMuXFQaQDKYxVJJyDUXomMBCjwpSI4CphWMsR0z6LjeP8wpgDQdkNU/ljdI"
    "mHAeN0QmxAYW1rx/o2sraO0N9tIKw2wJ7kSSiK4OhW+1KMowNhMxoxwWKiGUyv4wTkg7os"
    "zzyjVGkRkkosjaFsSBKuS+k+kIEnBfAzapRNcASrfKht1LfrOx+36jsmxCoZW7bv0/SK3N"
    "OBlkDfde6tn2iSRliMBbffLFYgaQrerk/i2fRKQyoIjfAqwhzYIoa5oYBYFM4LUQzJDeZM"
    "jDSUeG1zcwGzn42j3f3G0YqJeg/ZSFPMaY33M1ct9QHYAiS8G4+AmIX/mwA31tcfANBEzQ"
    "VofZMAzYqape/gJMQfxwf92RBLQyogT4RJ8JwGnl5FPFD64m1iXUARsgbRoVJXvAxvpdc4"
    "rXLd7R40LQWp9Ci2s9gJmoYxtMzhZenlB8OAeJfXJKZ4yiNrcl7stCushVULEWRkWUHGkF"
    "9+jOx3u/iQk1vb16dPmZJ78Unjc46jIvBvp43Tk5RxFLPIcDHFYrYDEZROgL58/YZooDwZ"
    "UxPBCYxRfhCtOZXte/os/8+0pZ9pSjMS4oDirfo0QJfdzCFYGfbKrdk5Bjlb9Q5FQxkjUz"
    "uoqPpndRa3feou7izhbebpHvT38vBqu5ns3qk2bB8fwbwy7EnMs+p8AeRp/3mnkNIyZhTl"
    "st4e7qzd4FktYj7tyVGvDLuVdcxOyxb4Wy5uOIaMHqyDkOEB4UR4s6rceFuMazKnvcyZpL"
    "INpqsxCFmDHwrTLbftNEKZCI3kECVCReaoQ5lw5MskVs/eoGZnDzr4JPOTXrNtLoyfqndC"
    "LTXhuEzu0dhnT/HGoLsgEpExepCR3y58YvpReSOWuwWcKG3xYc9n3uU0/1bGbjb+GcPnsc"
    "//LBd91whMecMRC0oN82tgzphANInTqx440DiF57WoTq997DZ6hxN9qtVw2+CpTfSo3Lqy"
    "VbnyjydBvzruPoJHdHbQb1e/AsZx7pkDmkiiJRbyGhNappSbc9PrfjXc/wFEHP4G"
)

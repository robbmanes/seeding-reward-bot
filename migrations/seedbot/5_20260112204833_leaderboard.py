from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "seeding_session" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "server" INT NOT NULL,
    "start_time" TIMESTAMPTZ NOT NULL,
    "end_time" TIMESTAMPTZ NOT NULL,
    "hll_player_id" INT NOT NULL REFERENCES "hll_player" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_seeding_ses_hll_pla_dca55d" UNIQUE ("hll_player_id", "server", "start_time")
);
CREATE INDEX IF NOT EXISTS "idx_seeding_ses_end_tim_3c34af" ON "seeding_session" ("end_time");
CREATE INDEX IF NOT EXISTS "idx_seeding_ses_hll_pla_081d7c" ON "seeding_session" ("hll_player_id");
COMMENT ON COLUMN "seeding_session"."server" IS 'Server session took place on';
COMMENT ON COLUMN "seeding_session"."start_time" IS 'Start time of seeding session';
COMMENT ON COLUMN "seeding_session"."end_time" IS 'End time of seeding session';
COMMENT ON TABLE "seeding_session" IS 'Model representing a one to many relation of a player''s seeding sessions.';
        ALTER TABLE "hll_player" ADD "hidden" BOOL NOT NULL DEFAULT False;
        COMMENT ON COLUMN "hll_player"."hidden" IS 'Player is hidden from stats';
        CREATE INDEX IF NOT EXISTS "idx_hll_player_hidden_218587" ON "hll_player" ("hidden") WHERE hidden = true;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_hll_player_hidden_218587";
        ALTER TABLE "hll_player" DROP COLUMN "hidden";
        DROP TABLE IF EXISTS "seeding_session";"""


MODELS_STATE = (
    "eJztmetvGjkQwP8Va780J/WilDx7up7EKw0tgSrQa9UoWpldAysWm9reJijK/35jr/e9EC"
    "AJx+nyJWLHY+/45/E8NveWIMQdMLlfJdxzxtYf6N6ieErgR37oLbLwbJYaUBKJB75WxonS"
    "QEiOHQnSIfYFAZFLhMO9mfQYBSkNfF8JmQOKHh0looB6PwNiSzYickw4DFzfgNijLrkjIn"
    "qcTeyhR3w3Y6znqndruS3nMy1rUXmuFdXbBrbD/GBKE+XZXI4ZjbU9qnc0IpRwLIlaXvJA"
    "ma+sM/uMdhRamqiEJqbmuGSIA1+mtrsiA4dRxQ+sEXqDI/WW3yvvjk6Pzg5Pjs5ARVsSS0"
    "4fwu0lew8nagKdvvWgx7HEoYbGmHD7RbhQJhXg1ceYl9NLTckhBMPzCCNgyxhGggRi4jjP"
    "RHGK72yf0JFULl45Pl7C7O/qVf2ierUHWr+p3TBw5tDHO2aoEo4psAlIdTfWgGjU/5sA3x"
    "0crAAQtBYC1GNZgPBGScI7mIX4qdftlENMTcmB/Ephg9eu58i3yPeEvNlNrEsoql0ro6dC"
    "/PTT8PYuq9/zXOvtbk1TYEKOuF5FL1ADxipkDiepy68EA+xMbjF37cIIq7BFusWhaWWal2"
    "CKR5qV2rHaX5RGLtpt+4uP5zquF7NManh5phn7vj1LFB/LNtYlc4mPOJkBF3AWOA6EUbgA"
    "+vPDX8j1hMO4Cxo+VnPE2JvtW7nj23yVx3PavZUgtMae6xJqKRVyp16mQm1M10AzzhQ5u6"
    "WVAYN6QN8umldNFK6DPuh8ZD285s1nzpvh0dtl+PpwFuX8MpP+5dBvhZcNtRpoyDgC30TJ"
    "rXpS5Oo3v/eXR67p3Iy0u52PkXo+nGWzg0GnH9cnHk3biLnxzGdD/kYgIRknLorM2j3cJp"
    "yV+nfNGy2MENl5j0eKFXBvGCmshonIxsHXcW4TPN5XKoeHp5WDw5Oz46PT0+OzgziKFIeW"
    "hZNa66OKKBnqUYjJZkKwypbelNgD7GPqlPk6jDaIL3H5ASxaJHcUENeIUtlXf1y13HaDT3"
    "XKAioRG6KAihkkVGQMR2MWcPHkS1FGvPP1staEsvR9vvKUTGLfTpNbG3v5EjsGva+MRDhG"
    "r8yIapgxhqiUPojtHoGPhdT4bGdMnEmRf8OwK8dfMn0R++jHdtG3wcCQt0q0ylJgfquYE6"
    "jS3ICHBaUaQPEWnpYWWpfNXr96+SWTGxrVflONVDJ5IZLuneQai3gR9K3Vv0DqEf3odpr5"
    "XiPW6/+wlE04kMym7NbGbppSJI5EGRcwlW8x3TDmE0zLDz6ZlDvvAcx6qSNe0GiYgsoTUf"
    "E95GwKqR7LZ4hn3W47c5C11oKrpU8QlDyZSjNr9IDFfCSiJqR4NGaF889Xpu0pK7JMg9cz"
    "y/XC5Xa6IU+kpt54eNHWOI+mrD8uwbekSc6d3RM6ZUYhZjEExs/j5lYlj6j7fSPi1B05yo"
    "rd86Yrl3TU17mvAoLwX+aXxFyGCfnm9Vvyy/bECfUV2SUTNuoUnjE/97QlkZ+BW7KJ8kKH"
    "oPDybAtuCmbiuGsWQ9mZu1UH9ZRtYSEENz13vf9/NQ+h7kZHnJ63nQNeseluUvf1dOOKNs"
    "5Jpd9RFobFwryXio47mF8KlWoZziLLc8aJN6KfyVwjbYFdC758lP+/YedYLipEQczxbVy0"
    "FH0Ftgq1Fgmr/3q1V682muH3/239z+fhH5Fnce0="
)

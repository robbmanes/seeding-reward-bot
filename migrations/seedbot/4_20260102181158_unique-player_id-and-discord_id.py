from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "hll_player" ADD UNIQUE ("player_id");
        ALTER TABLE "hll_player" ADD UNIQUE ("discord_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "hll_player" DROP CONSTRAINT IF EXISTS "hll_player_discord_id_key";
        ALTER TABLE "hll_player" DROP CONSTRAINT IF EXISTS "hll_player_player_id_key";"""


MODELS_STATE = (
    "eJztl21P2zAQx7+KlTdjEkMlPBSmbVJLu9GpDwjChkAochO3iXDsEDsDhPju8zlJ89C0PA"
    "qYtDdVc3d27n6+/C+5NQQh7pjLtRaJfMczPqNbg+GAqD9V1yoycBgWHGCReEx1MM6DxkJG"
    "2JHKOsFUEGVyiXAiP5Q+Z8rKYkrByB0V6LNpboqZfxkTW/IpkR6JlOPsXJl95pJrIrLL8M"
    "Ke+IS6pWR9F+6t7ba8CbWtx+R3HQh3G9sOp3HA8uDwRnqczaJ9piuaEkYiLAlsL6MY0ofs"
    "0jqzipJM85AkxcIal0xwTGWh3AcycDgDfioboQucwl0+meubzc2dje3NHRWiM5lZmndJeX"
    "ntyUJNYGgZd9qPJU4iNMac2x8SCUhpDt6eh6N6eoUlFYQq8SrCDNgyhpkhh5g3zgtRDPC1"
    "TQmbSmhxc2trCbNfrcO9/dbhior6CNVw1cxJjw9Tl5n4AGwOEp6NR0BMw/9NgOuNxgMAqq"
    "iFALWvDFDdUZLkGSxD/Hk0GtZDLCypgDxmqsAz13fkKqK+kOfvE+sSilA1JB0IcUmL8FYG"
    "rZMq173+qK0pcCGnkd5Fb9BWjEEyJxeFhx8MY+xcXOHItec83OSLYuddgRlULZjhqWYFFU"
    "N92RjZ7/ftA4pvtK7PT5mCe/mk8Si1wzzwvmljDLhLKIpIqLioZlHHgTBKNkBfvn5Dri8c"
    "HrkqgmJYIzw/XDMqx/f0Xf7PtFefacmx2HX4LHK9gF9p0RvLspE8CKjXQRMeIdU3KO/4Z6"
    "mK1T2xlqtKcJN6+qPhjyy8KjVl5U7R6cvHE8+WPYl52pkvhvyDQELyiLgoS+v94U6lpra/"
    "2/50oUKU192vFA/A/USlMDqpWqYN/pjmTsVj1zQ3NppmY2N7Z2uz2dzaacxUZN61TE7avR"
    "+gKCXqmcSUp5TKypZ+QOwxppg5db2uvB1CJa4/gEWbVI5C6RqBkDX4cWG71xWfVsBjJhGf"
    "oJiJUA07lCaOPB5H4tkPRR3x4fGg3VWvjLvVt0LJJaZ2kdyjsddv8c6gW5AkwjP0kEb2fu"
    "FhpUrFg3jdI6BYSI3PdjziXMzz76Ts6vHXLF/EPvvzuuj7KsGENwxayFQxvwLmhDDkxlHy"
    "sgcONCvheWOhN+geWa3BQWk2dFpWFzxmaS5k1pXtykv/bBP0u2ftI7hEp6Nht/odMIuzTg"
    "3ICceS24xf2dgtUsrMmeltvxvu/gIDu/us"
)

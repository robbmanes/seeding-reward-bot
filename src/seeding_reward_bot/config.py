from environs import Env, validate


class Configuration:
    def __init__(self):
        rcon_url_validater = validate.URL(schemes=("http", "https"), require_tld=False)

        env = Env(eager=False)
        env.read_env()

        self.log_level = env.log_level("LOG_LEVEL")
        self.error_message = env("ERROR_MESSAGE")
        self.maintainer_discord_ids = env.list(
            "MAINTAINER_DISCORD_IDS", [], subcast=int
        )
        self.discord_token = env("DISCORD_TOKEN")
        self.db_user = env("DB_USER")
        self.db_password = env("DB_PASSWORD")
        self.db_host = env("DB_HOST")
        self.db_port = env.int("DB_PORT")
        self.db_name = env("DB_NAME")
        self.rcon_url = env.dict(
            "RCON_URL",
            subcast_keys=str,
            subcast_values=int,
            validate=lambda items: all(rcon_url_validater(item) for item in items),
        )
        self.rcon_api_key = env("RCON_API_KEY")
        self.seeding_threshold = env.int(
            "SEEDING_THRESHOLD", validate=validate.Range(min=0, max=100)
        )
        self.seeder_vip_reward_hours = env.int(
            "SEEDER_VIP_REWARD_HOURS", validate=validate.Range(min=0)
        )
        self.seeder_reward_message = env("SEEDER_REWARD_MESSAGE")
        self.seeding_start_time_utc = env.time("SEEDING_START_TIME_UTC")
        self.seeding_end_time_utc = env.time("SEEDING_END_TIME_UTC")
        self.allow_messages_to_players = env.bool("ALLOW_MESSAGES_TO_PLAYERS")

        env.seal()


global_config = Configuration()

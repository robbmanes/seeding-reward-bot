import httpx
import asyncio
from datetime import datetime
from enum import StrEnum
from seeding_reward_bot.config import global_config
import logging

class Actions(StrEnum):
    """
    Predefined hll_rcon_tool actions as per:
    https://github.com/MarechJ/hll_rcon_tool/blob/25d5830a3203c76604246073061e8d37dc72bf9c/rcon/extended_commands.py#L33-L58
    """
    DISCONNECTED = "DISCONNECTED"
    CHAT_ALLIES = "CHAT[Allies]"
    CHAT_AXIS = "CHAT[Axis]"
    CHAT_ALLIES_UNIT = "CHAT[Allies][Unit]"
    KILL = "KILL"
    CONNECTED = "CONNECTED"
    CHAT_ALLIES_TEAM = "CHAT[Allies][Team]"
    CHAT_AXIS_TEAM = "CHAT[Axis][Team]"
    CHAT_AXIS_UNIT = "CHAT[Axis][Unit]"
    CHAT = "CHAT"
    VOTE_COMPLETED ="VOTE COMPLETED"
    VOTE_STARTED = "VOTE STARTED"
    VOTE = "VOTE"
    TEAMSWITCH = "TEAMSWITCH"
    TK_AUTO = "TK AUTO"
    TK_AUTO_KICKED = "TK AUTO KICKED"
    TK_AUTO_BANNED = "TK AUTO BANNED"
    ADMIN = "ADMIN"
    ADMIN_KICKED = "ADMIN KICKED"
    ADMIN_BANNED = "ADMIN BANNED"
    MATCH = "MATCH"
    MATCH_START = "MATCH START"
    MATCH_ENDED = "MATCH ENDED"
    MESSAGE = "MESSAGE"

class HLL_RCON_Client(object):
    """
    Represents connection to one or more https://github.com/MarechJ/hll_rcon_tool endpoints.

    While it can represent a single client, it can be used to span multiple endpoints
    so long as you want their data to match and sync.
    """

    global_timeout = httpx.Timeout(15.0, read=None)

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def for_single_rcon(fn):
        """
        Decorator to apply method to only ever work on a singe RCON server,
        like sending a player a message (since they can't be logged in to two
        HLL instances at once).

        This decorator handles auth to the RCON for the clients.
        """
        async def wrapper(self, rcon_server_url, *args):
            async with httpx.AsyncClient() as client:
                res = await self.handle_rcon_auth(rcon_server_url, client)
                self.logger.debug(f'Executing \"{fn.__name__}\" with RCON \"{rcon_server_url}\" as an endpoint...')
                res = await fn(self, rcon_server_url, client, *args)
                return res
        return wrapper

    def for_each_rcon(fn):
        """
        Decorator to apply method to all RCON servers in a list.
        Will iterate through all RCON servers in a list, meaning it calls it's wrapped
        function multiple times (once per server).

        This decorator additionally handles auth to the RCON's.

        Methods that call methods wrapped in this decorator should *always* expect a dict reply where the key of the
        dict is the RCON URL and the value is the return of the function.

        Ideally this method is adapted later to handle comparison of the values from different RCON's via a standard reply
        but for now the caller has to evaluate the returned dict themselves.
        """
        async def wrapper(self, *args):
            ret_vals = {}
            for rcon_server_url in global_config['hell_let_loose']['rcon_url']:
                async with httpx.AsyncClient() as client:
                    res = await self.handle_rcon_auth(rcon_server_url, client)
                    try:
                        self.logger.debug(f'Executing \"{fn.__name__}\" with RCON \"{rcon_server_url}\" as an endpoint...')
                        res = await fn(self, rcon_server_url, client, *args)
                        ret_vals[rcon_server_url] = res
                    except Exception as e:
                        raise
                    # We need to check if the return value is identical for each RCON.
                    # If it is not, error/alert to avoid deviant behavior.
                
            return ret_vals
        return wrapper

    async def handle_rcon_auth(self, rcon_server_url, client):
        """
        Takes a client and checks authentication to an endpoint.

        MUST be called within an active client coroutine (`async with client`, etc)
        """
        response = await client.get('%s/api/is_logged_in' % (rcon_server_url))
        r = response.json()
        if r['result']['authenticated'] == False:
            response = await client.post(
                '%s/api/login' % (rcon_server_url),
                json={
                    'username': global_config['hell_let_loose']['rcon_user'],
                    'password': global_config['hell_let_loose']['rcon_password'],
                },
                timeout=self.global_timeout,
            )
            r = response.json()
            if r['failed'] is False:
                self.logger.info(f'Successful RCON login to {rcon_server_url}')
            else:
                self.logger.error(f'Failed to log into {rcon_server_url}: \"{r}\"')

    @for_each_rcon
    async def grant_vip(self, rcon_server_url, client, name, steam_id_64, expiration):
        """
        Add a new VIP entry to the RCON instances or update an existing entry.

        Must supply the RCON server arguments:
        name -- user's name in RCON
        steam_id_64 -- user's `steam64id`
        expiration -- time VIP expires

        Returns True for success, False for failure.
        """
        response = await client.post(
            '%s/api/add_vip' % (rcon_server_url),
            json={
                'description': name,
                'player_id': str(steam_id_64),
                'expiration': expiration,
            },
            timeout=self.global_timeout,
        )
        result = response.json()
        if result['failed'] is False:
            self.logger.debug(f'Granted VIP to user \"{name}/{steam_id_64}\", expiration {expiration}')
            return True
        else:
            self.logger.error(f'Failed to update VIP user on \"{rcon_server_url}\": {result}')
            return False

    @for_each_rcon
    async def revoke_vip(self, rcon_server_url, client, name, steam_id_64):
        """Completely remove a VIP entry from the RCON instances."""
        response = await client.post(
            '%s/api/remove_vip' % (rcon_server_url),
            json={
                'player_id': steam_id_64,
            },
            timeout=self.global_timeout,
        )
        result = response.json()
        if result['result'] == 'SUCCESS':
            self.logger.debug(f'Revoked VIP for user {name}/{steam_id_64}')
            return True
        else:
            self.logger.error(f'Failed to remove VIP user on "\{rcon_server_url}\": {result}')
            return False
    
    @for_each_rcon
    async def get_vip(self, rcon_server_url, client, steam_id_64):
        """
        Queries the RCON server for all VIP's, and returns a single VIP object
        based on the input steam64id.
        """
        response = await client.get('%s/api/get_vip_ids' % (rcon_server_url), timeout=self.global_timeout)
        result = response.json()
        vip_list = result['result']
        for vip in vip_list:
            # Work around for https://github.com/MarechJ/hll_rcon_tool/issues/248
            # We need to verify numerical input
            try:
                if vip['player_id'] == steam_id_64:
                    return vip
            except ValueError as e:
                self.logger.error(f'Improper steam ID for VIP entry from RCON: {e}')
                self.logger.error(f'Failed entry: {vip}')
                continue
        return None
    
    @for_each_rcon
    async def get_recent_logs(self, rcon_server_url, client, since_min_ago):
        """
        Queries the RCON server for all logs and returns them in a list.

        Must supply an int in minutes to limit the query.
        """
        response = await client.get(
            '%s/api/get_recent_logs' % (rcon_server_url),
            json={
                'since_min_ago': since_min_ago
            },
            timeout=self.global_timeout,
        )
        result = response.json()

        logs = result['result']['logs']

        # If there's nothing, return nothing
        if len(logs) == 0:
            return None

        return logs
    
    @for_each_rcon
    async def get_chat_logs(self, rcon_server_url, client, since_min_ago):
        """
        Queries the RCON server for all logs but returns only chat logs.

        This is done to avoid filtering logic occuring on the RCON side.
        """
        actions = [
            Actions.CHAT,
            Actions.CHAT_ALLIES,
            Actions.CHAT_AXIS,
            Actions.CHAT_ALLIES_UNIT,
            Actions.CHAT_AXIS_UNIT,
            Actions.CHAT_ALLIES_TEAM,
            Actions.CHAT_AXIS_TEAM,
        ]
        response = await client.get(
            '%s/api/get_recent_logs' % (rcon_server_url),
            json={
                'since_min_ago': since_min_ago
            },
            timeout=self.global_timeout,
        )
        logs = response.json()

        chat_logs = []
        for log in logs['result']['logs']:
            if log['action'] in actions:
                chat_logs.append(log)
        
        # If there's nothing, return nothing
        if len(chat_logs) == 0:
            return None

        return chat_logs
    
    @for_each_rcon
    async def get_player_logs(self, rcon_server_url, client, steam_id_64):
        """
        Queries the RCON server for the last logs for a user by their steam_id_64.
        Returns raw logs in a list.
        """
        response = await client.get(
            '%s/api/get_structured_logs' % (rcon_server_url),
            json={
                'since_min_ago': global_config['hell_let_loose']['max_log_parse_mins']
            },
            timeout=self.global_timeout,
        )
        # We have to assume the player name can change, so ensure we only search for steamID's
        unfiltered_logs = response.json()
        player_logs = []
        for log in unfiltered_logs['result']['logs']:
            if log['player_id_1'] == steam_id_64 or log['player_id_2'] == steam_id_64:
                player_logs.append(log)
        
        return player_logs

    @for_each_rcon
    async def get_player_list(self, rcon_server_url, client):
        """
        Queries the RCON server(s) for a list of players.
        """
        response = await client.get('%s/api/get_players' % (rcon_server_url), timeout=self.global_timeout)
        player_list = response.json()
        return player_list['result']
    
    def parse_log_events(self, logs, action):
        """
        Takes a list of logs from get_player_logs and returns a list of logs of type ACTION.
        Actions can be any supported RCON type from game logs:
        https://github.com/MarechJ/hll_rcon_tool/blob/5cba530ceadd226a80fc345e3607eff7ce4011e1/rcon/game_logs.py#L29-L55
        """
        try:
            parsed_logs = []
            for log in logs:
                if log['action'] == action:
                    parsed_logs.append(log)
        except ValueError as e:
            self.logger.error(f'Failed to parse log events as action is undefined: {e}')
        
        return parsed_logs

    @for_single_rcon
    async def send_player_message(self, rcon_server_url, client, steam_id_64, message):
        """
        Send a player a message via the RCON.
        
        Returns True for success, False for failure
        """

        if global_config['hell_let_loose']['allow_messages_to_players'] is True:
            # early exit if config says don't send messages to players...
            # useful when (sneakily) testing!
            return True

        response = await client.post(
            '%s/api/message_player' % (rcon_server_url),
            json={
                'player_id': steam_id_64,
                'message': message,
            },
            timeout=self.global_timeout,
        )
        result = response.json()
        if result['result'] == 'SUCCESS':
            return True
        
        self.logger.error(f'Failed sending message to user {steam_id_64}: {result}')
        return False

def rcon_time_str_to_datetime(date_string):
    """Convert datetime strings from the RCON to datetime objects"""
    try:
        # Newer RCON entries do not have the .f field
        return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S%z")
    except ValueError as e:
        return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%f%z")

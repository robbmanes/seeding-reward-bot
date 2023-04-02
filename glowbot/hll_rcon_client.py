import aiohttp
import asyncio
from datetime import datetime
from enum import StrEnum
from glowbot.config import global_config
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

    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def connect(self):
        """
        Creates connections to RCON endpoints and stores them in self.sessions.
        Must be called before any other methods are called.
        """
        # Get our current event loop
        event_loop = asyncio.get_event_loop()

        # Open an aiohttp session per RCON endpoint
        self.sessions = {}
        for rcon_server_url in global_config['hell_let_loose']['rcon_url']:
            self.sessions[rcon_server_url] = aiohttp.ClientSession()

    def for_single_rcon(fn):
        """
        Decorator to apply method to only ever work on a singe RCON server,
        like sending a player a message (since they can't be logged in to two
        HLL instances at once).

        This decorator handles auth to the RCON for the session.
        """
        async def wrapper(self, rcon_server_url, session, *args):
            res = await self.handle_rcon_auth(rcon_server_url, session)
            self.logger.debug(f'Executing \"{fn.__name__}\" with RCON \"{rcon_server_url}\" as an endpoint...')
            res = await fn(self, rcon_server_url, session, *args)
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
            for rcon_server_url, session in self.sessions.items():
                res = await self.handle_rcon_auth(rcon_server_url, session)
                try:
                    self.logger.debug(f'Executing \"{fn.__name__}\" with RCON \"{rcon_server_url}\" as an endpoint...')
                    res = await fn(self, rcon_server_url, session, *args)
                    ret_vals[rcon_server_url] = res
                except Exception as e:
                    raise
                # We need to check if the return value is identical for each RCON.
                # If it is not, error/alert to avoid deviant behavior.
                
            return ret_vals
        return wrapper

    async def handle_rcon_auth(self, rcon_server_url, session):
        """
        Takes a session and checks authentication to an endpoint.
        """
        async with session.get(
            '%s/api/is_logged_in' % (rcon_server_url)
        ) as response:
            r = await response.json()
            if r['result']['authenticated'] == False:
                async with session.post(
                    '%s/api/login' % (rcon_server_url),
                    json={
                        'username': global_config['hell_let_loose']['rcon_user'],
                        'password': global_config['hell_let_loose']['rcon_password'],
                    },
                ) as response:
                    r = await response.json()
                    if r['failed'] is False:
                        self.logger.info(f'Successful RCON login to {rcon_server_url}')
                    else:
                        self.logger.error(f'Failed to log into {rcon_server_url}: \"{r}\"')

    @for_each_rcon
    async def grant_vip(self, rcon_server_url, session, name, steam_id_64, expiration):
        """
        Add a new VIP entry to the RCON instances or update an existing entry.

        Must supply the RCON server arguments:
        name -- user's name in RCON
        steam_id_64 -- user's `steam64id`
        expiration -- time VIP expires

        Returns True for success, False for failure.
        """
        async with session.post(
            '%s/api/do_add_vip' % (rcon_server_url),
            json={
                'name': name,
                'steam_id_64': str(steam_id_64),
                'expiration': expiration,
            }
        ) as response:
            result = await response.json()
            if result['result'] == 'SUCCESS':
                self.logger.debug(f'Granted VIP to user \"{name}/{steam_id_64}\", expiration {expiration}')
                return True
            else:
                self.logger.error(f'Failed to update VIP user on \"{rcon_server_url}\": {result}')
                return False

    @for_each_rcon
    async def revoke_vip(self, rcon_server_url, session, name, steam_id_64):
        """Completely remove a VIP entry from the RCON instances."""
        async with session.post(
            '%s/api/do_remove_vip' % (rcon_server_url),
            json={
                'name': name,
                'steam_id_64': int(steam_id_64),
            }
        ) as response:
            result = await response.json()
            if result['result'] == 'SUCCESS':
                self.logger.debug(f'Revoked VIP for user {name}/{steam_id_64}')
                return True
            else:
                self.logger.error(f'Failed to remove VIP user on "\{rcon_server_url}\": {result}')
                return False
    
    @for_each_rcon
    async def get_vip(self, rcon_server_url, session, steam_id_64):
        """
        Queries the RCON server for all VIP's, and returns a single VIP object
        based on the input steam64id.
        """
        async with session.get(
            '%s/api/get_vip_ids' % (rcon_server_url)
        ) as response:
            result = await response.json()
            vip_list = result['result']
            for vip in vip_list:
                if int(vip['steam_id_64']) == steam_id_64:
                    return vip
        return None
    
    @for_each_rcon
    async def get_recent_logs(self, rcon_server_url, session, since_min_ago):
        """
        Queries the RCON server for all logs and returns them in a list.

        Must supply an int in minutes to limit the query.
        """
        async with session.get(
            '%s/api/get_recent_logs' % (rcon_server_url),
            json={
                'since_min_ago': since_min_ago
            }
        ) as response:
            return response.json()['result']['logs']
    
    @for_each_rcon
    async def get_chat_logs(self, since_min_ago):
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

        async with session.get(
            '%s/api/get_recent_logs' % (rcon_server_url),
            json={
                'since_min_ago': since_min_ago
            }
        ) as response:
            logs = response.json()['result']['logs']

            chat_logs = []
            for log in logs:
                if log['action'] in actions:
                    chat_logs.append(log)
            
            return chat_logs
    
    @for_each_rcon
    async def get_player_logs(self, rcon_server_url, session, steam_id_64):
        """
        Queries the RCON server for the last logs for a user by their steam_id_64.
        Returns raw logs in a list.
        """
        async with session.get(
            '%s/api/get_structured_logs' % (rcon_server_url),
            json={
                'since_min_ago': global_config['hell_let_loose']['max_log_parse_mins']
            }
        ) as response:
            # We have to assume the player name can change, so ensure we only search for steamID's
            unfiltered_logs = await response.json()
            player_logs = []
            for log in unfiltered_logs['result']['logs']:
                if log['steam_id_64_1'] == steam_id_64 or log['steam_id_64_2'] == steam_id_64:
                    player_logs.append(log)
            
            return player_logs

    @for_each_rcon
    async def get_player_list(self, rcon_server_url, session):
        """
        Queries the RCON server(s) for a list of players.
        """
        async with session.get(
            '%s/api/get_players' % (rcon_server_url)
        ) as response:
            player_list = await response.json()
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
    async def send_player_message(self, rcon_server_url, session, steam_id_64, message):
        """
        Send a player a message via the RCON.
        
        Returns True for success, False for failure
        """
        async with session.get(
            '%s/api/do_message_player' % (rcon_server_url),
            json={
                'steam_id_64': steam_id_64,
                'message': message,
            }
        ) as response:
            result = await response.json()
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
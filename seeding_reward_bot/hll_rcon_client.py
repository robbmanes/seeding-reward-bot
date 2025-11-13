import asyncio
import logging
from datetime import datetime
from enum import StrEnum

import httpx
import stamina

from seeding_reward_bot.config import global_config


class HLL_RCON_Error(Exception):
    pass


class HLL_RCON_Client(object):
    """
    Represents connection to one or more https://github.com/MarechJ/hll_rcon_tool endpoints.

    While it can represent a single client, it can be used to span multiple endpoints
    so long as you want their data to match and sync.
    """

    global_timeout = httpx.Timeout(15.0, read=None)

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client = httpx.AsyncClient()

    def for_single_rcon(fn):
        """
        Decorator to apply method to only ever work on a singe RCON server,
        like sending a player a message (since they can't be logged in to two
        HLL instances at once).
        """

        async def wrapper(self, rcon_server_url, *args):
            self.logger.debug(
                f'Executing "{fn.__name__}" with RCON "{rcon_server_url}" as an endpoint...'
            )
            res = await fn(self, rcon_server_url, *args)
            return res

        return wrapper

    def for_each_rcon(fn):
        """
        Decorator to apply method to all RCON servers in a list.
        Will iterate through all RCON servers in a list, meaning it calls it's wrapped
        function multiple times (once per server).

        Methods that call methods wrapped in this decorator should *always* expect a dict reply where the key of the
        dict is the RCON URL and the value is the return of the function.

        Ideally this method is adapted later to handle comparison of the values from different RCON's via a standard reply
        but for now the caller has to evaluate the returned dict themselves.
        """

        async def wrapper(self, *args):
            ret_vals = {}
            for rcon_server_url in global_config["hell_let_loose"]["rcon_url"]:
                try:
                    self.logger.debug(
                        f'Executing "{fn.__name__}" with RCON "{rcon_server_url}" as an endpoint...'
                    )
                    res = await fn(self, rcon_server_url, *args)
                    ret_vals[rcon_server_url] = res
                except Exception as e:
                    raise
                # We need to check if the return value is identical for each RCON.
                # If it is not, error/alert to avoid deviant behavior.

            return ret_vals

        return wrapper

    @stamina.retry(on=httpx.HTTPError)
    async def request_rcon(self, method, server, query, json=None):
        headers = {
            "Authorization": f"bearer {global_config['hell_let_loose']['rcon_api_key']}",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
        }
        response = await self.client.request(
            method,
            f"{server}/api/{query}",
            headers=headers,
            json=json,
            timeout=httpx.Timeout(15.0, read=None),
        )
        response.raise_for_status()
        r = response.json()
        if r["failed"]:
            raise HLL_RCON_Error(f'RCON query failed!: "{r}"')
        return r["result"]

    async def get_rcon(self, server, query):
        return await self.request_rcon("GET", server, query)

    async def post_rcon(self, server, query, json):
        return await self.request_rcon("POST", server, query, json)

    @for_each_rcon
    async def grant_vip(self, rcon_server_url, name, steam_id_64, expiration):
        """
        Add a new VIP entry to the RCON instances or update an existing entry.

        Must supply the RCON server arguments:
        name -- user's name in RCON
        steam_id_64 -- user's `steam64id`
        expiration -- time VIP expires

        Returns True for success, False for failure.
        """
        try:
            result = await self.post_rcon(
                rcon_server_url,
                "add_vip",
                {
                    "description": name,
                    "player_id": str(steam_id_64),
                    "expiration": expiration.isoformat(timespec="seconds"),
                },
            )
        except:
            self.logger.exception(f'Failed to update VIP user on "{rcon_server_url}"')
            return False
        self.logger.debug(
            f'Granted VIP to user "{name}/{steam_id_64}", expiration {expiration}'
        )
        return True

    # @for_each_rcon
    # async def revoke_vip(self, rcon_server_url, client, name, steam_id_64):
    #    """Completely remove a VIP entry from the RCON instances."""
    #    response = await client.post(
    #        '%s/api/remove_vip' % (rcon_server_url),
    #        json={
    #            'player_id': steam_id_64,
    #        },
    #        timeout=self.global_timeout,
    #    )
    #    result = response.json()
    #    if result['result'] == 'SUCCESS':
    #        self.logger.debug(f'Revoked VIP for user {name}/{steam_id_64}')
    #        return True
    #    else:
    #        self.logger.error(f'Failed to remove VIP user on "{rcon_server_url}": {result}')
    #        return False

    @for_each_rcon
    async def get_vip(self, rcon_server_url, steam_id_64):
        """
        Queries the RCON server for all VIP's, and returns a single VIP object
        based on the input steam64id.
        """
        vip_list = await self.get_rcon(rcon_server_url, "get_vip_ids")
        for vip in vip_list:
            # Work around for https://github.com/MarechJ/hll_rcon_tool/issues/248
            # We need to verify numerical input
            try:
                if vip["player_id"] == steam_id_64:
                    return vip["vip_expiration"]
            except ValueError as e:
                self.logger.error(f"Improper steam ID for VIP entry from RCON: {e}")
                self.logger.error(f"Failed entry: {vip}")
                continue
        return None

    @for_each_rcon
    async def get_player_list(self, rcon_server_url):
        """
        Queries the RCON server(s) for a list of players.
        """
        return await self.get_rcon(rcon_server_url, "get_players")

    @for_single_rcon
    async def send_player_message(self, rcon_server_url, steam_id_64, message):
        """
        Send a player a message via the RCON.

        Returns True for success, False for failure
        """

        if not global_config["hell_let_loose"]["allow_messages_to_players"]:
            # early exit if config says don't send messages to players...
            # useful when (sneakily) testing!
            return True

        try:
            result = await self.post_rcon(
                rcon_server_url,
                "message_player",
                {
                    "player_id": steam_id_64,
                    "message": message,
                },
            )
            if result:
                return True
        except:
            self.logger.exception("An Exception occurred while messaging player")
        else:
            self.logger.error(f"Failed sending message to user {steam_id_64}: {result}")
        return False

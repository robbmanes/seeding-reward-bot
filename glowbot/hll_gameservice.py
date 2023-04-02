class HLL_Gameservice(object):
    """
    Class representing interactions with in-game users via the hll_rcon.

    This is unfortunately incredibly limited by the RCON tooling at this time.
    We have to continously make API calls for logs to monitor chat in order to respond to commands
    which is massively inefficient.  Hopefully, some time in the future the hll_rcon_tool will
    support websockets/subscribable events so we're not such a drain on the RCON for this sort
    of thing.
    """

    def __init__(self):
        pass
    
    def run(self):
        pass
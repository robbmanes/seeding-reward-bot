import requests

# API Class for https://github.com/MarechJ/hll_rcon_tool
class HLL_RCON_Connection(object):

    def __init__(self, config):
        pass

    def auth_session(self, username, password):
        self.client = requests.session()
        auth_response = self.client.post(self.config.api_endpoint,
                                    json={
                                        'username': self.config.username,
                                        'password': self.config.password,
                                    },
                                    verify=self.config.tls_verify)
        
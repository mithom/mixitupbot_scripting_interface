import requests
import random


class MixerApi(object):
    v1 = 'https://mixer.com/api/v1/'
    v2 = 'https://mixer.com/api/v2/'
    verify = True

    # noinspection PyPep8Naming
    def __init__(self, config, OAuthKey):
        self.OAuthKey = OAuthKey
        self.config = config

    def get_current_user_id(self):
        headers = {'Authorization': "Bearer " + self.OAuthKey or self.config["authkey"]}
        r = requests.get(self.v1 + 'users/current', headers=headers, timeout=1, verify=self.verify)
        return r.json()["id"]

    def get_channel_id(self):
        r = requests.get(self.v1 + 'channels/%s?fields=id' % self.config["channel"], timeout=1, verify=self.verify)
        return r.json()["id"]

    def get_channel_online(self):
        try:
            r = requests.get(self.v1 + 'channels/%s?fields=online' % self.config["channel"], timeout=1.5,
                             verify=self.verify)
        except requests.exceptions.Timeout:
            return False
        return r.json()["online"]

    def get_chat(self, channel_id):
        headers = {'Authorization': "Bearer " + self.OAuthKey}
        r = requests.get(self.v1 + 'chats/%i' % channel_id, headers=headers, timeout=1, verify=self.verify)
        data = r.json()
        return random.choice(data["endpoints"]), data.get("authkey", None), \
               data.get("roles", []), data.get("permissions", [])

    def get_user_id(self):
        return requests.get(
            self.v1 + 'users/search?query=%s' % self.config["username"], timeout=2, verify=self.verify
        ).json()[0]["id"]

    def get_chatter_list(self, channel_id):
        resp = requests.get(self.v2 + 'chats/{}/users?limit=50'.format(channel_id), timeout=5,
                            verify=self.verify)
        yield resp.json()
        while 'next' in resp.links:
            resp = requests.get(resp.links['next']['url'], timeout=5, verify=self.verify)
            yield resp.json()

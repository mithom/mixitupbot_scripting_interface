import requests
# noinspection PyUnresolvedReferences
from ChatServices.mixer import MixerChat as ChatService


# noinspection PyUnusedLocal
class DataService(object):
    mixitupbot = "http://localhost:8911/api"
    required_settings = {"username": {}, "currency_name": {}}

    def __init__(self, parent, config):
        self.currency_id = None
        self.channel_id = parent.ChatService.channel_id
        self.Parent = parent
        self.currency_name = config["currency_name"]

    class MIUException(Exception):
        def __init__(self, address, function_name):
            self.address = DataService.mixitupbot + address
            self.function_name = function_name
            Exception.__init__(self, 'unable to contact Mixitupapp developper API: {} from function {}'.format(
                self.address, self.function_name))

    def remove_points(self, user_id, username, amount):
        path = '/users/%i/currency/%s/adjust' % (user_id, self._get_currency_id())
        resp = requests.patch(
            self.mixitupbot + path,
            json={"Amount": -amount}, timeout=1)
        if resp.status_code in [200, 403]:
            return resp.status_code == 200
        else:
            raise self.MIUException(path, self.remove_points.__name__)

    def add_points(self, user_id, username, amount):
        path = '/users/%i/currency/%s/adjust' % (user_id, self._get_currency_id())
        resp = requests.patch(
            self.mixitupbot + path,
            json={"amount": amount}, timeout=1)
        if resp.status_code in [200, 403]:
            return resp.status_code == 200
        else:
            raise self.MIUException(path, self.add_points.__name__)

    def add_points_all(self, points_dict):
        path = '/currency/%i/give' % self._get_currency_id()
        resp = requests.post(
            self.mixitupbot + path,
            json=[{"Amount": amount, "UsernameOrID": user} for user, amount in points_dict.iteritems()],
            timeout=2)
        if resp.status_code == 200:
            return []
        else:
            return [self.Parent.viewer_list[user] for user in points_dict]

    def _get_currency_id(self):
        if self.currency_id is None:
            resp = requests.get(self.mixitupbot + "/currency", timeout=1)
            if resp.status_code == 200:
                currency = filter(lambda x: x["Name"] == self.currency_name, resp.json())[0]  # type: dict
                self.currency_id = currency["ID"]
                self.Parent.ranks = {rank["Name"]: rank["MinimumPoints"] for rank in currency["Ranks"]}
        return self.currency_id

    def get_top_currency(self, top):
        path = '/currency/%i/top?count=%i' % (self._get_currency_id(), top)
        resp = requests.get(self.mixitupbot + path, timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            # noinspection PyTypeChecker
            return {
                user["ID"]: filter(lambda x: x["ID"] == self._get_currency_id(), user["Currencyamounts"])[0]['Amount']
                for user in data}
        else:
            raise self.MIUException(path, self.get_top_currency.__name__)

    def get_hours(self, user_id):
        path = "/users/" + str(user_id)
        resp = requests.get(self.mixitupbot + path, timeout=1)
        if resp.status_code == 200:
            data = resp.json()
            return data["ViewingMinutes"] / 60
        else:
            raise self.MIUException(path, self.get_hours.__name__)

    def get_hours_all(self, users):
        path = '/users'
        resp = requests.post(self.mixitupbot + path, json=users, timeout=2)
        if resp.status_code == 200:
            return {data["ID"]: data["ViewingMinutes"] / 60 for data in resp.json()}
        else:
            raise self.MIUException(path, self.get_hours_all.__name__)

    def get_points(self, user_id):
        path = "/users/" + str(user_id)
        resp = requests.get(self.mixitupbot + path, timeout=1)
        if resp.status_code == 200:
            # noinspection PyTypeChecker
            return filter(lambda x: x["ID"] == self._get_currency_id(), resp.json()["Currencyamounts"])[0]['Amount']
        else:
            raise self.MIUException(path, self.get_points.__name__)

    def get_points_all(self, users):
        path = '/users'
        resp = requests.post(self.mixitupbot + path, json=users, timeout=2)
        if resp.status_code == 200:
            # noinspection PyTypeChecker
            return [filter(lambda x: x["ID"] == self._get_currency_id(), data["Currencyamounts"])[0]['Amount']
                    for data in resp.json()]
        else:
            raise self.MIUException(path, self.get_points_all.__name__)

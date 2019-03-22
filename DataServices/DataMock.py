import random
# noinspection PyUnresolvedReferences
from ChatServices.ChatMock import ChatMock as ChatService


# noinspection PyUnusedLocal,PyMethodMayBeStatic
class DataService(object):
    required_settings = {}

    def __init__(self, parent, _config):
        self.Parent = parent
        self.currency_name = 'Points'

    def remove_points(self, user_id, username, amount):
        return True

    def add_points(self, user_id, username, amount):
        return True

    def add_points_all(self, points_dict):
        return []

    def get_points(self, user_id):
        return int(random.random() * max(self.Parent.ranks.values() + [500]))

    def get_hours(self, user_id):
        return int(random.random() * 600)

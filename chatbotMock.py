import importlib
import sys
import os
import time
import requests
import json


# noinspection PyPep8Naming,PyUnusedLocal
class Parent(object):
    viewer_list = {}
    stop = False
    cooldowns = {}
    user_cooldowns = {}
    MixerChat = None
    websocket = None
    currency_name = "LyonBucks"
    mixitupbot = "http://localhost:8911/api"
    subscribers = {}
    API_Key = None
    stream_online = False
    currency_id = None
    ranks = None

    @classmethod
    def SendStreamMessage(cls, msg):
        cls.MixerChat.send_msg(msg)
        cls.stop = True

    @classmethod
    def get_currency_id(cls):
        if cls.currency_id is None:
            resp = requests.get(cls.mixitupbot + "/currency", timeout = 1)
            if resp.status_code == 200:
                currency = filter(lambda x: x["Name"] == cls.currency_name, resp.json())[0]
                cls.currency_id = currency["ID"]
                cls.ranks = {rank["Name"]: rank["MinimumPoints"] for rank in currency["Ranks"]}
        return cls.currency_id

    @classmethod
    def Log(cls, script_name, log):
        print "log from " + script_name + ": " + log

    @classmethod
    def RemovePoints(cls, user_id, username, amount):
        requests.patch('http://localhost:8911/api/users/%i/currency/%s/adjust'%(usser_id, cls.get_currency_id()),
                       json.dumps({"amount":-amount}), timeout=0.5)
        return resp.status_code == 200

    @classmethod
    def AddPoints(cls, user_id, username, amount):
        requests.patch('http://localhost:8911/api/users/%i/currency/%s/adjust'%(usser_id, cls.get_currency_id()),
                       json.dumps({"amount":amount}), timeout=0.5)
        return resp.status_code == 200
    @classmethod
    def AddPointsAll(cls, points_dict):
        print "not yet implemented: AddPointsAll"
        return filter(lambda user_id: user_id in cls.viewer_list, points_dict)

    @classmethod
    def IsLive(cls):
        return cls.stream_online

    @classmethod
    def GetDisplayName(cls, user_id):
        return cls.viewer_list[user_id]["username"]

    @classmethod
    def GetDisplayNames(cls, user_ids):
        return [cls.viewer_list[user_id]["username"] for user_id in user_ids]

    @classmethod
    def GetActiveUsers(cls):  # TODO: filter active
        return [user_data["username"] for user_data in cls.viewer_list.itervalues()]

    @classmethod
    def GetViewerList(cls):
        return [user_data["username"] for user_data in cls.viewer_list.itervalues()]

    # to make the mock work
    @classmethod
    def add_viewer(cls, user_id, user_data):
        cls.viewer_list[user_id] = user_data

    @classmethod
    def GetCurrencyName(cls):
        return cls.currency_name

    @classmethod
    def GetChannelName(cls):
        return cls.MixerChat.config["channel"]

    @classmethod
    def GetPoints(cls, user_id):
        data = requests.get(cls.mixitupbot + "/users/" + str(user_id), timeout=0.5).json()
        try:
            return [x["Amount"] for x in data["CurrencyAmounts"] if x["ID"] == cls.get_currency_id()][0]
        except IndexError:
            return 0

    @classmethod
    def IsOnUserCooldown(cls, scriptname, commandname, user):
        return time.time() < cls.user_cooldowns.get(scriptname + commandname, {}).get(user, 0)

    @classmethod
    def IsOnCooldown(cls, scriptname, commandname):
        return time.time() < cls.cooldowns.get(scriptname + commandname, 0)

    @classmethod
    def AddUserCooldown(cls, scriptname, commandname, user, seconds):
        if scriptname + commandname not in cls.user_cooldowns:
            cls.user_cooldowns[scriptname + commandname] = {}
        cls.user_cooldowns[scriptname + commandname][user] = time.time() + seconds

    @classmethod
    def AddCooldown(cls, scriptname, commandname, seconds):
        cls.cooldowns[scriptname + commandname] = time.time() + seconds

    @classmethod
    def HasPermission(cls, user, permission, extra):
        print "not yet implemented: HasPermission"
        return True

    @classmethod
    def BroadcastWsEvent(cls, eventname, jsondata):
        for client_id, client in Parent.subscribers.get(eventname, {}).iteritems():
            cls.websocket.send_message(client, json.dumps({"event": eventname, "data": jsondata}))

    @classmethod
    def GetRequest(cls, url, headers):
        resp = requests.get(url, headers=headers, timeout=0.5)
        return json.dumps({"status": resp.status_code,
                           "response": resp.text})

    @staticmethod
    def on_message(client, server, message):
        data = json.loads(message)
        if data.get("api_key", None) == Parent.API_Key:
            for event in data.get("events", {}):
                if event in Parent.subscribers:
                    Parent.subscribers[event][client["id"]] = client
                else:
                    Parent.subscribers[event] = {client["id"]: client}

    @staticmethod
    def on_client_connect(client, server):
        print "client connected" + str(client)

    @staticmethod
    def on_client_disconnect(client, server):
        for event in Parent.subscribers:
            if client["id"] in Parent.subscribers[event]:
                del Parent.subscribers[event][client["id"]]


# noinspection PyPep8Naming
class Data(object):
    def __init__(self, user, username, msg, whisper=False):
        self.Message = msg
        self.User = user
        self.UserName = username
        self.Whisper = whisper

    def IsChatMessage(self):
        return not self.Whisper

    def IsWhisper(self):
        return self.Whisper

    def IsFromDiscord(self):  # no discord will be implemented
        return False

    def GetParamCount(self):
        return len(self.Message.split())

    def GetParam(self, index):
        return self.Message.split()[index]


def start(script_name, folder=None):
    def gather_input():
        user = raw_input("username? ")
        if len(user) > 0:
            messages.append(Data("id:" + user, user, raw_input("msg: ")))

    sys.path.append(os.path.join(os.path.dirname(__file__), folder or script_name))
    if not script_name.endswith("_StreamlabsSystem"):
        script_name += "_StreamlabsSystem"

    script = importlib.import_module(script_name)
    script.Parent = Parent

    script.Init()
    messages = []
    while True:
        script.Tick()
        gather_input()
        if len(messages) > 0:
            script.Execute(messages.pop())


if __name__ == "__main__":
    start(*raw_input().split())

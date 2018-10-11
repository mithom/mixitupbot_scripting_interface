import importlib
import sys
import os
import time
import requests
import json
from threading import Thread
import random


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
    ranks = {}

    @classmethod
    def SendStreamMessage(cls, msg):
        cls.MixerChat.send_msg(msg)
        cls.stop = True

    @classmethod
    def SendStreamWhisper(cls, user, msg):
        username = cls.viewer_list[user]["username"]
        cls.MixerChat.send_whisper(username, msg)
        cls.stop = True

    @classmethod
    def get_currency_id(cls):
        if cls.currency_id is None:
            resp = requests.get(cls.mixitupbot + "/currency", timeout=1)
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
        try:
            resp = requests.patch(
                cls.mixitupbot + '/users/%i/currency/%s/adjust' % (user_id, cls.get_currency_id()),
                json={"Amount": -amount}, timeout=0.5)
            return resp.status_code == 200
        except requests.exceptions.Timeout:
            return False

    @classmethod
    def AddPoints(cls, user_id, username, amount):
        try:
            resp = requests.patch(
                cls.mixitupbot + '/users/%i/currency/%s/adjust' % (user_id, cls.get_currency_id()),
                json={"amount": amount}, timeout=0.5)
            return resp.status_code == 200
        except requests.exceptions.Timeout:
            return False
        
    @classmethod
    def AddPointsAll(cls, points_dict):  # TODO: check if users are in viewerlist
        try:
            resp = requests.post(
                cls.mixitupbot + '/currency/%i/give' % cls.get_currency_id(),
                json=[{"Amount": amount, "UsernameOrID": user} for user, amount in points_dict.iteritems()], timeout=1.5)
            if resp.status_code == 200:
                return []
            else:
                return [cls.viewer_list[user] for user in points_dict]
        except requests.exceptions.Timeout:
            return [False for i in xrange(len(points_dict))]
        
    @classmethod
    def AddPointsAllAsync(cls, points_dict, callback):
        thread = Thread(target=cls.AddPointsAllAsync_, args=(points_dict, callback))
        thread.daemon = True
        thread.run()

    @classmethod
    def AddPointsAllAsync_(cls, points_dict, callback):
        resp = cls.AddPointsAll(points_dict)
        callback(resp)

    @classmethod
    def GetTopCurrency(cls, top):
        try:
            resp = requests.get(cls.mixitupbot + '/currency/%i/top?count=%i' % (cls.get_currency_id(), top), timeout=0.5)
            data = resp.json()
        except requests.exceptions.Timeout:
            return []
        try:
            return {user["ID"]:filter(lambda x: x["ID"] == cls.get_currency_id(), user["Currencyamounts"])[0]["Amount"] for user in data}
        except IndexError:
            return []

    @classmethod
    def GetRank(cls, user):
        points = cls.GetPoints(user)
        max_min_amount = 0
        high_rank = ""
        for rank, min_amount in cls.ranks.iteritems():
            if points > min_amount > max_min_amount:
                high_rank = rank
                max_min_amount = min_amount
        return high_rank
    
    @classmethod
    def GetRanksAll(cls, users):
        print "not yet implemented"
        pass

    @classmethod
    def GetHours(cls, user_id):
        try:
            data = requests.get(cls.mixitupbot + "/users/" + str(user_id), timeout=0.5).json()
        except requests.exceptions.Timeout:
            return 0
        if resp.status_code == 200:
            return data["ViewingMinutes"] / 60
        else:
            return 0
    
    @classmethod
    def GetHoursAll(cls, users):
        print "not yet implemented"
        try:
            resp = requests.post(cls.mixitupbot + '/users', json=users, timeout=1)
        except requests.exceptions.Timeout:
            return 0
        return { data["ID"]: data["ViewingMinutes"]/60 for data in resp.json()}

    @classmethod
    def GetCurrencyUsers(cls, users):
        print "not yet implemented"
        pass

    @classmethod
    def GetPoints(cls, user_id):
        try:
            resp = requests.get(cls.mixitupbot + "/users/" + str(user_id), timeout=0.5)
        except requests.exceptions.Timeout:
            return 0
        if resp.status_code == 200:
            try:
                return filter(lambda x: x["ID"] == cls.get_currency_id(), resp.json()["Currencyamounts"])[0]["Amount"]
            except IndexError:
                return 0
        else:
            return 0
        
    @classmethod
    def GetPointsAll(cls, users):
        try:
            resp = requests.post(cls.mixitupbot + '/users', json=users, timeout=1)
        except requests.exceptions.Timeout:
            return 0
        try:
            return [filter(lambda x: x["ID"] == cls.get_currency_id(), data["Currencyamounts"])[0]["Amount"]
                    for data in resp.json()]
        except IndexError:
            return 0

    @classmethod
    def IsLive(cls):
        return cls.stream_online

    @classmethod
    def GetDisplayName(cls, user_id):
        print cls.viewer_list
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
    def GetCooldownDuration(cls, scriptname, commandname):
        return round((cls.cooldowns.get(scriptname + commandname, 0) - time.time())*100)/100

    @classmethod
    def GetUserCooldownDuration(cls, scriptname, commandname, user):
        return round((cls.user_cooldowns.get(scriptname + commandname, {}).get(user, 0) - time.time())*100)/100

    functions = {"Everyone": lambda x, y: True,
                 "Regular": lambda x, y: Parent.GetHours(x) / 60 >= 5,
                 "Subscriber": lambda x, y: "Subscriber" in Parent.viewer_list[x]["roles"],
                 "GameWisp Subscriber": lambda x, y: False,
                 "Moderator": lambda x, y: "Moderator" in Parent.viewer_list[x]["roles"] or
                                           "ChannelEditor" in Parent.viewer_list[x]["roles"] or
                                           "Owner" in Parent.viewer_list[x]["roles"],
                 "Editor": lambda x, y: "ChannelEditor" in Parent.viewer_list[x]["roles"] or
                                        "Owner" in Parent.viewer_list[x]["roles"],
                 "User_Specific": lambda x, y: y == Parent.viewer_list[x]["username"],
                 "Min_Rank": lambda x, y: Parent.GetPoints(x) >= Parent.ranks[y],
                 "Min_Points": lambda x, y: Parent.GetPoints(x) >= y,
                 "Min_Hours": lambda x, y: Parent.GetHours(x) >= y}

    @classmethod
    def HasPermission(cls, user, permission, extra):
        return cls.functions[permission](user, extra)

    @classmethod
    def BroadcastWsEvent(cls, eventname, jsondata):
        for client_id, client in Parent.subscribers.get(eventname, {}).iteritems():
            cls.websocket.send_message(client, json.dumps({"event": eventname, "data": jsondata}))

    @classmethod
    def GetRequest(cls, url, headers):
        resp = requests.get(url, headers=headers, timeout=0.5)
        return json.dumps({"status": resp.status_code,
                           "response": resp.text})
    @classmethod
    def GetRandom(cls, mini, maxi):
        return random.randint(mini, maxi)

    @staticmethod
    def on_message(client, server, message):
        data = json.loads(message)
        if data.get("api_key", None) == Parent.API_Key:
            for event in data.get("events", {}):
                if event in Parent.subscribers:
                    Parent.subscribers[event][client["id"]] = client
                else:
                    Parent.subscribers[event] = {client["id"]: client}

    @classmethod
    def GetStreamingService(cls):
        return "Mixer"

    @staticmethod
    def on_client_connect(client, server):
        print "client connected" + str(client)

    @staticmethod
    def on_client_disconnect(client, server):
        for event in Parent.subscribers:
            if client["id"] in Parent.subscribers[event]:
                del Parent.subscribers[event][client["id"]]


def concat(msg1, msg2):
            return msg1 + msg2["text"]


# noinspection PyPep8Naming
class Data(object):
    def __init__(self, user, username, jsond, raw):
        self.Message = reduce(concat, jsond["data"].get("message", {}).get("message", ""), "")
        self.User = user
        self.UserName = username
        self.Whisper = "whisper" in jsond["data"].get("message", {}).get("meta", {})
        self.RawData = raw
        self.ServiceType = "Mixer"

    def IsChatMessage(self):
        return self.Message != ""

    def IsWhisper(self):
        return self.Whisper

    @staticmethod
    def IsFromDiscord():  # discord might be implemented
        return False

    @staticmethod
    def IsFromTwitch():  # no twitch will be implemented
        return False

    @staticmethod
    def IsFromYoutube():  # no youtube will be implemented
        return False

    @staticmethod
    def IsFromMixer():  # at the moment only Mixer will be implemented
        return True

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

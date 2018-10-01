import importlib
import sys
import os
import time
import requests


# noinspection PyPep8Naming,PyUnusedLocal
class Parent(object):
    viewer_list = {}
    stop = False
    cooldowns = {}
    user_cooldowns = {}
    MixerChat = None
    currency_name = "lyonbucks"
    mixitupbot = "http://localhost:8911/api"

    @classmethod
    def SendStreamMessage(cls, msg):
        cls.MixerChat.send_msg(msg)
        cls.stop = True

    @classmethod
    def Log(cls, script_name, log):
        print "log from "+script_name+": "+log

    @classmethod
    def RemovePoints(cls, user_id, username, amount):
        return cls.GetPoints(user_id) >= amount

    @classmethod
    def AddPoints(cls, user_id, username, amount):
        resp = requests.get(cls.mixitupbot + "/users/" + str(user_id)).json()
        for currency in resp["CurrencyAmounts"]:
            if currency["Name"] == cls.currency_name:
                currency["Amount"] += amount
        print str(resp)
        print cls.mixitupbot+"/users/"+str(user_id)
        resp = requests.patch(cls.mixitupbot+"/users/"+str(user_id), data=resp, timeout=1)
        print resp

    @classmethod
    def AddPointsAll(cls, points_dict):
        return filter(lambda user_id: user_id in cls.viewer_list, points_dict)

    @classmethod
    def IsLive(cls):
        return cls.MixerChat.mixerApi.get_channel_online()

    @classmethod
    def GetDisplayName(cls, user_id):
        return cls.viewer_list[user_id]

    @classmethod
    def GetDisplayNames(cls, user_names):
        return [cls.viewer_list[username] for username in user_names]

    @classmethod
    def GetActiveUsers(cls):
        return list(cls.viewer_list)

    @classmethod
    def GetViewerList(cls):
        return list(cls.viewer_list)

    # to make the mock work
    @classmethod
    def add_viewer(cls, user, user_name):
        cls.viewer_list[user] = user_name

    @classmethod
    def GetCurrencyName(cls):
        return cls.currency_name

    @classmethod
    def GetChannelName(cls):
        return cls.MixerChat.config["channel"]

    @classmethod
    def GetPoints(cls, user_id):
        data = requests.get(cls.mixitupbot + "/users/"+str(user_id)).json()
        try:
            return [x["Amount"] for x in data["CurrencyAmounts"] if x["Name"] == cls.currency_name][0]
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
        return True

    @classmethod
    def BroadcastWsEvent(cls, eventname, jsondata):
        pass


# noinspection PyPep8Naming
class Data(object):
    def __init__(self, user, username, msg, whisper=False):
        self.Message = msg
        self.User = user
        self.UserName = username
        self.Whisper = whisper

    def IsChatMessage(self):
        return not self.Message.startswith("/w ")

    def IsWhisper(self):
        return self.Whisper

    def IsFromDiscord(self):
        return self.Message.startswith("/d ")

    def GetParamCount(self):
        return len(self.Message.split())

    def GetParam(self, index):
        return self.Message.split()[index]


def start(script_name, folder=None):
    def gather_input():
        user = raw_input("username? ")
        if len(user) > 0:
            messages.append(Data("id:"+user, user, raw_input("msg: ")))

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

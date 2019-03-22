import time
import requests
import json
from threading import Thread
import random
import sounddevice as sd
import soundfile as sf
import Queue
import dotnet  # makes clr available for scripts


# noinspection PyPep8Naming,PyUnusedLocal
class Parent(object):
    viewer_list = {}
    stop = False
    cooldowns = {}
    user_cooldowns = {}
    ChatService = None
    DataService = None
    DiscordService = None
    websocket = None
    subscribers = {}
    API_Key = None
    stream_online = False
    ranks = {}

    #######################
    # Messages
    #######################
    @classmethod
    def SendStreamMessage(cls, msg):
        cls.ChatService.send_msg(msg)
        cls.stop = True

    @classmethod
    def SendStreamWhisper(cls, user, msg):
        if user in cls.viewer_list:
            username = cls.viewer_list[user]["username"]
            cls.ChatService.send_whisper(username, msg)
        else:
            cls.ChatService.send_whisper(user, msg)
        cls.stop = True

    @classmethod
    def SendDiscordMessage(cls, msg):
        cls.DiscordService.send_msg(msg)
        cls.stop = True

    @classmethod
    def SendDiscordDM(cls, target, msg):
        cls.DiscordService.send_dm(target, msg)

    @classmethod
    def BroadcastWsEvent(cls, eventname, jsondata):
        for client_id, client in Parent.subscribers.get(eventname, {}).iteritems():
            cls.websocket.send_message(client, json.dumps({"event": eventname, "data": jsondata}))

    #######################
    # Currency
    #######################
    @classmethod
    def AddPoints(cls, user_id, username, amount):
        return cls.DataService.add_points(user_id, username, amount)

    @classmethod
    def RemovePoints(cls, user_id, username, amount):
        return cls.DataService.remove_points(user_id, username, amount)

    @classmethod
    def AddPointsAll(cls, points_dict):
        if hasattr(cls.DataService, 'add_points_all'):
            return cls.DataService.add_points_all(points_dict)
        else:
            raise NotImplementedError  # TODO: implement based on add_points

    @classmethod
    def AddPointsAllAsync(cls, points_dict, callback):
        if hasattr(cls.DataService, 'add_points_all_async'):
            return cls.DataService.add_points_all_async(points_dict, callback)
        else:
            thread = Thread(target=cls._AddPointsAllAsync, args=(points_dict, callback))
            thread.daemon = True
            thread.run()

    @classmethod
    def _AddPointsAllAsync(cls, points_dict, callback):
        resp = cls.AddPointsAll(points_dict)
        callback(resp)

    @classmethod
    def RemovePointsAll(cls, points_dict):
        if hasattr(cls.DataService, 'remove_points_all'):
            cls.DataService.remove_points_all(points_dict)
        else:
            raise NotImplementedError  # TODO: implement based on remove_points

    @classmethod
    def RemovePointsAllAsync(cls, points_dict, callback):
        if hasattr(cls.DataService, 'remove_points_all_async'):
            return cls.DataService.remove_points_all_async(points_dict, callback)
        else:
            thread = Thread(target=cls._RemovePointsAllAsync, args=(points_dict, callback))
            thread.daemon = True
            thread.run()

    @classmethod
    def _RemovePointsAllAsync(cls, points_dict, callback):
        resp = cls.AddPointsAll(points_dict)
        callback(resp)

    @classmethod
    def GetPoints(cls, user_id):
        return cls.DataService.get_points(user_id)

    @classmethod
    def GetHours(cls, user_id):
        return cls.DataService.get_hours(user_id)

    @classmethod
    def GetRank(cls, user):  # TODO: check for non-currency ranks
        points = cls.DataService.get_points(user)
        max_min_amount = 0
        high_rank = ""
        for rank, min_amount in cls.ranks.iteritems():
            if points > min_amount > max_min_amount:
                high_rank = rank
                max_min_amount = min_amount
        return high_rank

    @classmethod
    def GetTopCurrency(cls, top):
        return cls.DataService.get_top_currency(top)

    @classmethod
    def GetTopHours(cls, top):
        return cls.DataService.get_top_hours(top)

    @classmethod
    def GetPointsAll(cls, users):
        users = list(users)
        if hasattr(cls.DataService, 'get_points_all'):
            return cls.DataService.get_points_all(users)
        else:
            raise NotImplementedError  # TODO: implement on basis of get_points

    @classmethod
    def GetRanksAll(cls, users):
        users = list(users)
        raise NotImplementedError

    @classmethod
    def GetHoursAll(cls, users):
        users = list(users)
        if hasattr(cls.DataService, 'get_hours_all'):
            return cls.DataService.get_hours_all(users)
        else:
            raise NotImplementedError  # TODO: implement on basis of GetHours

    @classmethod
    def GetCurrencyUsers(cls, users):
        users = list(users)
        raise NotImplementedError

    #######################
    # Permissions
    #######################
    # TODO: use ChatService for roles
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

    #######################
    # Retrieving Viewers
    #######################
    @classmethod
    def GetViewerList(cls):
        return [user_data["username"] for user_data in cls.viewer_list.itervalues()]

    # TODO: differentiate from GetViewerList, database with user activity
    @classmethod
    def GetActiveUsers(cls):  # TODO: filter active
        return [user_data["username"] for user_data in cls.viewer_list.itervalues()]

    @classmethod
    def GetRandomActiveViewer(cls):
        if hasattr(cls.ChatService, 'get_random_active_viewer'):
            return cls.ChatService.get_random_active_viewer()
        else:
            return random.choice(cls.GetActiveUsers())

    @classmethod
    def GetDisplayName(cls, user_id):
        if user_id in cls.viewer_list:
            return cls.viewer_list[user_id]["username"]
        else:
            cls.ChatService.get_display_name(user_id)

    @classmethod
    def GetDisplayNames(cls, user_ids):
        user_ids = list(user_ids)
        return [cls.viewer_list[user_id]["username"] for user_id in user_ids]

    #######################
    # Cooldown Management
    #######################
    @classmethod
    def AddCooldown(cls, scriptname, commandname, seconds):
        cls.cooldowns[scriptname + commandname] = time.time() + seconds

    @classmethod
    def IsOnCooldown(cls, scriptname, commandname):
        return time.time() < cls.cooldowns.get(scriptname + commandname, 0)

    @classmethod
    def GetCooldownDuration(cls, scriptname, commandname):
        return round((cls.cooldowns.get(scriptname + commandname, 0) - time.time()) * 100) / 100

    @classmethod
    def AddUserCooldown(cls, scriptname, commandname, user, seconds):
        if scriptname + commandname not in cls.user_cooldowns:
            cls.user_cooldowns[scriptname + commandname] = {}
        cls.user_cooldowns[scriptname + commandname][user] = time.time() + seconds

    @classmethod
    def IsOnUserCooldown(cls, scriptname, commandname, user):
        return time.time() < cls.user_cooldowns.get(scriptname + commandname, {}).get(user, 0)

    @classmethod
    def GetUserCooldownDuration(cls, scriptname, commandname, user):
        return round((cls.user_cooldowns.get(scriptname + commandname, {}).get(user, 0) - time.time()) * 100) / 100

    #######################
    # OBS
    #######################

    #######################
    # API Requests
    #######################
    @classmethod
    def GetRequest(cls, url, headers):
        resp = requests.get(url, headers=headers, timeout=1)
        return json.dumps({"status": resp.status_code,
                           "response": resp.text})

    @classmethod
    def PostRequest(cls, url, headers, content, isJsonContent=True):
        if isJsonContent:
            resp = requests.post(url, headers=headers, json=content, timeout=0.5)
        else:
            resp = requests.post(url, headers=headers, data=content, timeout=0.5)
        return json.dumps({"status": resp.status_code, "response": resp.text})

    @classmethod
    def DeleteRequest(cls, url, headers):
        resp = requests.delete(url, headers=headers, timeout=0.5)
        return json.dumps({"status": resp.status_code, "response": resp.text})

    @classmethod
    def PutRequest(cls, url, headers, content, isJsonContent=True):
        if isJsonContent:
            resp = requests.put(url, headers=headers, json=content, timeout=0.5)
        else:
            resp = requests.put(url, headers=headers, data=content, timeout=0.5)
        return json.dumps({"status": resp.status_code, "response": resp.text})

    #######################
    # Stream infos
    #######################
    @classmethod
    def IsLive(cls):
        return cls.stream_online

    #######################
    # Miscellaneous
    #######################
    @classmethod
    def GetRandom(cls, mini, maxi):
        return random.randint(mini, maxi)

    @classmethod
    def GetStreamingService(cls):
        return "Mixer"

    @classmethod
    def GetChannelName(cls):
        return cls.ChatService.get_channel_name()

    @classmethod
    def GetCurrencyName(cls):
        return cls.DataService.currency_name

    @classmethod
    def Log(cls, script_name, log):
        print "log from " + script_name + ": " + log

    @classmethod
    def PlaySound(cls, filepath, volume):
        block_size = 20
        q = Queue.Queue(maxsize=2048)
        f = sf.SoundFile(filepath).__enter__()

        def sound_callback(outdata, frames, _time, status):
            _data = q.get_nowait()
            if len(_data) < len(outdata):
                outdata[:len(_data)] = _data
                outdata[len(_data):] = b'\x00' * (len(outdata) - len(_data))
                f.__exit__()
                raise sd.CallbackStop
            else:
                outdata[:] = _data

        data = None
        for _ in range(2048):
            data = f.buffer_read(block_size, dtype='float32')
            if not data:
                break
            q.put_nowait(data)  # Pre-fill queue
        stream = sd.RawOutputStream(samplerate=f.samplerate, blocksize=block_size, dtype='float32',
                                    callback=sound_callback, channels=f.channels)

        def read_sound_to_stream():
            _data = True
            with stream:
                timeout = block_size * 2048.0 / f.samplerate
                while _data:
                    _data = f.buffer_read(block_size, dtype='float32')
                    q.put(_data, timeout=timeout)

        thread = Thread(target=read_sound_to_stream)
        thread.daemon = True
        thread.start()

    @classmethod
    def GetQueue(cls, max_nb):
        raise NotImplementedError

    #######################
    # internal workings
    #######################
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

    @classmethod
    def add_viewer(cls, user_id, user_data):
        cls.viewer_list[user_id] = user_data


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


# noinspection PyPep8Naming
class Currency(object):  # this should be read only!
    def __init__(self, userid, username, points, minutes_watched, rank):
        self.__UserId = userid
        self.__UserName = username
        self.__Points = points
        self.__TimeWatched = minutes_watched
        self.__Rank = rank

    @property
    def UserId(self):
        return self.__UserId

    @property
    def UserName(self):
        return self.__UserName

    @property
    def Points(self):
        return self.__Points

    @property
    def TimeWatched(self):
        return self.__TimeWatched

    @property
    def Rank(self):
        return self.__Rank

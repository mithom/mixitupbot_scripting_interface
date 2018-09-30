import database as db
from chatbotMock import Parent, Data
import json
import sys
import os
import webbrowser
import random
from threading import Thread

sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
import OAuth
import websocket
import requests
import time
import atexit

file_path = os.path.dirname(__file__)
script_path = os.path.join(file_path, 'scripts')


def init(config):
    OAuth.config = config
    db.create_table_if_not_exists()
    print "start"
    OAuth.start()
    print "done"
    url = "https://127.0.0.1:5555/"
    webbrowser.open(url, new=1, autoraise=True)
    return OAuth.stop()


def read_settings():
    # Open JSON settings file
    with open("settingsM.json") as data:
        return json.load(data)


class MixerApi(object):
    v1 = 'https://mixer.com/api/v1/'

    def __init__(self, config, OAuthKey):
        self.OAuthKey = OAuthKey
        self.config = config

    def get_current_user_id(self):
        headers = {'Authorization': "Bearer " + self.OAuthKey or self.config["authkey"]}
        r = requests.get(self.v1 + 'users/current', headers=headers)
        return r.json()["id"]

    def get_channel_id(self):
        r = requests.get(self.v1 + 'channels/%s?fields=id' % self.config["username"])
        return r.json()["id"]

    def get_chat(self, channel_id):
        headers = {'Authorization': "Bearer " + self.OAuthKey}
        r = requests.get(self.v1 + 'chats/%i' % channel_id, headers=headers)
        data = r.json()
        return random.choice(data["endpoints"]), data.get("authkey", None), \
               data.get("roles", []), data.get("permissions", [])

    def get_user_id(self):
        return requests.get(self.v1 + 'users/search/%s' % self.config["username"]).json()[0]["id"]


class MixerChat(object):
    id_types = {}

    OAuthKey = None
    config = None
    mixerApi = None
    user_id = None
    channel_id = None
    channel_url = None
    mixer = None
    authKey = None
    roles = []
    permissions = []
    message_id = None

    @classmethod
    def init(cls, config):
        keys = init(config)
        cls.OAuthKey = keys["access_token"]
        cls.config = config
        cls.mixerApi = MixerApi(config, cls.OAuthKey)
        cls.user_id = cls.mixerApi.get_current_user_id()
        cls.channel_id = cls.mixerApi.get_channel_id()
        cls.chat_url, cls.authKey, cls.roles, cls.permissions = cls.mixerApi.get_chat(cls.channel_id)
        headers = {'Client-ID': cls.config["client_id"]}
        cls.mixer = websocket.WebSocketApp(cls.chat_url, header=headers)
        cls.mixer.on_message = cls.on_message
        cls.mixer.on_open = cls.connect
        cls.mixer.on_close = cls.close
        cls.mixer.on_error = cls.error
        cls.message_id = cls.message_id_gen()
        # websocket.enableTrace(True)

    @staticmethod
    def message_id_gen():
        i = 0
        while True:
            i += 1
            i %= 100000
            yield i

    @staticmethod
    def close():
        print('closed')

    @staticmethod
    def error(err):
        print('error')
        print(err)

    # authenticate
    @staticmethod
    def connect(mixer):
        mixer.send(json.dumps(MixerChat.auth()))

    @staticmethod
    def on_message(mixer, message):
        data = json.loads(message)
        type_ = data["type"]
        if type_ == 'reply':
            MixerChat.handle_reply(data)
        elif type_ == 'event':
            MixerChat.handle_event(data)

    @classmethod
    def start(cls):
        print("started")
        cls.mixer.run_forever()
        print('never reach this')

    @classmethod
    def auth(cls):
        return cls.create_method("auth", cls.channel_id, cls.user_id, cls.authKey)

    @classmethod
    def create_method(cls, method, *args):
        id_ = cls.message_id.next()
        cls.id_types[id_] = method
        return {"type": "method", "method": method, "arguments": args, "id": id_}

    @classmethod
    def send_msg(cls, mixer, message, sp=None):  # Send a chat message (if s is true, the message will append /me)
        if sp:
            message = "/me " + message
        mixer.send(json.dumps(cls.create_method("msg", message)))

    @classmethod
    def handle_reply(cls, data):
        pass

    @classmethod
    def handle_event(cls, data):
        def concat(msg1, msg2):
            return msg1 + msg2["text"]

        if data['event'] == "ChatMessage":
            data["data"]["message"]["message"].insert(0, "")
            msg = reduce(concat, data["data"]["message"]["message"])
            whisp = "whisper" in data["data"]["message"]["meta"]
            ScriptHandler.to_process.append(Data(data["data"]["user_id"], data["data"]["user_name"], msg, whisp))
        if data['event'] == "UserJoin":
            Parent.add_viewer(data["data"]["id"], data["data"]["username"])
        if data['event'] == "UserLeave":
            del Parent.viewer_list[data["data"]["id"]]


class ScriptHandler(object):
    to_process = []

    def __init__(self):
        self.scripts = []
        self.script_folders = [f for f in os.listdir(script_path) if os.path.isdir(os.path.join(script_path, f))]
        for script_folder in self.script_folders:
            content = os.listdir(os.path.join(script_path, script_folder))
            script_name = script_folder + "_StreamlabsSystem"
            if script_name + ".py" in content and "UI_Config.json" in content:
                try:
                    self.scripts.append(self.import_by_filename(
                        os.path.join(os.path.join(script_path, script_folder), script_name + ".py")))
                except Exception as e:
                    print e.message
            else:
                print("invalid script folder: " + script_folder)

    def init(self):
        for script in self.scripts:
            script.Parent = Parent
            script.Init()

    def scripts_loop(self):
        next_t = 0
        while True:
            if len(self.to_process) > 0:
                data = self.to_process.pop(0)
                for script in self.scripts:
                    try:
                        script.Execute(data)
                    except Exception as e:
                        print 'Error', e.message
                    if Parent.stop:
                        Parent.stop = False
                        break
            if time.time() > next_t:
                next_t = time.time() + 0.1
                for script in self.scripts:
                    try:
                        script.Tick()
                    except Exception as e:
                        print 'Error', e.message

    @staticmethod
    def import_by_filename(filename):
        directory, module_name = os.path.split(filename)
        module_name = os.path.splitext(module_name)[0]

        path = list(sys.path)
        sys.path.insert(0, directory)
        try:
            module = __import__(module_name)
        finally:
            sys.path[:] = path  # restore
        return module


def unload():
    print "stop"
    for script in script_handler.scripts:
        try:
            script.Unload()
        except AttributeError:
            pass


atexit.register(unload)


if __name__ == "__main__":
    opt = read_settings()
    MixerChat.init(opt)
    script_handler = ScriptHandler()
    script_handler.init()
    server = Thread(target=script_handler.scripts_loop)
    server.start()
    MixerChat.start()

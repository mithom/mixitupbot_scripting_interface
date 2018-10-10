import json
import codecs
import sys
import os
import webbrowser
import random
from threading import Thread, Event
import time
import atexit
import traceback
import binascii
import ctypes

sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
from chatbotMock import Parent, Data
import OAuth
import websocket
import requests
from websocket_server import WebsocketServer


file_path = os.path.dirname(__file__)
script_path = os.path.join(file_path, 'scripts')


def init(config):
    OAuth.config = config
    OAuth.cert = os.path.join(os.path.dirname(__file__), 'script_interface.crt')
    OAuth.key = os.path.join(os.path.dirname(__file__), 'script_interface.key')
    if not OAuth.start():
        url = "https://127.0.0.1:5555/"
        webbrowser.open(url, new=1, autoraise=True)
    return OAuth.stop()


def read_settings():
    # Open JSON settings file
    with codecs.open(os.path.join(file_path, "settingsM.json"), encoding="utf-8-sig", mode="r") as data:
        return json.load(data)


class MixerApi(object):
    v1 = 'https://mixer.com/api/v1/'

    def __init__(self, config, OAuthKey):
        self.OAuthKey = OAuthKey
        self.config = config

    def get_current_user_id(self):
        headers = {'Authorization': "Bearer " + self.OAuthKey or self.config["authkey"]}
        r = requests.get(self.v1 + 'users/current', headers=headers, timeout=1)
        return r.json()["id"]

    def get_channel_id(self):
        r = requests.get(self.v1 + 'channels/%s?fields=id' % self.config["channel"], timeout=1)
        return r.json()["id"]

    def get_channel_online(self):
        r = requests.get(self.v1 + 'channels/%s?fields=online' % self.config["channel"], timeout=1.5)
        return r.json()["online"]

    def get_chat(self, channel_id):
        headers = {'Authorization': "Bearer " + self.OAuthKey}
        r = requests.get(self.v1 + 'chats/%i' % channel_id, headers=headers, timeout=1)
        data = r.json()
        return random.choice(data["endpoints"]), data.get("authkey", None), \
               data.get("roles", []), data.get("permissions", [])

    def get_user_id(self):
        return requests.get(self.v1 + 'users/search?query=%s' % self.config["username"], timeout=2).json()[0]["id"]


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
        cls.user_id = cls.mixerApi.get_user_id()
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
    def close(mixer):
        print('closed')

    @staticmethod
    def error(mixer, err):
        print('error')
        print(err)

    # authenticate
    @staticmethod
    def connect(mixer):
        mixer.send(json.dumps(MixerChat.auth()))
        connected.set()

    @staticmethod
    def on_message(mixer, message):
        data = json.loads(message)
        type_ = data["type"]
        if type_ == 'reply':
            MixerChat.handle_reply(data, message)
        elif type_ == 'event':
            MixerChat.handle_event(data, message)

    @classmethod
    def start(cls):
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
    def send_msg(cls, message):  # Send a chat message (if s is true, the message will append /me)
        if message.startswith('/me'):
            message = "/me " + message
        test = json.dumps(cls.create_method("msg", message))
        connected.wait()
        cls.mixer.send(test)

    @classmethod
    def send_whisper(cls, username, message):  # Send a chat message (if s is true, the message will append /me)
        test = json.dumps(cls.create_method("whisper", username, message))
        connected.wait()
        cls.mixer.send(test)

    @classmethod
    def handle_reply(cls, data, message):
        if cls.id_types[data["id"]] == "auth":
            if data.get("error", None) is not None:
                msg = "please authorize the correct user, you probably authorized you main account instead of your bot." \
                      "\ndelete token.json and try again!"
                ctypes.windll.user32.MessageBoxA(0, msg, "wrong account authorized", 0)

    @classmethod
    def handle_event(cls, data, message):
        if data['event'] == "ChatMessage":
            if data["data"]["user_id"] not in Parent.viewer_list:
                userdata = {"username": data["data"]["user_name"],
                            "id": data["data"]["user_id"],
                            "roles": data["data"]["user_roles"]}
                Parent.add_viewer(userdata["id"], userdata)
            ScriptHandler.to_process.append(Data(data["data"]["user_id"], data["data"]["user_name"], data, message))
        if data['event'] == "UserJoin":
            Parent.add_viewer(data["data"]["id"], data["data"])
        if data['event'] == "UserLeave":
            del Parent.viewer_list[data["data"]["id"]]
        """else:
            print data"""


class ScriptHandler(object):
    to_process = []

    def __init__(self):
        self.scripts = []
        self.API_Key = binascii.b2a_base64(os.urandom(15))[:-1]
        self.API_Socket = "ws://127.0.0.1:3337/streamlabs"
        self.websocket = None
        self.script_folders = [f for f in os.listdir(script_path) if os.path.isdir(os.path.join(script_path, f))]
        for script_folder in self.script_folders:
            content = os.listdir(os.path.join(script_path, script_folder))
            script_name = script_folder + "_StreamlabsSystem"
            if script_name + ".py" in content and "UI_Config.json" in content:
                try:
                    specific_scripth_path = os.path.join(script_path, script_folder)
                    self.scripts.append(self.import_by_filename(
                        os.path.join(specific_scripth_path, script_name + ".py")))
                    self.insert_API_Key(specific_scripth_path)
                except Exception as e:
                    print e.message
                    traceback.print_exc()
            else:
                print("invalid script folder: " + script_folder)

    def insert_API_Key(self, dir_path):
        api_file = os.path.join(dir_path, "API_KEY.js")
        try:
            with codecs.open(api_file, encoding="utf-8-sig", mode="w") as f:
                f.write('var API_Key = "{0}";\nvar API_Socket = "{1}";'.format(self.API_Key, self.API_Socket))
        except:
            traceback.print_exc()

    def start_websocket(self):
        self.websocket = WebsocketServer(3337, "127.0.0.1")
        self.websocket.set_fn_new_client(Parent.on_client_connect)
        self.websocket.set_fn_client_left(Parent.on_client_disconnect)
        self.websocket.set_fn_message_received(Parent.on_message)
        thread = Thread(target=self.websocket.run_forever)
        thread.daemon = True
        thread.start()
        Parent.websocket = self.websocket
        Parent.API_Key = self.API_Key
        
    def init(self):
        self.start_websocket()
        for script in self.scripts:
            script.Parent = Parent
            script.Init()

    def scripts_loop(self):
        self.init()
        next_t = 0
        live_check = 0
        while not stopped.is_set():
            if time.time() < live_check:
                Parent.stream_online = MixerChat.mixerApi.get_channel_online()
                live_check = time.time() + 120
            if len(self.to_process) > 0:
                data = self.to_process.pop(0)
                for script in self.scripts:
                    try:
                        script.Execute(data)
                    except Exception as e:
                        print 'Error', e.message
                        traceback.print_exc()
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
                        traceback.print_exc()

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


stopped = Event()
connected = Event()


def unload():
    print "stopping"
    stopped.set()
    if server is not None:
        server.join()
        for script in script_handler.scripts:
            try:
                script.Unload()
            except AttributeError:
                pass
    print "succesfully stopped"


server = None
atexit.register(unload)


if __name__ == "__main__":
    Parent.MixerChat = MixerChat
    opt = read_settings()
    MixerChat.init(opt)
    script_handler = ScriptHandler()
    server = Thread(target=script_handler.scripts_loop)
    server.start()
    MixerChat.start()

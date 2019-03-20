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
from chatbotInterface import Parent, Data
import OAuth
import websocket
import requests
from websocket_server import WebsocketServer
import PyChatter
import re
import Tkinter as Tk

file_path = os.path.dirname(__file__)
persistent_path = os.getenv('localappdata')
OAuth.token_file = os.path.join(persistent_path, "PyChatter", "token.json")
script_path = None  # type: str


def init(config):
    OAuth.config = config
    OAuth.cert = os.path.join(os.path.dirname(__file__), 'data', 'script_interface.crt')
    OAuth.key = os.path.join(os.path.dirname(__file__), 'data', 'script_interface.key')
    if not OAuth.start():
        url = "https://127.0.0.1:5555/"
        webbrowser.open(url, new=1, autoraise=True)
    return OAuth.stop()


def load_settings(application, force_reload=False):
    global settings, script_path
    read_success = True
    if not force_reload:
        try:
            settings = read_settings()
            script_path = settings['script_path']
            MIU.currency_name = settings['currency_name']
        except:
            read_success = False
            application.add_to_queue(application.ask_settings, username={}, client_id={}, client_secret={'show': '*'},
                                     channel={}, currency_name={})
    else:
        read_success = False
        application.add_to_queue(application.ask_settings, username={}, client_id={}, client_secret={'show': '*'},
                                 channel={}, currency_name={})
    if read_success:
        application.add_to_queue(application.finish_settings)


def store_settings(settings_):
    global settings, script_path
    script_path = settings_.get('script_path', '')
    MIU.currency_name = settings_['currency_name']
    settings = settings_
    if not os.path.isdir(os.path.join(persistent_path, "PyChatter")):
        os.makedirs(os.path.join(persistent_path, "PyChatter"))
    with codecs.open(os.path.join(persistent_path, "PyChatter", "settingsM.json"), encoding="utf-8-sig",
                     mode="w+") as f:
        json.dump(settings, f, encoding="utf-8", ensure_ascii=False)


def read_settings():
    # Open JSON settings file
    with codecs.open(os.path.join(persistent_path, "PyChatter", "settingsM.json"), encoding="utf-8-sig",
                     mode="r") as data:
        return json.load(data)


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

    def get_chatter_list(self):
        resp = requests.get(self.v2 + 'chats/{}/users?limit=50'.format(MixerChat.channel_id), timeout=5,
                            verify=self.verify)
        yield resp.json()
        while 'next' in resp.links:
            resp = requests.get(resp.links['next']['url'], timeout=5, verify=self.verify)
            yield resp.json()


# noinspection PyUnusedLocal
class MIU(object):
    class MIUException(Exception):
        def __init__(self, address, function_name):
            self.address = MIU.mixitupbot + address
            self.function_name = function_name
            Exception.__init__(self, 'unable to contact Mixitupapp developper API: {} from function {}'.format(
                self.address, self.function_name))

    mixitupbot = "http://localhost:8911/api"
    currency_name = None  # type: str

    def __init__(self):
        self.currency_id = None

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
            return [Parent.viewer_list[user] for user in points_dict]

    def _get_currency_id(self):
        if self.currency_id is None:
            resp = requests.get(self.mixitupbot + "/currency", timeout=1)
            if resp.status_code == 200:
                currency = filter(lambda x: x["Name"] == self.currency_name, resp.json())[0]  # type: dict
                self.currency_id = currency["ID"]
                Parent.ranks = {rank["Name"]: rank["MinimumPoints"] for rank in currency["Ranks"]}
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


# noinspection PyUnusedLocal
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
        if keys is None:
            return False
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
        return True

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
        print 'send whisper', username, message

    @classmethod
    def get_channel_name(cls):
        return cls.config["channel"]

    @classmethod
    def handle_reply(cls, data, message):
        if cls.id_types[data["id"]] == "auth":
            if data.get("error", None) is not None:
                msg = "please authorize the correct user, you probably authorized you main account instead of your " \
                      "bot.\ndelete token.json and try again!"
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
        if data['event'] == "WelcomeEvent":
            for user_list in cls.mixerApi.get_chatter_list():
                for user in user_list:
                    user = {'id': user['userId'], 'username': user['username'], 'roles': user['userRoles']}
                    Parent.add_viewer(user['id'], user)
            connected.set()
        """else:
            print data"""


class ScriptHandler(object):
    to_process = []

    def __init__(self, application):
        self.application = application
        self.scripts = []
        self.API_Key = binascii.b2a_base64(os.urandom(15))[:-1]
        self.API_Socket = "ws://127.0.0.1:3337/streamlabs"
        self.websocket = None
        self.script_folders = [f for f in os.listdir(script_path) if os.path.isdir(os.path.join(script_path, f))]
        script_pattern = re.compile(".*_StreamlabsSystem.py")
        for script_folder in self.script_folders:
            content = os.listdir(os.path.join(script_path, script_folder))
            script_names = filter(script_pattern.match, content)
            if len(script_names) > 0 and "UI_Config.json" in content:
                try:
                    specific_scripth_path = os.path.join(script_path, script_folder)
                    self.scripts.append(self.import_by_filename(
                        os.path.join(specific_scripth_path, script_names[0])))
                    self.insert_api_key(specific_scripth_path)
                except Exception as e:
                    print e.message
                    traceback.print_exc()
            else:
                print("invalid script folder: " + script_folder)

    def insert_api_key(self, dir_path):
        api_file = os.path.join(dir_path, "API_KEY.js")
        try:
            with codecs.open(api_file, encoding="utf-8-sig", mode="w") as f:
                f.write('var API_Key = "{0}";\nvar API_Socket = "{1}";'.format(self.API_Key, self.API_Socket))
        except Exception as e:
            print e.message
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

    def load_settings(self, script):
        return Tk.Button(text='test')  # created at root lvl

    def init(self):
        self.start_websocket()
        failed = []
        for script in self.scripts:
            try:
                script.Parent = Parent
                script.Init()
                self.application.add_to_queue(self.application.add_loaded_script, self.application.ScriptManager.Script(
                    script, self.load_settings(script), ['Version', 'Creator', 'Description']
                ))
            except Exception as e:
                failed.append(script)
                print "failed to load script", str(script)
                print e.message
                traceback.print_exc()
        for script in failed:
            self.scripts.remove(script)

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
    if MixerChat.mixer is not None:
        MixerChat.mixer.close()


server = None
atexit.register(unload)


def start(application=None):
    global script_handler, server
    Parent.ChatService = MixerChat
    Parent.DataService = MIU()
    if application is not None:
        for thread in application.threads:
            if thread.name == PyChatter.STORE_SETTINGS:
                thread.join()
    if MixerChat.init(settings):
        application.add_to_queue(application.show_script_manager)
        script_handler = ScriptHandler(application)
        server = Thread(target=script_handler.scripts_loop)
        server.start()
        MixerChat.start()


def shutdown():
    unload()
    OAuth.stop_if_running()

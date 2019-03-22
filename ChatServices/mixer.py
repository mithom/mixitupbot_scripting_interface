from Api.MixerApi import MixerApi
import websocket
import json
import ctypes
import webbrowser
from .auth.MixerOAuth import MixerOAuth
from threading import Event
import os

connected = Event()


class MixerChat(object):
    required_settings = {"client_id": {}, "client_secret": {'show': '*'}, "channel": {}}

    id_types = {}

    mixerApi = None
    user_id = None
    channel_id = None
    channel_url = None
    message_id = None

    def __init__(self, parent, config, script_handler):
        keys = self._auth(config)
        if keys is None:
            raise LookupError
        self.Parent = parent
        self.script_handler = script_handler
        self.OAuthKey = keys["access_token"]
        self.mixerApi = MixerApi(config, self.OAuthKey)
        self.config = config
        self.user_id = self.mixerApi.get_user_id()
        self.channel_id = self.mixerApi.get_channel_id()
        self.chat_url, self.authKey, self.roles, self.permissions = self.mixerApi.get_chat(self.channel_id)
        headers = {'Client-ID': self.config["client_id"]}
        self.mixer = websocket.WebSocketApp(self.chat_url, header=headers)
        self.mixer.on_message = self.on_message
        self.mixer.on_open = self.connect
        self.mixer.on_close = self.close
        self.mixer.on_error = self.error
        self.message_id = self.message_id_gen()

    def _auth(self, config):
        cert = os.path.join(os.path.dirname(__file__), '..', 'data', 'script_interface.crt')
        key = os.path.join(os.path.dirname(__file__), '..', 'data', 'script_interface.key')
        token_file = os.path.join(config['persistent_path'], "PyChatter", "token.json")
        moauth = MixerOAuth(config, cert, key, token_file)
        if not moauth.start():
            url = "https://127.0.0.1:5555/"
            webbrowser.open(url, new=1, autoraise=True)
        return moauth.stop()

    @staticmethod
    def message_id_gen():
        i = 0
        while True:
            i += 1
            i %= 100000
            yield i

    def close(self, _mixer):
        print('closed')

    def error(self, _mixer, err):
        print('error')
        print(err)

    # authenticate
    def connect(self, mixer):
        mixer.send(json.dumps(self.auth()))

    def on_message(self, _mixer, message):
        data = json.loads(message)
        type_ = data["type"]
        if type_ == 'reply':
            self.handle_reply(data, message)
        elif type_ == 'event':
            self.handle_event(data, message)

    def start(self):
        self.mixer.run_forever()
        print('never reach this')

    def auth(self):
        return self.create_method("auth", self.channel_id, self.user_id, self.authKey)

    def create_method(self, method, *args):
        id_ = self.message_id.next()
        self.id_types[id_] = method
        return {"type": "method", "method": method, "arguments": args, "id": id_}

    def send_msg(self, message):  # Send a chat message (if s is true, the message will append /me)
        if message.startswith('/me'):
            message = "/me " + message
        test = json.dumps(self.create_method("msg", message))
        connected.wait()
        self.mixer.send(test)

    def send_whisper(self, username, message):  # Send a chat message (if s is true, the message will append /me)
        test = json.dumps(self.create_method("whisper", username, message))
        connected.wait()
        self.mixer.send(test)
        print 'send whisper', username, message

    def get_channel_name(self):
        return self.config["channel"]

    def handle_reply(self, data, _message):
        if self.id_types[data["id"]] == "auth":
            if data.get("error", None) is not None:
                msg = "please authorize the correct user, you probably authorized you main account instead of your " \
                      "bot.\ndelete token.json and try again!"
                ctypes.windll.user32.MessageBoxA(0, msg, "wrong account authorized", 0)

    def handle_event(self, data, message):
        if data['event'] == "ChatMessage":
            if data["data"]["user_id"] not in self.Parent.viewer_list:
                userdata = {"username": data["data"]["user_name"],
                            "id": data["data"]["user_id"],
                            "roles": data["data"]["user_roles"]}
                self.Parent.add_viewer(userdata["id"], userdata)
            self.script_handler.add_data_to_process(
                self.script_handler.Data(data["data"]["user_id"], data["data"]["user_name"], data, message))
        if data['event'] == "UserJoin":
            self.Parent.add_viewer(data["data"]["id"], data["data"])
        if data['event'] == "UserLeave":
            del self.Parent.viewer_list[data["data"]["id"]]
        if data['event'] == "WelcomeEvent":
            for user_list in self.mixerApi.get_chatter_list(self.channel_id):
                for user in user_list:
                    user = {'id': user['userId'], 'username': user['username'], 'roles': user['userRoles']}
                    self.Parent.add_viewer(user['id'], user)
            connected.set()
        """else:
            print data"""

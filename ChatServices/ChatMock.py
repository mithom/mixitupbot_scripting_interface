import json
import traceback
from threading import Event


# noinspection PyMethodMayBeStatic
class ChatMock(object):
    required_settings = {}

    def __init__(self, parent, config, script_handler):
        self.stopped = Event()
        self.config = config
        self.Parent = parent
        self.script_handler = script_handler
        self.channel_id = config.get('username', 'developper')

    def auth(self):
        return True

    def send_msg(self, msg):
        print msg

    def send_whisper(self, target, msg):
        print '/w', target, msg

    def get_channel_name(self):
        return 'mi_thom'

    def start(self):
        messages = []
        last_user = None
        while not self.stopped.is_set():
            try:
                last_user = self._gather_input(last_user)
                if len(messages) > 0:
                    self.script_handler.add_data_to_process(messages.pop())
            except Exception as e:
                print e.message
                traceback.print_exc()

    def shutdown(self):
        self.stopped.set()

    def _gather_input(self, _last_user):
        user = raw_input("username? ")
        if len(user) > 0:
            self.Parent.add_viewer('id:' + user, {'username': user})
            json_data = {'data': {'message': {'message': [{'text': raw_input("msg: ")}]}}}
            self.script_handler.add_data_to_process(
                self.script_handler.Data("id:" + user, user, json_data, json.dumps(json_data)))
        elif _last_user is not None:
            json_data = {'data': {'message': {'message': [{'text': raw_input("msg: ")}]}}}
            self.script_handler.add_data_to_process(
                self.script_handler.Data("id:" + _last_user, _last_user, json_data, json.dumps(json_data)))
        return user or _last_user

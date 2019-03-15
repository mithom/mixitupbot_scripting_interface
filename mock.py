from chatbotInterface import Parent, Data
import importlib
import random
import sys
import json
from threading import Event

have_settings = Event()

class ChatMock(object):
    def send_msg(self, msg):
        print msg

    def send_whisper(self, target, msg):
        print '/w', target, msg

    def get_channel_name(self):
        return 'mi_thom'

class DataMock(object):
    def remove_points(self, user_id, username, amount):
        return True

    def add_points(self, user_id, username, amount):
        return True

    def add_points_all(self, points_dict):
        return []

    def get_points(self, user_id):
        return int(random.random()*max(Parent.ranks.values()+[500]))

    def get_hours(self, user_id):
        return int(random.random()*600)

def start(application):
    global script_name, folder

    Parent.ChatService = ChatMock()
    Parent.stream_online = True
    Parent.DataService = DataMock()

    def gather_input(last_user):
        user = raw_input("username? ")
        if len(user) > 0:
            Parent.add_viewer('id:' + user, {'username': user})
            jsond = {'data': {'message': {'message': [{'text': raw_input("msg: ")}]}}}
            messages.append(Data("id:" + user, user, jsond, json.dumps(jsond)))
        elif last_user is not None:
            jsond = {'data': {'message': {'message': [{'text': raw_input("msg: ")}]}}}
            messages.append(Data("id:" + last_user, last_user, jsond, json.dumps(jsond)))
        return user or last_user

    application.add_to_queue(application.show_script_manager)
    have_settings.wait()
    sys.path.append(folder)
    if not script_name.endswith("_StreamlabsSystem"):
        script_name += "_StreamlabsSystem"

    script = importlib.import_module(script_name)
    script.Parent = Parent

    script.Init()
    application.add_to_queue(application.add_loaded_script, application.ScriptManager.Script(
        script.ScriptName,
        script.Version,
        script.Creator,
        script.Description
    ))
    messages = []
    last_user = None
    while True:
        script.Tick()
        last_user = gather_input(last_user)
        if len(messages) > 0:
            script.Execute(messages.pop())


def shutdown():
    pass


def load_settings(application, **_):
    application.add_to_queue(application.ask_settings, script_name={})


def store_settings(settings):
    global script_name, folder
    script_name = settings['script_name']
    folder = settings.get('script_path', '')
    have_settings.set()


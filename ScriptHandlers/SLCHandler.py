import traceback
import binascii
import os
import sys
from threading import Thread, Event
from websocket_server import WebsocketServer
import re
import codecs
import Tkinter as Tk
import Queue
from ScriptInterfaces.SLCInterface import Parent, Data
import time
import json

ChatService = None
DataService = None

script_handler = None  # type: ScriptHandler


class ScriptHandler(object):
    Data = Data

    def __init__(self, application, script_path):
        self.application = application
        self.to_process = Queue.Queue()
        self.scripts = []
        self.server = None
        self.stopped = Event()
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

    def add_data_to_process(self, data):
        self.to_process.put(data)

    def start(self):
        self.server = Thread(target=self.scripts_loop)
        self.server.start()

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

    def unload(self):
        self.stopped.set()
        if self.server is not None:
            self.server.join()
            for script in self.scripts:
                try:
                    script.Unload()
                except AttributeError:
                    pass

    def scripts_loop(self):
        self.init()
        next_t = 0
        live_check = 0
        while not self.stopped.is_set():
            if time.time() < live_check:
                Parent.stream_online = Parent.ChatService.mixerApi.get_channel_online()
                live_check = time.time() + 120
            if not self.to_process.empty():
                data = self.to_process.get()
                for script in self.scripts:
                    try:
                        script.Execute(data)
                    except Exception as e:
                        print 'Error', e.message
                        traceback.print_exc()
                    if Parent.stop:
                        Parent.stop = False
                        break
                self.to_process.task_done()
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


def load_settings(application, _persistent_path, force_reload=False):
    global settings, script_path, persistent_path
    read_success = True
    persistent_path = _persistent_path
    if not force_reload:
        try:
            settings = read_settings()
            required_keys = (ChatService.required_settings.keys() + DataService.required_settings.keys())
            if all(required_key in settings.keys() for required_key in required_keys):
                script_path = settings['script_path']
            else:
                application.add_to_queue(application.ask_settings)
        except:
            read_success = False
            application.add_to_queue(application.ask_settings)
    else:
        read_success = False
        application.add_to_queue(application.ask_settings)
    if read_success:
        application.add_to_queue(application.finish_settings)


def store_settings(settings_):
    global settings, script_path
    script_path = settings_.get('script_path', '')
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


def start(application):
    global script_handler
    for thread in application.threads:
        if thread.name == 'store_settings':
            thread.join()
    settings['persistent_path'] = persistent_path
    script_handler = ScriptHandler(application, script_path)
    # noinspection PyCallingNonCallable
    Parent.ChatService = ChatService(Parent, settings, script_handler)
    if Parent.ChatService.auth():
        # noinspection PyCallingNonCallable
        Parent.DataService = DataService(Parent, settings)
        application.add_to_queue(application.show_script_manager)

        script_handler.start()
        Parent.ChatService.start()
    else:
        application.add_to_queue(application.back_to_settings_config)


def shutdown():
    # TODO: nog altijd niet volledig in orde (datamock met SLCHandler stopt niet)
    if script_handler is not None:
        script_handler.unload()
    if Parent.ChatService is not None:
        Parent.ChatService.shutdown()


file_path = os.path.dirname(__file__)

script_path = None  # type: str

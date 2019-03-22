from ScriptInterfaces.SLCInterface import Parent, Data
import importlib
import sys
from threading import Event
import Tkinter as Tk

have_settings = Event()

DataService = None
ChatService = None

script_name = None  # type: str
folder = None  # type: str
settings = None  # type: dict


class ScriptHandler(object):
    Data = Data
    stopped = Event()

    def __init__(self, application, script_path):
        global script_name
        sys.path.append(script_path)
        if not script_name.endswith("_StreamlabsSystem"):
            script_name += "_StreamlabsSystem"

        self.script = importlib.import_module(script_name)
        self.script.Parent = Parent

        self.script.Init()
        application.add_to_queue(application.add_loaded_script, application.ScriptManager.Script(
            self.script, load_script_settings(), ['Version', 'Creator', 'Description']
        ))

    def add_data_to_process(self, data):
        self.script.Tick()
        self.script.Execute(data)


def start(application):
    global folder, settings
    settings['persistent_path'] = persistent_path
    have_settings.wait()
    application.add_to_queue(application.show_script_manager)
    script_handler = ScriptHandler(application, folder)
    # noinspection PyCallingNonCallable
    Parent.ChatService = ChatService(Parent, settings, script_handler)
    Parent.stream_online = True
    # noinspection PyCallingNonCallable
    Parent.DataService = DataService(Parent, settings)

    Parent.ChatService.start()


def load_script_settings():
    return Tk.Button(text='test')  # created at root lvl


def save_script_settings(_settings_frame):
    pass


def shutdown():
    ScriptHandler.stopped.set()


def load_settings(application, _persistent_path, **_):
    global persistent_path
    persistent_path = _persistent_path
    application.add_to_queue(application.ask_settings, script_name={})


def store_settings(_settings):
    global script_name, folder, settings
    settings = _settings
    script_name = _settings['script_name']
    folder = _settings.get('script_path', '')
    have_settings.set()

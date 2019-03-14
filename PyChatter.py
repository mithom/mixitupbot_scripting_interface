"""
This file will be the running program. It will start up in several steps:
1. check and install availability of packages (don't vendor them anymore) - loading window
2. open a selection box for which streaming server to use - default to last one used - option to skip next time
3. open a selection box for which chatbot to support - default to last one used - option to skip next time
4. ask credentials for all required logins - option to remember for next time -> auto login + prompt if failed
5. start the bot.
"""
import Tkinter as Tk
import mxpy
import twpy
import threading
import ttk
from Queue import Queue
import tkFont

STORE_SETTINGS = 'store_settings'


# noinspection PyAttributeOutsideInit
class StartUpApplication(Tk.Frame):
    services = {'Mixer': mxpy, 'Twitch': twpy}

    class AskSettings(Tk.Frame):
        def __init__(self, master, **kwargs):
            Tk.Frame.__init__(self, master)
            self.items = {}
            self.title = 'Settings'

            i = 0
            for key, settings in kwargs.iteritems():
                label = Tk.Label(self, text=key, justify=Tk.RIGHT)
                label.grid(pady=5, padx=(10, 15), row=i, column=0)

                entry = Tk.Entry(self, text=key, justify=Tk.LEFT, **settings)
                entry.grid(pady=5, padx=(15, 10), row=i, column=1)
                i += 1
                self.items[label] = entry

    class ProgressBar(Tk.Frame):
        def __init__(self, master, title=''):
            Tk.Frame.__init__(self, master)
            self.title = title
            self.progressBar = ttk.Progressbar(self, mode='indeterminate')
            self.progressBar.start()
            self.progressBar.pack()

    class ServiceSelection(Tk.Frame):
        def __init__(self, master):
            Tk.Frame.__init__(self, master)
            self.title = 'Select Streaming Service'
            self.selectedService = Tk.StringVar(self)
            self.selectedService.set('Mixer')
            self.serviceSelection = Tk.OptionMenu(self, self.selectedService, *StartUpApplication.services.keys())
            self.serviceSelection.pack(pady=(20, 40))

    class ScriptManager(Tk.Frame):
        def __init__(self, master):
            Tk.Frame.__init__(self, master)
            self.title = 'Active Scripts'
            self.scripts = []
            self.headers = {}
            self.next_row = 1  # 0 is the header row

            self.script_content = Tk.Frame(master=self)
            self.script_content.pack(padx=10, pady=10, fill=Tk.BOTH)

            self.settings_content = Tk.Frame(master=self, relief=Tk.RAISED, borderwidth=1)
            self.settings_content.pack(padx=10, pady=10, side=Tk.LEFT, fill=Tk.Y)

            for header in ['name', 'version', 'author', 'description']:
                self.add_header(header)
            self.add_script(self.Script('testScript', '0.0.1', 'mi_thom', 'a fake script'))

        class Script:
            def __init__(self, name, version, author, description, **kwargs):
                self.name = name
                self.version = version
                self.author = author
                self.description = description
                self.kwargs = kwargs

        class ScriptRow:
            def __init__(self, master, script, row):
                self.script = script
                a = Tk.Label(master, text=script.name, relief=Tk.FLAT, bg="lightgrey")
                b = Tk.Label(master, text=script.version, relief=Tk.FLAT, bg="lightgrey")
                c = Tk.Label(master, text=script.author, relief=Tk.FLAT, bg="lightgrey")
                d = Tk.Label(master, text=script.description, relief=Tk.FLAT, bg="lightgrey")
                a.grid(row=row, column=0, sticky=Tk.E + Tk.W)
                b.grid(row=row, column=1, sticky=Tk.E + Tk.W)
                c.grid(row=row, column=2, sticky=Tk.E + Tk.W)
                d.grid(row=row, column=3, sticky=Tk.E + Tk.W)
                self.labels = [a, b, c, d]
                for header, field in script.kwargs.iteritems():
                    label = Tk.Label(master, text=field, relief=Tk.FLAT, bg="lightgrey")
                    label.grid(row=row, column=self.master.parent.get_header_col(header), sticky=Tk.E + Tk.W)
                    self.labels.append(label)
                for label in self.labels:
                    label.bind('<Enter>', self.highlight_row)
                    label.bind('<Leave>', self.default_row)

            def highlight_row(self, event):
                for label in self.labels:
                    label.config(bg="grey")

            def default_row(self, event):
                for label in self.labels:
                    label.config(bg="lightgrey")

        def get_header_col(self, header):
            col = self.headers.get(header, None)
            if col is None:
                return self.add_header(header)
            return col

        def add_header(self, header):
            col = len(self.headers)
            label = Tk.Label(self.script_content, text=header, font=tkFont.Font(weight=tkFont.BOLD))
            label.grid(row=0, column=col)
            self.headers[header] = len(self.headers)
            return col

        def add_script(self, script):
            if isinstance(script, self.Script):
                script_row = self.ScriptRow(self.script_content, script, self.next_row)
                ttk.Separator(self.script_content, orient=Tk.HORIZONTAL).grid(
                    row=self.next_row + 1, column=0, sticky=Tk.E + Tk.W,
                    columnspan=self.script_content.grid_size()[0],pady=2
                )
                self.scripts.append(script_row)
                self.next_row += 2

    def __init__(self, master=None):
        Tk.Frame.__init__(self, master)

        self.threads = []
        self.queue = Queue()
        self.last_kwargs = {}
        self.service = None
        self._frame = None

        # self.pack(fill=Tk.BOTH)
        self.pack(fill=Tk.BOTH, expand=1)
        self.master.title('ChatbotApplication')

        self.title_place = Tk.Frame(master=self, relief=Tk.FLAT)
        self.title_place.grid(row=0, column=0, columnspan=4, sticky=Tk.NSEW)
        self._title = self._title = Tk.Label(self.title_place, font=tkFont.Font(weight=tkFont.BOLD, underline=True),
                                             justify=Tk.CENTER)
        self.test = ttk.Separator(self, orient=Tk.HORIZONTAL)
        self.test.grid(row=1, column=0, columnspan=4, pady=2, sticky=Tk.EW)

        self.content = Tk.Frame(master=self, relief=Tk.RAISED, borderwidth=1)
        self.content.grid(row=2, column=0, columnspan=4, padx=10, pady=10, sticky=Tk.NSEW)

        # create the buttons
        self.continueButton = Tk.Button(self, text='Continue')
        self.previousButton = Tk.Button(self, text='Previous')
        self.quitButton = Tk.Button(self, text='Close', command=self.quit, anchor=Tk.SE)

        # TODO: change to place to stick to bottom right corner
        self.quitButton.grid(row=3, column=3, padx=5, pady=5, sticky=Tk.SE)
        self.previousButton.grid(row=3, column=2, padx=5, pady=5, sticky=Tk.SE)
        self.continueButton.grid(row=3, column=1, padx=5, pady=5, sticky=Tk.SE)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.select_service()
        self.after(100, self.periodic_queue_process)

        # master.pack()
        # master.geometry(
        #     '300x150+' + str(master.winfo_screenwidth() / 2 - 150) + '+' + str(master.winfo_screenheight() / 2 - 75))

    def periodic_queue_process(self):
        if not self.queue.empty():
            func = self.queue.get()
            func[0](*func[1], **func[2])
            self.queue.task_done()
        self.after(100, self.periodic_queue_process)

    def add_to_queue(self, func, *args, **kwargs):
        print 'adding to queue'
        self.queue.put([func, args, kwargs])

    def switch_frame(self, frame_class, *args, **kwargs):
        """Destroys current frame and replaces it with a new one."""
        new_frame = frame_class(self.content, *args, **kwargs)
        if self._frame is not None:
            self._frame.destroy()
        if hasattr(new_frame, 'title'):
            self._title.config(text=new_frame.title)
            self._title.pack()
        else:
            self._title.pack_forget()
            # self.title_place.config(height=0, pady=0)
            # self.title_place.pack_configure(ipady=0, pady=0)
        self._frame = new_frame
        self._frame.pack(fill=Tk.BOTH, expand=1)

    def select_service(self):
        # self.switch_frame(self.ServiceSelection)
        self.switch_frame(self.ServiceSelection)
        self.continueButton.config(command=self.config_service, state=Tk.ACTIVE)
        self.previousButton.config(state=Tk.DISABLED, text='Previous')

    def config_service(self, force_reload=False):
        self.continueButton.configure(state=Tk.DISABLED)
        if isinstance(self._frame, self.ServiceSelection):
            self.service = self.services[self._frame.selectedService.get()]
        func = self.service.load_settings
        kwargs = {'force_reload': force_reload}
        # noinspection PyTypeChecker
        fun_thread = threading.Thread(target=func, name=self.service.__name__, args=(self,), kwargs=kwargs)
        self.threads.append(fun_thread)
        self.previousButton.configure(state=Tk.ACTIVE, command=self.select_service, text='Cancel')
        self.switch_frame(self.ProgressBar, 'Verifying Authentication Settings')
        # make sure everything is initialised before thread starts
        fun_thread.start()

    def back_to_settings_config(self):
        if len(self.last_kwargs) > 0:
            self.ask_settings(**self.last_kwargs)
        else:
            self.config_service(force_reload=True)

    def ask_settings(self, **kwargs):
        if not isinstance(self._frame, self.ProgressBar):
            raise RuntimeError('ask_settings was called, but _frame was not ProgressBar')
        self.last_kwargs = kwargs
        self.switch_frame(self.AskSettings, **kwargs)
        self.continueButton.config(state=Tk.ACTIVE, command=self.confirm_settings)
        self.previousButton.configure(state=Tk.ACTIVE, command=self.select_service, text='Previous')

    def confirm_settings(self):
        func = self.service.store_settings
        args = {}
        if not isinstance(self._frame, self.AskSettings):
            raise RuntimeError('self._frame was not of class self.AskSettings')
        for label, entry in self._frame.items.iteritems():
            args[label.cget('text')] = entry.get()
        fun_thread = threading.Thread(target=func, args=(args,), name=STORE_SETTINGS)
        self.threads.append(fun_thread)
        fun_thread.start()
        self.finish_settings()

    def finish_settings(self):
        if not (isinstance(self._frame, self.AskSettings) or isinstance(self._frame, self.ProgressBar)):
            raise RuntimeError('finish_settings has been called while not working on settings')
        func = self.service.start
        fun_thread = threading.Thread(target=func, name='service_start', args=(self,))
        self.threads.append(fun_thread)
        fun_thread.start()
        self.switch_frame(self.ProgressBar, 'Authenticating & Loading Scripts')

        self.continueButton.config(state=Tk.DISABLED)
        self.previousButton.config(command=self.back_to_settings_config, text='Cancel')

    def show_script_manager(self):
        self.switch_frame(self.ScriptManager)

    def add_loaded_script(self, script):
        if not isinstance(self._frame, self.ScriptManager):
            raise RuntimeError("can't add scripts before showing the ScriptManager")
        self._frame.add_script(script)


if __name__ == "__main__":
    root = Tk.Tk()
    root.resizable(0, 0)
    app = StartUpApplication(master=root)
    try:
        app.mainloop()
    finally:
        root.destroy()
    print 'initial thread ended'

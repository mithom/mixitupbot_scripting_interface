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
import Queue

STORE_SETTINGS = 'store_settings'


# noinspection PyAttributeOutsideInit
class StartUpApplication(Tk.Frame):
    services = {'Mixer': mxpy, 'Twitch': twpy}

    class AskSettings(Tk.Frame):
        def __init__(self, master, **kwargs):
            Tk.Frame.__init__(self, master)
            self.items = {}

            i = 0
            for key, settings in kwargs.iteritems():
                label = Tk.Label(self, text=key, justify=Tk.RIGHT)
                label.grid(pady=5, padx=(10, 15), row=i, column=0)

                entry = Tk.Entry(self, text=key, justify=Tk.LEFT, **settings)
                entry.grid(pady=5, padx=(15, 10), row=i, column=1)
                i += 1
                self.items[label] = entry

    class ProgressBar(Tk.Frame):
        def __init__(self, master):
            Tk.Frame.__init__(self, master)
            self.progressBar = ttk.Progressbar(self, mode='indeterminate')
            self.progressBar.start()
            self.progressBar.pack()

    class ServiceSelection(Tk.Frame):
        def __init__(self, master):
            Tk.Frame.__init__(self, master)
            self.selectedService = Tk.StringVar(self)
            self.selectedService.set('Mixer')
            self.serviceSelection = Tk.OptionMenu(self, self.selectedService, *StartUpApplication.services.keys())
            self.serviceSelection.pack(pady=(20, 40))

    def __init__(self, master=None):
        Tk.Frame.__init__(self, master)

        self.threads = []
        self.queue = []
        self.last_kwargs = {}
        self.service = None
        self._frame = None

        self.pack(fill=Tk.BOTH)
        self.master.title('ChatbotApplication')

        self.content = Tk.Frame(master=self, relief=Tk.RAISED, borderwidth=1)
        self.content.pack(padx=10, pady=10, fill=Tk.BOTH)

        # create the buttons
        self.continueButton = Tk.Button(self, text='Continue')
        self.previousButton = Tk.Button(self, text='Previous')
        self.quitButton = Tk.Button(self, text='Close', command=self.quit)

        self.quitButton.pack(side=Tk.RIGHT, padx=5, pady=5)
        self.previousButton.pack(side=Tk.RIGHT, padx=5, pady=5)
        self.continueButton.pack(side=Tk.RIGHT, padx=5, pady=5)

        self.select_service()
        self.after(100, self.periodic_queue_process)


        # master.pack()
        # master.geometry(
        #     '300x150+' + str(master.winfo_screenwidth() / 2 - 150) + '+' + str(master.winfo_screenheight() / 2 - 75))

    def periodic_queue_process(self):
        if len(self.queue) > 0:
            func = self.queue.pop(0)
            func[0](*func[1], **func[2])
        self.after(100, self.periodic_queue_process)

    def add_to_queue(self, func, *args, **kwargs):
        print 'adding to queue'
        self.queue.append([func, args, kwargs])

    def switch_frame(self, frame_class, **kwargs):
        """Destroys current frame and replaces it with a new one."""
        new_frame = frame_class(self.content, **kwargs)
        if self._frame is not None:
            self._frame.destroy()
        self._frame = new_frame
        self._frame.pack()

    def select_service(self):
        self.switch_frame(self.ServiceSelection)
        self.continueButton.config(command=self.config_service, state=Tk.ACTIVE)
        self.previousButton.config(state=Tk.DISABLED)

    def config_service(self, force_reload=False):
        self.continueButton.configure(state=Tk.DISABLED)
        if isinstance(self._frame, self.ServiceSelection):
            self.service = self.services[self._frame.selectedService.get()]
        func = self.service.load_settings
        kwargs = {'force_reload': force_reload}
        # noinspection PyTypeChecker
        fun_thread = threading.Thread(target=func, name=self.service.__name__, args=(self,), kwargs=kwargs)
        self.threads.append(fun_thread)
        self.previousButton.configure(state=Tk.ACTIVE, command=self.select_service)
        self.switch_frame(self.ProgressBar)
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
        self.previousButton.configure(state=Tk.ACTIVE, command=self.select_service)

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
        self.switch_frame(self.ProgressBar)

        self.continueButton.config(state=Tk.DISABLED)
        self.previousButton.config(command=self.back_to_settings_config)

    def close_window(self):
        self.quit()


if __name__ == "__main__":
    root = Tk.Tk()
    app = StartUpApplication(master=root)
    try:
        app.mainloop()
    finally:
        root.destroy()
    print 'initial thread ended'

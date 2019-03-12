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


INIT = 'INITIALIZING'
SERVICE = 'SERVICE SELECTION'
READ_SETTINGS = 'READING SETTINGS'
FORM_SETTINGS = 'SETTINGS FORM'
DONE = 'DONE'


# noinspection PyAttributeOutsideInit
class StartUpApplication(Tk.Frame):
    services = {'Mixer': mxpy, 'Twitch': twpy}

    def __init__(self, master=None):
        Tk.Frame.__init__(self, master)

        self.threads = []
        self.state = INIT
        print self.state
        self.service = None

        self.pack(fill=Tk.BOTH)
        self.master.title('ChatbotApplication')

        self.content = Tk.Frame(master=self, relief=Tk.RAISED, borderwidth=1)
        self.content.pack(padx=10, pady=10, fill=Tk.BOTH)
        # create a dropdown select box
        self.selectedService = Tk.StringVar(self)
        self.selectedService.set('Mixer')
        self.serviceSelection = Tk.OptionMenu(self.content, self.selectedService, *self.services.keys())
        self.serviceSelection.pack(pady=(20, 40))

        # create the buttons
        self.continueButton = Tk.Button(self, text='Continue', command=self.config_service)
        self.previousButton = Tk.Button(self, text='Previous', state=Tk.DISABLED)
        self.quitButton = Tk.Button(self, text='Close', command=self.quit)

        self.quitButton.pack(side=Tk.RIGHT, padx=5, pady=5)
        self.previousButton.pack(side=Tk.RIGHT, padx=5, pady=5)
        self.continueButton.pack(side=Tk.RIGHT, padx=5, pady=5)

        master.geometry(
            '300x150+' + str(master.winfo_screenwidth() / 2 - 150) + '+' + str(master.winfo_screenheight() / 2 - 75))
        self.state = SERVICE
        print self.state

    def config_service(self):
        self.state = READ_SETTINGS
        print self.state
        self.continueButton.configure(state=Tk.DISABLED)
        self.service = self.services[self.selectedService.get()]
        func = self.service.load_settings
        # noinspection PyTypeChecker
        fun_thread = threading.Thread(target=func, name=self.selectedService.get(), args=(self,))
        self.threads.append(fun_thread)
        self.serviceSelection.destroy()
        self.previousButton.configure(state=Tk.ACTIVE, command=self.back_to_service_selection)
        self.progressBar = ttk.Progressbar(self.content, mode='indeterminate')
        self.progressBar.start()
        self.progressBar.pack()
        # make sure everything is initialised before thread starts
        fun_thread.start()

    def back_to_service_selection(self):
        pass

    def ask_settings(self, **kwargs):
        if self.state != READ_SETTINGS:
            print 'error state:', self.state
            raise RuntimeError('ask_settings was called, but state was not READ_SETTINGS')
        self.state = FORM_SETTINGS
        print self.state
        self.progressBar.destroy()
        self.items = {}

        for key, settings in kwargs.iteritems():
            label = Tk.Label(self.content, text=key)
            label.pack(pady=5, padx=(10, 15), side=Tk.TOP, justify=Tk.RIGHT)

            entry = Tk.Entry(self.content, text=key, **settings)
            entry.pack(pady=5, padx=(15, 10), side=Tk.RIGHT, justify=Tk.LEFT)
            self.items[label] = entry
        self.continueButton.config(state=Tk.ACTIVE, command=self.confirm_settings)

    def confirm_settings(self):
        func = self.service.store_settings
        fun_thread = threading.Thread(target=func, args=({},), name='save_settings')
        fun_thread.start()
        self.threads.append(fun_thread)
        self.finish_settings()

    def finish_settings(self):
        if self.state not in [READ_SETTINGS, FORM_SETTINGS]:
            raise RuntimeError('finish_settings has been called while not working on settings')
        self.state = DONE
        print self.state
        root.quit()
        for thread in self.threads:
            if thread != threading.current_thread():
                thread.join()
        self.threads = []
        self.service.start()


if __name__ == "__main__":
    root = Tk.Tk()
    app = StartUpApplication(master=root)
    try:
        app.mainloop()
    finally:
        root.destroy()
        for thread in app.threads:
            thread.join()
else:
    raise ImportError(
        "this file should not be imported, only executed, extendable code will be in the provided packages")

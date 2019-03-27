from requests_oauthlib import OAuth2Session
from flask import Flask, request, redirect
from threading import Thread, Event
import os
import json
import codecs
import requests

app = Flask(__name__)

token = None
server = None


class MixerOAuth(object):
    authorization_base_url = 'https://mixer.com/oauth/authorize'
    token_url = 'https://mixer.com/api/v1/oauth/token'
    instance = None

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            obj = object.__new__(cls)
            cls.instance = obj
        return cls.instance

    def __init__(self, config, cert, key, token_file):
        self.config = config
        self.cert = cert
        self.key = key
        self.token_file = token_file

        self.is_running = Event()
        self.stopped = Event()
        self.instance = self

    @staticmethod
    @app.route("/")
    def demo():
        global state
        scope = ["chat:chat", "chat:connect", "chat:bypass_slowchat", "chat:bypass_catbot", "chat:bypass_filter",
                 "chat:bypass_links", "chat:change_ban", "chat:change_role", "chat:clear_messages",
                 "chat:giveaway_start", "chat:poll_start", "chat:poll_vote", "chat:purge",
                 "chat:timeout", "chat:view_deleted", "chat:whisper", "resource:find:self"]
        mixer = OAuth2Session(MixerOAuth.instance.config["client_id"], redirect_uri='https://127.0.0.1:5555/callback',
                              scope=scope)
        auth_url, state = mixer.authorization_url(MixerOAuth.authorization_base_url)
        return redirect(auth_url)

    @staticmethod
    @app.route("/callback", methods=["GET"])
    def callback():
        global token, state
        mixer = OAuth2Session(MixerOAuth.instance.config["client_id"], state=state,
                              redirect_uri='https://127.0.0.1:5555/callback')
        token = mixer.fetch_token(MixerOAuth.instance.token_url,
                                  client_secret=MixerOAuth.instance.config["client_secret"],
                                  authorization_response=request.url, verify=False)
        MixerOAuth.instance.shutdown_server()
        return "you can now close this window"

    def start(self):
        global server, token
        try:
            with codecs.open(self.token_file, encoding="utf-8-sig", mode="r") as f:
                token = json.load(f, encoding="utf-8")
                self.refresh_acces_token(token)
            return True
        except:
            print "could not retrieve refresh token - start OAuth process"
            token = None
            app.secret_key = os.urandom(24)
            server = Thread(target=app.run,
                            kwargs={"ssl_context": (self.cert, self.key), "port": 5555, "host": "127.0.0.1"})
            server.daemon = True
            if not self.stopped.is_set():
                self.is_running.set()
                server.start()
            return False

    @staticmethod
    @app.route("/shutdown", methods=["GET"])
    def shutdown_server():
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()
        MixerOAuth.instance.is_running.clear()
        print 'Oauth server has been stopped'
        return 'Oauth server has been stopped'

    def refresh_acces_token(self, token_dict):
        global token
        print "refreshing"
        mixer = OAuth2Session(self.config["client_id"])
        token = mixer.refresh_token(self.token_url, refresh_token=token_dict["refresh_token"],
                                    client_secret=self.config["client_secret"], client_id=self.config["client_id"],
                                    verify=False)

    def stop_if_running(self):
        self.stopped.set()
        if self.is_running.is_set():
            requests.get('https://127.0.0.1:5555/shutdown', verify=False)

    def stop(self):
        if server is not None and server.isAlive():
            server.join()
        try:
            with codecs.open(self.token_file, encoding="utf-8-sig", mode="w+") as f:
                json.dump(token, f, encoding="utf-8-sig", ensure_ascii=False)
        finally:
            return token

from requests_oauthlib import OAuth2Session
from flask import Flask, request, redirect, session, url_for
from threading import Thread
import os
import json
import codecs

app = Flask(__name__)

authorization_base_url = 'https://mixer.com/oauth/authorize'
token_url = 'https://mixer.com/api/v1/oauth/token'

config = None
token = None
server = None

token_file = os.path.join(os.path.dirname(__file__),"token.json")


@app.route("/")
def demo():
    global state
    scope = ["chat:chat", "chat:connect", "chat:bypass_slowchat", "chat:bypass_catbot", "chat:bypass_filter",
             "chat:bypass_links", "chat:change_ban", "chat:change_role", "chat:clear_messages",
             "chat:giveaway_start", "chat:poll_start", "chat:poll_vote", "chat:purge",
             "chat:timeout", "chat:view_deleted", "chat:whisper", "resource:find:self"]
    mixer = OAuth2Session(config["client_id"], redirect_uri='https://127.0.0.1:5555/callback', scope=scope)
    auth_url, state = mixer.authorization_url(authorization_base_url)
    return redirect(auth_url)


@app.route("/callback", methods=["GET"])
def callback():
    global token, state
    mixer = OAuth2Session(config["client_id"], state=state, redirect_uri='https://127.0.0.1:5555/callback')
    token = mixer.fetch_token(token_url, client_secret=config["client_secret"], authorization_response=request.url)
    shutdown_server()
    return "you can now close this window"


def start():
    global server, token
    try:
        with codecs.open(token_file, encoding="utf-8-sig", mode="r") as f:
            token = json.load(f, encoding="utf-8")
        refresh_acces_token(token)
        return True
    except:
        print "error"
        app.secret_key = os.urandom(24)
        server = Thread(target=app.run, kwargs={"ssl_context": "adhoc", "port": 5555, "host": "127.0.0.1"})
        server.daemon = True
        server.start()
        return False


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


def refresh_acces_token(token_dict):
    global token
    print "refreshing"
    mixer = OAuth2Session(config["client_id"])
    token = mixer.refresh_token(token_url, refresh_token=token_dict["refresh_token"],
                                client_secret=config["client_secret"], client_id=config["client_id"])


def stop():
    if server is not None:
        server.join()
    try:
        with codecs.open(token_file, encoding="utf-8-sig", mode="w+") as f:
            json.dump(token, f, encoding="utf-8-sig", ensure_ascii=False)
    finally:
        return token

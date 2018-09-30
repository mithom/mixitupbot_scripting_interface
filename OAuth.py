from requests_oauthlib import OAuth2Session
from flask import Flask, request, redirect, session, url_for
from threading import Thread
import os

app = Flask(__name__)

authorization_base_url = 'https://mixer.com/oauth/authorize'
token_url = 'https://mixer.com/api/v1/oauth/token'

config = None
token = None


@app.route("/")
def demo():
    global state
    scope = ["chat:chat", "chat:connect", "chat:bypass_slowchat"]
    mixer = OAuth2Session(config["client_id"], redirect_uri='https://localhost:5555/callback', scope=scope)
    auth_url, state = mixer.authorization_url(authorization_base_url)
    return redirect(auth_url)


@app.route("/callback", methods=["GET"])
def callback():
    global token, state
    mixer = OAuth2Session(config["client_id"], state=state, redirect_uri='https://localhost:5555/callback')
    token = mixer.fetch_token(token_url, client_secret=config["client_secret"], authorization_response=request.url)
    shutdown_server()
    return "you can now close this window"


def start():
    global server
    app.secret_key = os.urandom(24)
    server = Thread(target=app.run, kwargs={"ssl_context": "adhoc", "port": 5555, "host": "0.0.0.0"})
    server.start()


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


def stop():
    server.join()
    return token

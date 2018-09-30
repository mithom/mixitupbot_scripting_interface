import database as db
import json
from lib import websocket


def init():
    db.create_table_if_not_exists()


def read_settings():
    # Open JSON settings file
    with open("settingsT.json") as data:
        return json.load(data)


class TwitchChat:
    def __init__(self):
        init()

        self.twitch = websocket.WebSocketApp("wss://irc-ws.chat.twitch.tv:443")
        self.twitch.on_message = self.on_message
        self.twitch.on_open = self.connect
        self.twitch.on_close = self.close
        self.twitch.on_error = self.error
        print('config done')

    def start(self):
        print("started")
        self.twitch.run_forever()

    @staticmethod
    def close():
        print('closed')

    @staticmethod
    def error(err):
        print('error')
        print(err)

    # authenticate
    @staticmethod
    def connect(twitch):
        print('hallo')
        twitch.send("CAP REQ :twitch.tv/membership\r\n".encode())
        twitch.send("CAP REQ :twitch.tv/commands\r\n".encode())
        twitch.send("CAP REQ :twitch.tv/tags\r\n".encode())
        twitch.send(("PASS " + opt["authkey"] + "\r\n").encode())
        twitch.send(("NICK " + opt["username"] + "\r\n").encode())
        twitch.send(("JOIN #" + opt["channel"] + "\r\n").encode())
        print('connected')

    # Chat
    @staticmethod
    def on_message(twitch, message):
        response = TwitchChat.infof(message, twitch)
        print(response)
        # We do not want to return this data as it is an IRC message from Twitch or JTV.
        if response["display-name"] == "twitch" or response["display-name"].lower() == opt["username"]:
            dont_do_anything = 1

        # This is a command (Do something with it.).
        elif response["message"].startswith("!addcom"):
            if response["user-type"] == "mod" or "broadcaster" in response["@badges"]:
                # Split it 3 times ("!addcom", "user-level", "!command", "response")
                spliced = response["message"].split(" ", 3)
                level = spliced[1]
                command = spliced[2]
                response = spliced[3]

                # Don't allow hard-coded commands to be added

                if not (command == "!addcom" or command == "!delcom" or command == "!commands"):
                    returned = db.add_command(command, response, level)

        # This is a command (Do something with it.).
        elif response["message"].startswith("!delcom"):
            if response["user-type"] == "mod":
                spliced = response["message"].split(" ", 1)
                pre = spliced[1]
                post = pre.split("\r")
                command = post[0]
                returned = db.remove_command(command)

        elif response["message"] == "!commands":
            returned = db.get_command_list()
            if returned is None:
                TwitchChat.send(twitch, "There are currently no commands set for this channel.")
            else:
                TwitchChat.send(twitch, returned)

        # This is a command (Do something with it.).
        elif response["message"].startswith("!"):
            spliced = response["message"].split("\r")
            command = spliced[0]
            returned = db.get_command(command)
            if returned != [] and response["user-type"] != returned[0][2]:
                if response["user-type"] == "mod":
                    TwitchChat.send(twitch, returned[0][1])
            else:
                TwitchChat.send(twitch, returned[0][1])
        else:
            pass  # TODO: pass to scripts

    # Bot events
    @staticmethod
    def send(twitch, message, sp=None):  # Send a chat message (if s is true, the message will append /me)
        if sp is None:
            construct = "PRIVMSG #" + opt["channel"] + " :" + message + "\r\n"
            twitch.send(construct.encode())
        else:
            construct = "PRIVMSG #" + opt["channel"] + " :/me " + message + "\r\n"
            twitch.send(construct.encode())

    @staticmethod
    def afk(twitch):  # This responds to Twitch's afk PING requests.
        construct = "PONG :tmi.twitch.tv\r\n"
        twitch.send(construct.encode())

        # Message information, returns attributes.

    @staticmethod
    def infof(uin, twitch):
        if uin.startswith("@badges"):
            info = {}  # This will be returned eventually.

            input_split = uin.split(" ", 1)
            input_tags = input_split[0]
            input_other = input_split[1]
            input_message = input_split[1].split(":")

            # This is a check to stop these messages from being sent to chat.
            if ":jtv MODE" in uin or "GLOBALUSERSTATE" in uin or "USERSTATE" in uin or "ROOMSTATE" in uin or \
                    "JOIN #" in uin or "tmi.twitch.tv 353" in uin or "tmi.twitch.tv 366" in uin:
                info["display-name"] = "twitch"

            elif uin.startswith("PING"):
                TwitchChat.afk(twitch)

            # Gets the message sent and the channel it was sent from.
            elif len(input_message) == 3:
                msg_init = input_message[2]
                message = msg_init.split("\r")[0]
                info["message"] = message

                if message.startswith("ACTION"):
                    info["action-message"] = True

                else:
                    info["action-message"] = False

                chan_init = input_message[1]
                str_plit = chan_init.split(" ")
                chan_tear = str_plit[2].split("#")
                channel = chan_tear[1]
                info["channel"] = channel

            # Splits remaining tags into the dictionary so they can all be called.
            tags = input_tags.split(";")
            for i, t in enumerate(tags):
                obj = t.split("=")
                obj_title = obj[0]
                obj_value = obj[1]
                info[obj_title] = obj_value

                if i >= len(tags) - 1:
                    if info["user-type"] == "":
                        info["user-type"] = "all"
                        return info
                    else:
                        return info

        else:
            info = {}  # This gets returned.
            # Returns the display-name twitch as all of the messages are from the IRC connection. Dealt with later.
            input_split = uin.split(" ")

            info["message"] = ""
            info["channel"] = ""
            info["sent-ts"] = ""
            info["user-id"] = ""
            info["@badges"] = ""
            info["display-name"] = "twitch"
            info["mod"] = "0"
            info["subscriber"] = "0"
            info["user-type"] = ""

            return info


if __name__ == "__main__":
    opt = read_settings()
    bot = TwitchChat()
    bot.start()

import sqlite3

db = sqlite3.connect("database.db")
c = db.cursor()


# This creates the commands table if it does not exist
def create_table_if_not_exists():
    c.execute("CREATE TABLE IF NOT EXISTS Commands(command TEXT, response TEXT, level TEXT)")


# query adds command/response to the commands table
def add_command(command, response, level):
    try:
        c.execute("INSERT INTO Commands (command, response, level) VALUES (?, ?, ?)", (command, response, level))
        db.commit()
        print('succesfully added')
        return 1
    except sqlite3.OperationalError as e:
        print('failed to add command')
        return e


# query removes command/response to the commands table
def remove_command(command):
    try:
        c.execute("DELETE FROM Commands WHERE command=?", (command,))
        db.commit()
        return 1
    except sqlite3.OperationalError as e:
        return e


# query fetches response on request of a command
def get_command(command):
    c.execute("SELECT * FROM Commands WHERE command = ?", (command,))
    response = c.fetchall()
    if response is not None:
        return response
    else:
        return 0


# query fetches list off all of the commands available
def get_command_list():
    x = "Commands: "
    c.execute("SELECT * FROM Commands")
    d = c.fetchall()
    if d is None:
        return None
    else:
        for index, com in enumerate(d):
            command = com[0]
            level = com[2]
            if index >= len(d) - 1:
                x = x + command + " - " + level
                return x
            else:
                x = x + command + " - " + level + "  |  "

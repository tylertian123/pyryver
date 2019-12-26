import pyryver
from quicklatex_render import ql_render
import time

ryver = pyryver.Ryver("arctos6135")

forums = ryver.get_cached_chats(pyryver.TYPE_FORUM)
teams = ryver.get_cached_chats(pyryver.TYPE_TEAM)

chat = pyryver.get_obj_by_field(forums, pyryver.FIELD_NAME, "Test")

creator = None

# Current admins are: @tylertian, @moeez, @michalkdavis, and @Julia
admins = set([1311906, 1605991, 1108002, 1108009])

help_text = """
Command set:
  - `@latexbot render <formula>` - Renders LaTeX.
  - `@latexbot help` - Print a help message.
  - `@latexbot ping` - I will respond with "Pong" if I'm here.
  - `@latexbot moveToForum <forum>` - Move me to another forum.
  - `@latexbot moveToTeam <team>` - Move me to another team.
  - `@latexbot updateChats` - Updates the list of forums/teams. Only Bot Admins can do this.
"""

print("LaTeX Bot is running!")
chat.send_message("""
LaTeX Bot v0.1.0 is online! Note that to reduce load, I only check messages once per 3 seconds or more!
""" + help_text, creator)

def _render(msg: pyryver.Message, formula: str):
    global chat, creator
    if len(formula) > 0:
        img = ql_render(formula)
        chat.send_message(f"![{formula}]({img})", creator)
    else:
        chat.send_message("Formula can't be empty.", creator)

def _movetoforum(msg: pyryver.Message, name: str):
    global chat, creator, forums
    if len(name) > 0:
        new_forum = pyryver.get_obj_by_field(forums, pyryver.FIELD_NAME, name)
        if not new_forum:
            chat.send_message("Forum not found.", creator)
        else:
            chat.send_message(f"LaTeX Bot has moved to {name}.", creator)
            chat = new_forum
            chat.send_message("LaTeX Bot has moved here.", creator)

def _movetoteam(msg: pyryver.Message, name: str):
    global chat, creator, teams
    if len(name) > 0:
        new_team = pyryver.get_obj_by_field(teams, pyryver.FIELD_NAME, name)
        if not new_team:
            chat.send_message("Team not found.", creator)
        else:
            chat.send_message(f"LaTeX Bot has moved to {name}.", creator)
            chat = new_team
            chat.send_message("LaTeX Bot has moved here.", creator)

def _help(msg: pyryver.Message, s: str):
    global chat, creator
    chat.send_message(help_text, creator)

def _ping(msg: pyryver.Message, s: str):
    global chat, creator
    chat.send_message("Pong", creator)

def _updatechats(msg: pyryver.Message, s: str):
    global chat, creator, forums, teams
    if msg.get_raw_data()["from"]["id"] not in admins:
        chat.send_message("I'm sorry Dave, I'm afraid I can't do that.", creator)
        return
    forums = ryver.get_cached_chats(pyryver.TYPE_FORUM, force_update=True)
    teams = ryver.get_cached_chats(pyryver.TYPE_TEAM, force_update=True)
    chat.send_message("Forums/Teams updated.", creator)

command_processors = {
    "render": _render,
    "moveToForum": _movetoforum,
    "moveToTeam": _movetoteam,
    "help": _help,
    "ping": _ping,
    "updateChats": _updatechats,
}

try:
    while True:
        msgs = chat.get_messages(1)
        text = msgs[0].get_body().split(" ")

        if text[0] == "@latexbot" and len(text) >= 2:
            print("Command received: " + " ".join(text))

            if text[1] in command_processors:
                command_processors[text[1]](msgs[0], " ".join(text[2:]))
            else:
                chat.send_message("Sorry, I didn't understand what you were asking me to do.", creator)

        time.sleep(3)
except KeyboardInterrupt:
    pass

chat.send_message("LaTeX Bot has been SIGINT'ed. Goodbye!", creator)

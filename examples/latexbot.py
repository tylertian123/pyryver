import pyryver
from quicklatex_render import ql_render
import time

ryver = pyryver.Ryver("arctos6135")

forums = ryver.get_cached_chats(pyryver.TYPE_FORUM)

forum = pyryver.get_obj_by_field(forums, pyryver.FIELD_NAME, "Off-Topic")

creator = pyryver.Creator("LaTeX Bot", "https://cdn.tutsplus.com/mac/authors/james-cull/TeX-Icon.png")

help_text = """
Command set:
  - `$latexbot render <formula>` - Renders LaTeX.
  - `$latexbot help` - Print a help message.
  - `$latexbot ping` - I will respond with "Pong" if I'm here.
  - `$latexbot moveto <forum>` - Move me to another forum (only Tyler can do this right now).
"""

print("LaTeX Bot is running!")
forum.send_message("""
LaTeX Bot is online! Note that to reduce load, I only check messages once per 3 seconds or more!
""" + help_text, creator)

def _render(msg: pyryver.Message, formula: str):
    global forum, creator
    if len(formula) > 0:
        img = ql_render(formula)
        forum.send_message(f"![{formula}]({img})", creator)
    else:
        forum.send_message("Formula can't be empty.", creator)

def _moveto(msg: pyryver.Message, name: str):
    global forum, creator
    if len(name) > 0:
        if msg.data["from"]["id"] != 1311906:
            forum.send_message("I'm sorry Dave, I'm afraid I can't do that.", creator)
        else:
            new_forum = pyryver.get_obj_by_field(forums, pyryver.FIELD_NICKNAME, name)
            if not new_forum:
                forum.send_message("Forum not found.", creator)
            else:
                forum.send_message(f"LaTeX Bot has moved to {name}.", creator)
                forum = new_forum
                forum.send_message("LaTeX Bot has moved here.", creator)

def _help(msg: pyryver.Message, s: str):
    global forum, creator
    forum.send_message(help_text, creator)

def _ping(msg: pyryver.Message, s: str):
    global forum, creator
    forum.send_message("Pong", creator)

command_processors = {
    "render": _render,
    "moveto": _moveto,
    "help": _help,
    "ping": _ping,
}

try:
    while True:
        msgs = forum.get_messages(1)
        text = msgs[0].get_body().split(" ")

        if text[0] == "$latexbot" and len(text) >= 2:
            print("Command received: " + " ".join(text))

            if text[1] in command_processors:
                command_processors[text[1]](msgs[0], " ".join(text[2:]))
            else:
                forum.send_message("Sorry, I didn't understand what you were asking me to do.", creator)

        time.sleep(3)
except KeyboardInterrupt:
    pass

forum.send_message("LaTeX Bot has been SIGINT'ed. Goodbye!", creator)

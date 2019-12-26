import pyryver
from quicklatex_render import ql_render
import time

ryver = pyryver.Ryver("arctos6135")

forums = ryver.get_cached_chats(pyryver.TYPE_FORUM)

forum = pyryver.get_obj_by_field(forums, pyryver.FIELD_NAME, "Off-Topic")

creator = pyryver.Creator("LaTeX Bot", "https://cdn.tutsplus.com/mac/authors/james-cull/TeX-Icon.png")

print("LaTeX Bot is running!")
forum.send_message("""
LaTeX Bot is online! Note that to reduce load, I only check messages once per 3 seconds or more!
Command set:
  - `$latexbot render <formula>` - Renders LaTeX.
  - `$latexbot ping` - I will respond with "Pong" if I'm here.
  - `$latexbot moveto <forum>` - Move me to another forum (only Tyler can do this right now).
""", creator)

try:
    while True:
        msgs = forum.get_messages(1)
        text = msgs[0].get_body()
        if text.startswith("$latexbot"):
            print("Command received: " + text)
            text = text[text.index(" ") + 1:]

            if text.startswith("render "):
                formula = text[text.index(" ") + 1:]
                if len(formula) > 0:
                    img = ql_render(formula)
                    forum.send_message(f"![LaTeX]({img})", creator)
                else:
                    forum.send_message("Formula can't be empty.", creator)
            elif text.startswith("moveto "):
                f = text[text.index(" ") + 1:]
                if len(f) > 0:
                    if msgs[0].data["from"]["id"] != 1311906:
                        forum.send_message("I'm sorry Dave, I'm afraid I can't do that.", creator)
                    else:
                        new_forum = pyryver.get_obj_by_field(forums, pyryver.FIELD_NICKNAME, f)
                        if not new_forum:
                            forum.send_message("Forum not found.", creator)
                        else:
                            forum = new_forum
                            forum.send_message("LaTeX Bot has moved here.", creator)
                else:
                    forum.send_message("Please provide a forum nickname.", creator)
            elif text.startswith("ping"):
                forum.send_message("Pong", creator)
            else:
                forum.send_message("Sorry, I didn't understand what you were asking me to do.", creator)
        time.sleep(3)
except KeyboardInterrupt:
    pass

forum.send_message("LaTeX Bot has been SIGINT'ed. Goodbye!", creator)

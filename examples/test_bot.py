import pyryver
import time
import code

ryver = pyryver.Ryver("arctos6135")

forums = ryver.get_cached_chats(pyryver.TYPE_FORUM)
teams = ryver.get_cached_chats(pyryver.TYPE_TEAM)

chat = pyryver.get_obj_by_field(forums, pyryver.FIELD_NAME, "Test")

creator = pyryver.Creator("Moeez's Test Bot", "https://i.imgur.com/KQFedrx.png")

start_text = "Hi I'm Moeez's Test Bot"

print("Test bot is running...")
chat.send_message(start_text, creator)

code.interact(local=dict(globals(), **locals()))

print("Shutting down...")
chat.send_message("I died.", creator)

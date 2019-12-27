# pyryver

`pyryver` is a small and simple Python library for Ryver's REST APIs. It provides a simple and sane way of automating tasks on Ryver and building bots, without the need to set up Hubot or Botkit.

`pyryver` is still under development. More features are coming soon!

## Setup
As `pyryver` is not on pip yet, simply put `pyryver.py` inside your project. It also depends on the `requests` library.

## Examples
More examples can be found in the `examples` directory.

### Sending a chat message
```py
import pyryver

# This will prompt you for credentials
ryver = pyryver.Ryver()

# This will get all the forums that your user can see
# You can also replace TYPE_FORUM with TYPE_TEAM or TYPE_USER
# Note this will cache the forums as a JSON
forums = ryver.get_cached_chats(pyryver.TYPE_FORUM)
# Find the forum with the desired name
forum = pyryver.get_obj_by_field(forums, pyryver.FIELD_NAME, "Your Forum Name")

# Send a message to that forum
forum.send_message("Hello, World!")
```

### Reading chat messages
```py
import pyryver

# This will prompt you for credentials
ryver = pyryver.Ryver()

# This will get all the forums that your user can see
# You can also replace TYPE_FORUM with TYPE_TEAM or TYPE_USER
# Note this will cache the forums as a JSON
forums = ryver.get_cached_chats(pyryver.TYPE_FORUM)
# Find the forum with the desired name
forum = pyryver.get_obj_by_field(forums, pyryver.FIELD_NAME, "Your Forum Name")

# Get the last 5 chat messages and print them
messages = forum.get_messages(5)
for message in message:
    print(message.get_body())
```

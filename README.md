# pyryver

`pyryver` is a small and simple Python library for Ryver's REST APIs. It provides a simple and sane way of automating tasks on Ryver and building bots, without the need to set up Hubot or Botkit.

`pyryver` is still under development. More features are coming soon!

## Installation
`pyryver` is now on PyPI! You can install it with `python3 -m pip install --user pyryver`.

You can also simply put `pyryver/pyryver.py` inside your project. Note that `pyryver` depends on the `requests` library.

## Supported Actions
  - All Chats (`Chat`, includes forums, teams, and user DMs)
    - Send message (`Chat.send_message()`)
    - Create topic (`Chat.create_topic()`)
    - Get topics (`Chat.get_topics()`)
    - Get messages (`Chat.get_messages()`)
  - Users (`User`)
    - Activate/Deactivate (`User.set_activated()`)
    - Get roles (`User.get_roles()`)
    - Set role (`User.set_org_role()`)
  - All Messages (Topics, Topic Replies, Chat Messages) (`Message`)
    - Get body (`Message.get_body()`)
    - React (`Message.react()`)
    - Get reactions (`Message.get_reactions()`)
    - Get author (`Message.get_author()`)
    - Get file attachment (`Message.get_attached_file()`)
  - Topics (`Topic`)
    - Reply (`Topic.reply()`)
    - Get replies (`Topic.get_replies()`)
  - Topic Replies (`TopicReply`)
    - Get topic (`TopicReply.get_topic()`)
  - Chat Messages (`ChatMessage`)
    - Delete (`ChatMessage.delete()`)
    - Get chat (`ChatMessage.get_chat()`)
  - Notifications (`Notification`)
    - Get notifications (`Ryver.get_notifs()`)
    - Mark all notifications as read (`Ryver.mark_all_notifs_read()`)
    - Mark all notifications as seen (`Ryver.mark_all_notifs_seen()`)
    - Mark a notification as read/unread/seen/unseen (`Notification.set_status()`)
  - Miscellaneous
    - List all forums/teams/users/etc (`Ryver.get_chats()`/`Ryver.get_cached_chats()`)
    - Uploading files (`Ryver.upload_file()`)

More actions will be coming soon!

## Examples
More examples can be found in the `examples` directory.
To see an example of `pyryver` being used for a real project, check out [`tylertian123/ryver-latexbot`](https://github.com/tylertian123/ryver-latexbot).

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

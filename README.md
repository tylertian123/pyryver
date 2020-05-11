# pyryver
![Python 3](https://img.shields.io/pypi/pyversions/pyryver)
[![MIT License](https://img.shields.io/pypi/l/pyryver)](https://github.com/tylertian123/pyryver/blob/master/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/pyryver)](https://pypi.org/project/pyryver/)
[![Read the Docs](https://img.shields.io/readthedocs/pyryver)](https://pyryver.readthedocs.io/en/latest/)

`pyryver` is an unofficial async Python library for Ryver.
It provides a simple and sane way of automating tasks on Ryver and building bots, without the need to set up Hubot or Botkit.

`pyryver` is still under development. More features are coming soon!

Special thanks to [@mincrmatt12](https://github.com/mincrmatt12)!

## Installation
`pyryver` is now on PyPI! You can install it with `python3 -m pip install --user pyryver`.

You can also simply put `pyryver/pyryver.py` inside your project, and install everything in `requirements.txt`.

`pyryver` requires Python >= 3.6 and the `aiohttp` library.

## Supported Actions
Here is a list of most of the major actions supported by `pyryver`. 
For a complete list of everything the API contains, head over to [the docs](https://pyryver.readthedocs.io/en/latest/index.html).
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
    - Edit (`ChatMessage.edit()`)
    - Get chat (`ChatMessage.get_chat()`)
  - Notifications (`Notification`)
    - Get notifications (`Ryver.get_notifs()`)
    - Mark all notifications as read (`Ryver.mark_all_notifs_read()`)
    - Mark all notifications as seen (`Ryver.mark_all_notifs_seen()`)
    - Mark a notification as read/unread/seen/unseen (`Notification.set_status()`)
  - Live Sessions (`RyverWS`)
    - Respond to messages in real-time (`@RyverWS.on_chat`)
    - Send typing indicators (`RyverWS.send_typing()`, `async with RyverWS.typing()`)
    - Send messages (fast) (`RyverWS.send_chat()`)
    - Respond to messages being edited (`@RyverWS.on_chat_updated`)
    - Respond to messages being deleted (`@RyverWS.on_chat_deleted`)
    - Respond to other misc. events (`@RyverWS.on_event()`)
  - Miscellaneous
    - List all forums/teams/users/etc (`Ryver.get_chats()`/`Ryver.get_cached_chats()`)
    - Uploading files (`Ryver.upload_file()`)

More actions will be coming soon!

## Documentation and Examples
Documentation and examples can be found on [Read the Docs](https://pyryver.readthedocs.io/en/latest/index.html).

If you want to see an example of `pyryver` being used in a real project, check out [LaTeX Bot](https://github.com/tylertian123/ryver-latexbot).

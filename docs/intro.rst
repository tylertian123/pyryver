Introduction
============

Prerequisites
-------------

``pyryver`` requires Python 3.6 or later, and is regularly tested against Python 3.6 & Python 3.8.
Our only dependency is on :doc:`aiohttp <aiohttp:index>`.

You may also wish to read :doc:`aiohttp <aiohttp:index>`'s information about optional prerequisites for high-performance workloads.

Installation
------------

Installing ``pyryver`` can either be accomplished by cloning our git repository and doing the normal ``setup.py install``, or using PyPI:
::

   # normal
   pip install -U pyryver
   # if you have multiple versions of python
   python3 -m pip install -U pyryver
   # if you use windows
   py -3 -m pip install -U pyryver

Key Information
---------------

In Ryver's API, the base class is a Chat. This, although somewhat unintuitive, does make sense: all of Ryver's functionality can be accessed through one of many interfaces, all
of which support chatting. As such, ``pyryver``'s API and this documentation often uses the word "chat" to refer to "users, teams and forums". We also use the term "group chat" to
refer to both teams and forums, and you might see them referred to as "conferences" within the code since that's what Ryver appears to call them (especially within the WebSocket API).

We also use the term "logged-in" user to refer to whichever user who's credentials were passed when creating the Ryver session.

Quickstart
----------

The core of the ``pyryver`` API is the `pyryver.ryver.Ryver` object, which represents a session with the Ryver OData HTTP API.

.. literalinclude:: _snippets/quickstart1.py
   :language: python3

As the snippet above demonstrates, you can log in as a normal user, or using a token for a custom integration.

.. warning::
   While both normal users and custom integrations can perform most actions, the Realtime API currently does not function when logging in with a token.

The `Ryver` object also stores (and can cache) some information about the Ryver organization, specifically lists of all chats.

These can be loaded either with the type-specific `pyryver.ryver.Ryver.load_users`, `pyryver.ryver.Ryver.load_teams` and `pyryver.ryver.Ryver.load_forums` or with `pyryver.ryver.Ryver.load_chats`. 
There's also `pyryer.ryver.Ryver.load_missing_chats` which won't update already loaded chats, which can be useful.

.. literalinclude:: _snippets/quickstart2.py
   :language: python3

Notice that since we grab *all* the chats once at the beginning, the specific chat lookup methods do not need to be awaited, since they just search within pre-fetched data. Also notice that searching for users
and group chats are in separate methods; either a `pyryver.objects.Forum` or `pyryver.objects.Team` is returned depending on what gets found.

Most of the functionality of ``pyryver`` exists within these chats, such as sending/checking messages and managing topics. Additional, more specific methods (such as user and chat membership management) can also
be found within the different `pyryver.objects.Chat` subclasses. For example, the following code will scan the most recent 50 messages the 
logged-in user sent to ``tylertian123`` and inform them of how many times an ellipsis occurred
within them.

.. literalinclude:: _snippets/quickstart3.py
   :language: python3

For more information on how to use `Chats <pyryver.objects.Chat>` and other Ryver data types, use the :doc:`Ryver entities reference <api_data>`.

Realtime Quickstart
-------------------

Building on the previous example, what if we want our terrible ellipsis counting bot to give live updates? We can use the **realtime** API! The realtime interface is centred around the `pyryver.ryver_ws.RyverWS` object, which
can be obtained with `Ryver.get_live_session()`. Unlike the rest of the API, the realtime API is largely event driven. For example:

.. warning::
   The Realtime API currently does not work when logging in with a token.

.. literalinclude:: _snippets/quickstart4.py
   :language: python3

There are a few things to notice here: firstly, that we can set event handlers with the various ``on_`` decorators of the `pyryver.ryver_ws.RyverWS` instance (you could also call these directly like any other decorator if
you want to declare these callbacks without having obtained the `pyryver.ryver_ws.RyverWS` instance yet), and secondly that the realtime API starts as soon as it is created. `pyryver.ryver_ws.RyverWS.run_forever()` is 
a helper that will run until something calls `pyryver.ryver_ws.RyverWS.terminate()`, which can be called from within event callbacks safely.

The contents of the ``msg`` parameter passed to our callback is an object of type `pyryver.ws_data.WSChatMessageData` that contains information about the message. In the ``chat`` message,
there are two fields our "bot" needs to care about: ``to_jid``, which specifies which chat the message was posted in, and ``text``, which is the content of the message. ``from_jid`` refers to the message's creator.
Perhaps unintuitively, the ``to_jid`` field should be referring to our user's chat, since we're looking at a private DM. For group chats, you'd expect the chat's JID here.

.. note::
   Note that the callback will be called even if the message was sent by the current logged in user!
   Therefore, even if you want to respond to messages from everyone, you should still make sure to check that ``from_jid`` is not the bot user's JID to avoid replying to your own messages.

Notice how we're working with the chat's **JID** here, which is a string, as opposed to the regular ID, which is an integer.
This is because the websocket system uses JIDs to refer to chats. Using this information, we can complete our terrible little bot:

.. note::
   The reason for the separate IDs is because the "ratatoskr" chat system appears to be built on XMPP, which uses these "JabberID"s to refer to users and groups.

.. literalinclude:: _snippets/quickstart5.py
   :language: python3

.. note::
   Prior to v0.3.0, the ``msg`` parameter would have been a dict containing the raw JSON data of the message, and you would access the fields directly by name through dict lookups.
   If you still wish to access the raw data of the message, all message objects passed to callbacks have a ``raw_data`` attribute that contains the dict. In v0.3.2, ``__getitem__()`` was implemented for message objects
   to directly access the ``raw_data`` dict, providing (partial) backwards compatibility.

Here we also added a connection loss handler with the `pyryver.ryver_ws.RyverWS.on_connection_loss()` decorator. The connection loss handler calls ``terminate()``, which causes ``run_forever()`` to return, allowing the program to
exit on connection loss instead of waiting forever. Alternatively, you could also make the session auto-reconnect by doing `ryver.get_live_session(auto_reconnect=True)` when starting the session.

It's important to note here that although the non-realtime API is perfectly accessible (and sometimes necessary) to use in event callbacks, it's often faster to use corresponding methods in the `pyryver.ryver_ws.RyverWS` instance
whenever possible. For some ephemeral actions like typing indicators and presence statuses, the realtime API is the *only* way to accomplish certain tasks.

For more information on how to use the realtime interface, use the :doc:`live session reference <api_realtime>`.

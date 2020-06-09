Realtime Client
========================

.. currentmodule:: pyryver.ryver_ws

.. autoclass:: RyverWS

   .. automethod:: on_chat
      :decorator:
   .. automethod:: on_chat_deleted
      :decorator:
   .. automethod:: on_chat_updated
      :decorator:
   .. automethod:: on_presence_changed
      :decorator:
   .. automethod:: on_user_typing
      :decorator:
   .. automethod:: on_connection_loss
      :decorator:

   .. autoattribute:: EVENT_REACTION_ADDED
   .. autoattribute:: EVENT_REACTION_REMOVED
   .. autoattribute:: EVENT_TOPIC_CHANGED
   .. autoattribute:: EVENT_TASK_CHANGED
   .. autoattribute:: EVENT_ENTITY_CHANGED
   .. autoattribute:: EVENT_ALL

   .. automethod:: on_event
      :decorator:

   .. autoattribute:: MSG_TYPE_CHAT
   .. autoattribute:: MSG_TYPE_CHAT_UPDATED
   .. autoattribute:: MSG_TYPE_CHAT_DELETED
   .. autoattribute:: MSG_TYPE_PRESENCE_CHANGED
   .. autoattribute:: MSG_TYPE_USER_TYPING
   .. autoattribute:: MSG_TYPE_EVENT
   .. autoattribute:: MSG_TYPE_ALL

   .. automethod:: on_msg_type
      :decorator:

   .. automethod:: send_chat

   .. automethod:: typing
      :async-with:
   .. automethod:: send_typing
   .. automethod:: send_clear_typing

   .. autoattribute:: PRESENCE_AVAILABLE
   .. autoattribute:: PRESENCE_AWAY
   .. autoattribute:: PRESENCE_DO_NOT_DISTURB
   .. autoattribute:: PRESENCE_OFFLINE

   .. automethod:: send_presence_change

   .. note::
      If you use this class as an ``async with`` context manager, you don't need to call
      these two methods, unless you want to break out of a `RyverWS.run_forever()`.

   .. automethod:: start
   .. automethod:: close

   .. automethod:: run_forever

.. autoclass:: RyverWSTyping
   :members:
   :undoc-members:

.. autoclass:: ClosedError
   :members:
   :show-inheritance:


Callback Task Data Types
------------------------
.. currentmodule:: pyryver.ws_data

.. autoclass:: WSMessageData
   :members:
.. autoclass:: WSChatMessageData
   :members:
   :show-inheritance:
.. autoclass:: WSChatUpdatedData
   :members:
   :show-inheritance:
.. autoclass:: WSChatDeletedData
   :members:
   :show-inheritance:
.. autoclass:: WSPresenceChangedData
   :members:
   :show-inheritance:
.. autoclass:: WSUserTypingData
   :members:
   :show-inheritance:
.. autoclass:: WSEventData
   :members:
   :show-inheritance:

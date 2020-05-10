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

   .. automethod:: on_connection_loss
      :decorator:

   .. autoattribute:: EVENT_REACTION_ADDED
   .. autoattribute:: EVENT_REACTION_REMOVED
   .. autoattribute:: EVENT_ALL

   .. automethod:: on_event
      :decorator:

   .. autoattribute:: MSG_TYPE_ALL

   .. automethod:: on_msg_type
      :decorator:

   .. automethod:: send_chat

   .. automethod:: typing
      :async-with:
   .. automethod:: send_typing

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

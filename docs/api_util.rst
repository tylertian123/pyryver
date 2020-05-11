Utilities
=========

.. automodule:: pyryver.cache_storage
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: pyryver.util
   :members:
   :undoc-members:

.. _util-data-constants:

Entity Types
------------

.. data:: TYPE_USER

   Corresponds to `pyryver.objects.User`.
.. data:: TYPE_FORUM

   Corresponds to `pyryver.objects.Forum`.
.. data:: TYPE_TEAM

   Corresponds to `pyryver.objects.Team`.
.. data:: TYPE_GROUPCHAT_MEMBER

   Corresponds to `pyryver.objects.GroupChatMember`.
.. data:: TYPE_TOPIC

   Corresponds to `pyryver.objects.Topic`.
.. data:: TYPE_TOPIC_REPLY

   Corresponds to `pyryver.objects.TopicReply`.
.. data:: TYPE_NOTIFICATION

   Corresponds to `pyryver.objects.Notification`.
.. data:: TYPE_STORAGE

   Corresponds to `pyryver.objects.Storage`.
.. data:: TYPE_FILE

   Corresponds to `pyryver.objects.File`.

Common Field Names
------------------

.. data:: FIELD_USERNAME
.. data:: FIELD_EMAIL_ADDR
.. data:: FIELD_DISPLAY_NAME

   The object's display name (friendly name)
.. data:: FIELD_NAME
.. data:: FIELD_NICKNAME
.. data:: FIELD_ID

   The object's ID, sometimes an `int`, sometimes a `str` depending on the object type.
.. data:: FIELD_JID

   The object's JID, or JabberID. Used in the live socket interface for referring to chats.

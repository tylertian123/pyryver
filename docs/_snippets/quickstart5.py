async with pyryver.Ryver("organization_name", "username", "password") as ryver:
    await ryver.load_chats()

    a_user = ryver.get_user(username="tylertian123")
    me = ryver.get_user(username="username")

    async with ryver.get_live_session() as session:
        @session.on_chat
        async def on_chat(msg: pyryver.WSChatMessageData):
            # did the message come from a_user and was sent via DM to us?
            if msg.to_jid == me.get_jid() and msg.from_jid == a_user.get_jid():
                # did the message contain "..."?
                if "..." in msg.text:
                    # send a reply via the non-realtime system (slow)
                    # await a_user.send_message("Hey, that ellipsis is _mean_!")
                    # send a reply via the realtime system
                    await session.send_chat(a_user, "Hey, that ellipsis is _mean_!")

        @session.on_connection_loss
        async def on_connection_loss():
            # Make sure that the session is terminated and run_forever() returns on connection loss
            await session.terminate()

        await session.run_forever()

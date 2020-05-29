async with pyryver.Ryver("organization_url", "username", "password") as ryver:
    await ryver.load_chats()

    a_user = ryver.get_user(username="tylertian123")
    me = ryver.get_user(username="username")

    async with ryver.get_live_session() as session:
        @session.on_chat
        async def on_chat(msg):
            # did the message come from a_user and was sent via DM to us?
            if msg["to"] == me.get_jid() and msg["from"] == a_user.get_jid():
                # did the message contain "..."?
                if "..." in msg["text"]:
                    # send a reply via the non-realtime system (slow)
                    # await a_user.send_message("Hey, that ellipsis is _mean_!")
                    # send a reply via the realtime system
                    await session.send_chat(a_user, "Hey, that ellipsis is _mean_!")

        @session.on_connection_loss
        async def on_connection_loss():
            await session.close()

        await session.run_forever()

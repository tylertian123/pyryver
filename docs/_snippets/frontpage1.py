import pyryver
import asyncio

async def main():
    # Connect to ryver
    async with pyryver.Ryver("my_organization", "my_username", "my_password") as ryver:
        # Load all chats
        await ryver.load_chats()

        # get a user by username
        my_friend = ryver.get_user(username="tylertian123")
        me = ryver.get_user(username="my_username")
        # send a message to a chat (in this case a DM)
        await my_friend.send_message("hello there")

        # connect to the websockets interface
        async with ryver.get_live_session(auto_reconnect=True) as session:
            @session.on_chat
            async def on_message(msg: pyryver.WSChatMessageData):
                print(msg.text) # print out the message's text
                # Reply to the message
                # Make sure to check that the message isn't from the bot itself
                if msg.from_jid != me.get_jid() and msg.text == "hello":
                    # Send a message to the same chat
                    # This could be either a user (for a private message) or a forum/team
                    chat = ryver.get_chat(jid=msg.to_jid)
                    await chat.send_message("hi")

            # run until session.terminate() is called
            await session.run_forever()

asyncio.get_event_loop().run_until_complete(main())

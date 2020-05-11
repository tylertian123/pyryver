import pyryver
import asyncio

async def main():
    # Connect to ryver
    async with pyryver.Ryver("myorg", "username", "password") as ryver:
        await ryver.load_users()
        
        # get a user by username
        my_friend = ryver.get_user(username="tylertian123")
        # send a message to a chat (in this case a DM)
        await my_friend.send_message("hello there") 

        # connect to the websockets interface
        async with ryver.get_live_session() as session:
            @session.on_chat
            def on_message(msg):
                print(msg["text"]) # print out the message's text

            # run until session.close()
            await session.run_forever()

asyncio.get_event_loop().run_until_complete(main())

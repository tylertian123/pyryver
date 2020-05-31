async with pyryver.Ryver("organization_name", "username", "password") as ryver:
    await ryver.load_chats()

    a_user = ryver.get_user(username="tylertian123")

    async with ryver.get_live_session() as session:
        @session.on_chat
        async def on_chat(msg):
            pass

        await session.run_forever()

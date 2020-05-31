async with pyryver.Ryver("organization_name", "username", "password") as ryver:
    await ryver.load_chats()

    a_user = ryver.get_user(username="tylertian123")
    a_forum = ryver.get_groupchat(display_name="Off-Topic")

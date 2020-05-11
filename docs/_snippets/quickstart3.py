async with pyryver.Ryver("organization_url", "username", "password") as ryver:
    await ryver.load_chats()

    a_user = ryver.get_user(username="tylertian123")
    # a_forum = ryver.get_groupchat(display_name="Off-Topic")

    tally = 0
    for message in await a_user.get_messages(50):
        if "..." in message.get_body():
            tally += 1

    await a_user.send_message("There's been an ellipsis in here {} times".format(tally))

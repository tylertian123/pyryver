# Log in as a normal user
async with pyryver.Ryver("organization_name", "username", "password") as ryver:
    pass

# Log in with a token (for custom integrations)
async with pyryver.Ryver("organization_name", token="token") as ryver:
    pass

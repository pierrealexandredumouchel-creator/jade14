MASTER_NICK = "alxd"

MASTER_HOSTS = [
    "Alerion.users.undernet.org",
    "alxd.kekistan.faith",
]

def is_master(nick, hostmask):

    if nick.lower() != MASTER_NICK.lower():
        return False

    return any(
        host in hostmask
        for host in MASTER_HOSTS
    )

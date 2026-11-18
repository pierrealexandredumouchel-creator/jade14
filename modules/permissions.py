"""Maîtres des bots Ghost Royale.

Un maître est reconnu par son pseudo ET son hôte : un pseudo seul se vole
en deux secondes sur Undernet. Pour ajouter quelqu'un, mets son pseudo en
minuscules et le bout d'hôte que montre /whois (avec le @ devant).
Un pseudo sans hôte n'a aucun accès.
"""

MASTERS = {
    "alxd": (
        "@alxd.kekistan.faith",
        "@alerion.users.undernet.org",
        "@alxd99.users.undernet.org",
    ),
    # Chums de #montreal nommés maîtres par alxd (2026-11-18).
    # Hôtes à remplir : tant que c'est vide, ils n'ont pas accès.
    "ikce": (),
    "simon": (),
    "sid": (),
}


def is_master(nick, hostmask):
    """hostmask : préfixe IRC complet, ex. « alxd!~alxd@alxd.kekistan.faith »."""
    allowed_hosts = MASTERS.get(str(nick).casefold())
    if not allowed_hosts:
        return False
    hostmask = str(hostmask).casefold()
    return any(host.casefold() in hostmask for host in allowed_hosts)


def master_nicks():
    """Pseudos qui ont au moins un hôte configuré."""
    return sorted(nick for nick, hosts in MASTERS.items() if hosts)

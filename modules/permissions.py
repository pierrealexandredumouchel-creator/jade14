"""Maîtres des bots Ghost Royale (même fichier dans Anya, Jade et Christine).

Un maître est reconnu par son pseudo ET son hôte exact : un pseudo seul se
vole en deux secondes sur Undernet. Pour ajouter quelqu'un, mets son pseudo
en minuscules et l'hôte que montre /whois (la partie après le @).
Un pseudo sans hôte n'a aucun accès.
"""

import json
import os

MASTERS = {
    "alxd": (
        "alxd.kekistan.faith",
        "alerion.users.undernet.org",
        "alxd99.users.undernet.org",
    ),
    # Chums de #montreal nommés maîtres par alxd (2026-11-18).
    # Hôtes à remplir : tant que c'est vide, ils n'ont pas accès.
    "ikce": (),
    "simon": (),
    "sid": (),
}

ADMINFILE = os.path.join(os.path.dirname(__file__), "admins.json")


def _host(hostmask):
    """« alxd!~alxd@alxd.kekistan.faith » -> « alxd.kekistan.faith »."""
    return str(hostmask).rsplit("@", 1)[-1].strip().lower()


def is_master(nick, hostmask):
    allowed_hosts = MASTERS.get(str(nick).casefold())
    if not allowed_hosts:
        return False
    return _host(hostmask) in {h.lower() for h in allowed_hosts}


def master_nicks():
    """Pseudos qui ont au moins un hôte configuré."""
    return sorted(nick for nick, hosts in MASTERS.items() if hosts)


def is_trusted(nick, hostmask):
    """Maître, ou admin inscrit sous la forme « nick@hôte » dans admins.json
    (pseudo ET hôte doivent concorder)."""
    if is_master(nick, hostmask):
        return True
    try:
        with open(ADMINFILE) as f:
            admins = json.load(f).get("admins", [])
    except Exception:
        admins = []
    host = _host(hostmask)
    for entry in admins:
        if "@" not in entry:
            continue
        n, h = entry.split("@", 1)
        if n.lower() == str(nick).lower() and h.lower() == host:
            return True
    return False

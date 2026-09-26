import json
import os
import os

ADMINFILE = os.path.join(os.path.dirname(__file__), "admins.json")

def load_admins():
    if not os.path.exists(ADMINFILE):
        return {"admins": []}
    with open(ADMINFILE, "r") as f:
        return json.load(f)

def save_admins(data):
    with open(ADMINFILE, "w") as f:
        json.dump(data, f)

def is_admin(nick):
    data = load_admins()
    return nick.lower() in [a.lower() for a in data["admins"]]

def add_admin(nick):
    data = load_admins()
    if nick not in data["admins"]:
        data["admins"].append(nick)
        save_admins(data)
        return True
    return False

def del_admin(nick):
    data = load_admins()
    if nick in data["admins"]:
        data["admins"].remove(nick)
        save_admins(data)
        return True
    return False

def list_admins():
    data = load_admins()
    return ", ".join(data["admins"]) if data["admins"] else "Aucun admin."

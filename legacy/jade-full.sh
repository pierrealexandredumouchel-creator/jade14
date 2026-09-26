#!/bin/bash
set -e

echo "=== INSTALLATION JADE14-PYTHON-ULTRA-FULL-2026 — alxd ==="

sudo apt update -y
sudo apt install -y python3 python3-pip

sudo mkdir -p /opt/jade14
sudo chown $USER:$USER /opt/jade14
cd /opt/jade14

# -----------------------------
# BOT PYTHON ULTRA FULL
# -----------------------------
sudo tee jade14.py > /dev/null << 'EOF'
import socket, time, threading, json, random

SERVER = "irc6.undernet.org"
PORT = 6667
NICK = "Jade14"
ALT = "Jade14_"
IDENT = "jade14"
REALNAME = "Jade14 Python Bot Ultra"
CHANNEL = "#montreal"

DATA_FILE = "/opt/jade14/data.json"

# -----------------------------
# Chargement / sauvegarde JSON
# -----------------------------
try:
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
except:
    data = {
        "gold":{},
        "inv":{},
        "boss":{},
        "xp":{},
        "lvl":{},
        "quests":{}
    }

def save():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# -----------------------------
# Fonctions utilitaires
# -----------------------------
def send(msg):
    s.send((msg + "\r\n").encode())

def give_gold(user, amount):
    data["gold"][user] = data["gold"].get(user, 0) + amount
    save()

def add_item(user, item):
    data["inv"].setdefault(user, []).append(item)
    save()

def give_xp(user, amount):
    data["xp"][user] = data["xp"].get(user, 0) + amount
    if data["xp"][user] >= (data["lvl"].get(user,1) * 100):
        data["lvl"][user] = data["lvl"].get(user,1) + 1
        send(f"PRIVMSG {CHANNEL} :🎉 {user} monte au niveau {data['lvl'][user]} !")
    save()

# -----------------------------
# Boss cosmique multi‑phases
# -----------------------------
def spawn_boss():
    data["boss"] = {
        "name":"Chat Noir Cosmique",
        "hp":200,
        "phase":1
    }
    save()
    send(f"PRIVMSG {CHANNEL} :⚠️ Le Chat Noir Cosmique apparaît ! HP = 200")

def hit_boss(user):
    if not data["boss"]:
        send(f"PRIVMSG {CHANNEL} :Aucun boss présent.")
        return

    dmg = random.randint(10,30)
    data["boss"]["hp"] -= dmg
    save()

    send(f"PRIVMSG {CHANNEL} :{user} frappe le boss pour {dmg} dégâts ! HP = {data['boss']['hp']}")

    # Phase 2
    if data["boss"]["hp"] <= 120 and data["boss"]["phase"] == 1:
        data["boss"]["phase"] = 2
        save()
        send(f"PRIVMSG {CHANNEL} :🔥 Le boss entre en phase 2 ! Attaques plus rapides !")

    # Phase 3
    if data["boss"]["hp"] <= 60 and data["boss"]["phase"] == 2:
        data["boss"]["phase"] = 3
        save()
        send(f"PRIVMSG {CHANNEL} :💀 Phase 3 ! Le Chat Noir Cosmique déchaîne sa fureur !")

    # Mort
    if data["boss"]["hp"] <= 0:
        send(f"PRIVMSG {CHANNEL} :🌟 Le boss est vaincu ! +100 or et +200 XP à tous les joueurs !")
        for u in data["gold"]:
            give_gold(u, 100)
            give_xp(u, 200)
        data["boss"] = {}
        save()

# -----------------------------
# Quêtes
# -----------------------------
quests_list = {
    "chasseur": "Tuer 1 boss",
    "explorateur": "Trouver 3 loots",
    "marchand": "Acheter 2 items"
}

def start_quest(user, quest):
    if quest not in quests_list:
        send(f"PRIVMSG {CHANNEL} :Quête inconnue.")
        return
    data["quests"][user] = {"name":quest, "progress":0}
    save()
    send(f"PRIVMSG {CHANNEL} :{user} commence la quête : {quest}")

def progress_quest(user, action):
    if user not in data["quests"]:
        return
    q = data["quests"][user]["name"]

    if q == "chasseur" and action == "boss_kill":
        data["quests"][user]["progress"] = 1

    if q == "explorateur" and action == "loot":
        data["quests"][user]["progress"] += 1

    if q == "marchand" and action == "buy":
        data["quests"][user]["progress"] += 1

    if data["quests"][user]["progress"] >= 1 and q == "chasseur":
        send(f"PRIVMSG {CHANNEL} :🎖️ {user} termine la quête Chasseur ! +50 or +100 XP")
        give_gold(user, 50)
        give_xp(user, 100)
        del data["quests"][user]
        save()

    if data["quests"][user]["progress"] >= 3 and q == "explorateur":
        send(f"PRIVMSG {CHANNEL} :🎖️ {user} termine la quête Explorateur ! +30 or +80 XP")
        give_gold(user, 30)
        give_xp(user, 80)
        del data["quests"][user]
        save()

    if data["quests"][user]["progress"] >= 2 and q == "marchand":
        send(f"PRIVMSG {CHANNEL} :🎖️ {user} termine la quête Marchand ! +40 or +60 XP")
        give_gold(user, 40)
        give_xp(user, 60)
        del data["quests"][user]
        save()

# -----------------------------
# Shop
# -----------------------------
shop_items = {
    "potion":10,
    "épée":25,
    "armure":40
}

def buy_item(user, item):
    if item not in shop_items:
        send(f"PRIVMSG {CHANNEL} :Item inconnu.")
        return
    price = shop_items[item]
    if data["gold"].get(user,0) < price:
        send(f"PRIVMSG {CHANNEL} :{user}, tu n'as pas assez d'or.")
        return
    give_gold(user, -price)
    add_item(user, item)
    progress_quest(user, "buy")
    send(f"PRIVMSG {CHANNEL} :{user} achète {item} pour {price} or.")

# -----------------------------
# Commandes IRC
# -----------------------------
def handle_command(user, cmd):
    if cmd == "!ping":
        send(f"PRIVMSG {CHANNEL} :Pong {user} !")

    elif cmd == "!gold":
        send(f"PRIVMSG {CHANNEL} :{user}, or = {data['gold'].get(user,0)}")

    elif cmd == "!xp":
        send(f"PRIVMSG {CHANNEL} :{user}, XP = {data['xp'].get(user,0)}, Niveau = {data['lvl'].get(user,1)}")

    elif cmd == "!loot":
        loot = random.choice(["Plume magique","Pierre lunaire","Fragment d'étoile"])
        give_gold(user, random.randint(3,10))
        add_item(user, loot)
        progress_quest(user, "loot")
        send(f"PRIVMSG {CHANNEL} :{user} trouve un loot rare : {loot} !")

    elif cmd == "!inv":
        items = ", ".join(data["inv"].get(user, [])) or "Inventaire vide"
        send(f"PRIVMSG {CHANNEL} :Inventaire de {user} : {items}")

    elif cmd == "!boss":
        spawn_boss()

    elif cmd == "!hit":
        hit_boss(user)

    elif cmd.startswith("!buy"):
        try:
            item = cmd.split()[1]
            buy_item(user, item)
        except:
            send(f"PRIVMSG {CHANNEL} :Usage : !buy item")

    elif cmd == "!shop":
        send(f"PRIVMSG {CHANNEL} :Boutique : Potion(10), Épée(25), Armure(40)")

    elif cmd.startswith("!quest"):
        try:
            q = cmd.split()[1]
            start_quest(user, q)
        except:
            send(f"PRIVMSG {CHANNEL} :Quêtes : chasseur, explorateur, marchand")

# -----------------------------
# Boucle du bot
# -----------------------------
def bot_loop():
    global s
    s = socket.socket()
    s.connect((SERVER, PORT))
    send(f"NICK {NICK}")
    send(f"USER {IDENT} 0 * :{REALNAME}")
    time.sleep(5)
    send(f"JOIN {CHANNEL}")

    while True:
        raw = s.recv(2048).decode(errors="ignore")
        if raw.startswith("PING"):
            send(raw.replace("PING","PONG"))

        if "PRIVMSG" in raw:
            try:
                user = raw.split("!")[0].replace(":", "")
                msg = raw.split("PRIVMSG")[1].split(":",1)[1].strip()
                if msg.startswith("!"):
                    handle_command(user, msg)
            except:
                pass

threading.Thread(target=bot_loop).start()
EOF

# -----------------------------
# Service systemd
# -----------------------------
sudo tee /etc/systemd/system/jade14.service > /dev/null << 'EOF'
[Unit]
Description=Jade14 Python IRC Bot Ultra Full 2026
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/jade14/jade14.py
Restart=always
User=root
WorkingDirectory=/opt/jade14

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now jade14

echo "=== JADE14-PYTHON-ULTRA-FULL-2026 ONLINE — #montreal ==="


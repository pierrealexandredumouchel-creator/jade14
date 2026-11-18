import re
from modules.master import handle as ghost_handle
from modules.permissions import is_master, master_nicks
from modules.duckhunt import reset_duck, score, shoot, spawn_duck


def handle_command(bot, line):
    parts = line.split(" ")
    user = parts[0].split("!")[0].replace(":", "")
    chan = parts[2]
    msg = " ".join(parts[3:]).replace(":", "", 1)
    hostmask = parts[0][1:]

    class GhostAdapter:
        def __init__(self, bot):
            self.bot = bot
            self.sock = bot.sock

        def send_raw(self, data):
            self.sock.send((data + "\r\n").encode())

        def reply(self, target, nick, text):
            self.bot.send(target, f"{nick}: {text}")

    if ghost_handle(
        GhostAdapter(bot),
        user,
        hostmask,
        chan,
        msg
    ):
        return

    # GHOST TARGET JOIN PART jade14
    target_prefixes = (
            "!jade ",
            "!jade14 ",
    )

    if msg.casefold().startswith(target_prefixes):
        owner_ok = is_master(user, hostmask)

        if not owner_ok:
            bot.send(
                chan,
                f"{user}: accès refusé.",
            )
            return

        command_parts = msg.split()

        # En privé, on répond à la personne plutôt qu'à Jade elle-même.
        reply_to = chan if chan.startswith("#") else user

        # Parler à travers Jade : !jade say|action #canal texte (maître seulement).
        if len(command_parts) >= 4 and command_parts[1].casefold() in ("say", "action"):
            destination = command_parts[2]
            texte = " ".join(msg.split(" ", 3)[3].split())[:400]
            if not re.fullmatch(r"#[^\x00\x07\r\n ,:]+", destination) or not texte:
                bot.send(reply_to, "Usage: !jade say|action #canal texte")
                return
            if command_parts[1].casefold() == "say":
                bot.send(destination, texte)
            else:
                bot.send(destination, "\x01ACTION " + texte + "\x01")
            return

        if len(command_parts) != 3:
            bot.send(
                chan,
                "Usage: !jade join|part #canal, ou !jade say|action #canal texte",
            )
            return

        action = command_parts[1].casefold()
        requested_channel = command_parts[2]

        valid_channel = re.fullmatch(
            r"#[^\x00\x07\r\n ,:]+",
            requested_channel,
        )

        if not valid_channel:
            bot.send(
                chan,
                "Canal invalide.",
            )
            return

        if action == "join":
            bot.sock.send(
                (
                    f"JOIN {requested_channel}\r\n"
                ).encode()
            )

            bot.send(
                chan,
                f"Je rejoins {requested_channel}.",
            )
            return

        if action == "part":
            bot.sock.send(
                (
                    f"PART {requested_channel} "
                    f":Commande de {user}\r\n"
                ).encode()
            )
            return

        bot.send(
            chan,
            "Usage: commande join|part #canal",
        )
        return


    if msg.startswith("!ping"):
        bot.send(chan, "pong")

    if msg.startswith("!hello"):
        bot.send(chan, f"Salut {user}, ici JADE14 Ghost Royale.")

    if msg.startswith("!say "):
        # Réservé aux admins : sinon n'importe qui fait dire n'importe quoi à Jade.
        if not is_master(user, hostmask):
            bot.send(chan, f"{user}: Tu n'es pas admin.")
            return
        bot.send(chan, msg[5:])

    if msg.startswith("!duckhunt"):
        spawn_duck(bot, chan)

    if msg.startswith("!shoot"):
        shoot(bot, user, chan)

    if msg.startswith("!score"):
        score(bot, user, chan)

    if msg.startswith("!resetduck"):
        if not is_master(user, hostmask):
            bot.send(chan, f"{user}: Tu n'es pas admin.")
            return
        reset_duck(bot, chan)

    if msg.startswith("!addadmin"):
        if not is_master(user, hostmask):
            bot.send(chan, f"{user}: Tu n'es pas admin.")
            return

        # Les maîtres se configurent avec leur hôte dans modules/permissions.py :
        # un pseudo seul, ajouté par IRC, se volerait trop facilement.
        bot.send(chan, f"{user}: les maîtres s'ajoutent dans modules/permissions.py (pseudo + hôte).")

    if msg.startswith("!admins"):
        bot.send(chan, "Maîtres: " + (", ".join(master_nicks()) or "aucun"))

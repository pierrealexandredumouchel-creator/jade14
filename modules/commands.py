import re
from modules.master import handle as ghost_handle
from modules.admin import add_admin, is_admin, list_admins
from modules.duckhunt import reset_duck, score, shoot, spawn_duck


def handle_command(bot, line):
    parts = line.split(" ")
    user = parts[0].split("!")[0].replace(":", "")
    chan = parts[2]
    msg = " ".join(parts[3:]).replace(":", "", 1)

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
        user,
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
        hostmask = parts[0][1:]
        host_lower = hostmask.casefold()

        owner_ok = (
            user.casefold() == "alxd"
            and (
                "@alxd.kekistan.faith"
                in host_lower
                or
                "@alerion.users.undernet.org"
                in host_lower
            )
        )

        if not owner_ok:
            bot.send(
                chan,
                f"{user}: accès refusé.",
            )
            return

        command_parts = msg.split()

        if len(command_parts) != 3:
            bot.send(
                chan,
                "Usage: commande join|part #canal",
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
        if not is_admin(user):
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
        if not is_admin(user):
            bot.send(chan, f"{user}: Tu n'es pas admin.")
            return
        reset_duck(bot, chan)

    if msg.startswith("!addadmin"):
        if not is_admin(user):
            bot.send(chan, f"{user}: Tu n'es pas admin.")
            return

        try:
            new_admin = msg.split(" ")[1]
            if add_admin(new_admin):
                bot.send(chan, f"Admin ajouté: {new_admin}")
            else:
                bot.send(chan, f"{new_admin} est déjà admin.")
        except IndexError:
            bot.send(chan, "Usage: !addadmin <nick>")

    if msg.startswith("!admins"):
        bot.send(chan, "Admins: " + list_admins())

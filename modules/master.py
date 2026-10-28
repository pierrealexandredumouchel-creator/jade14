from modules.permissions import is_master

def handle(bot, nick, hostmask, target, msg):

    if not is_master(nick, hostmask):
        return False

    if msg == "!status":

        try:
            bot.reply(
                target,
                nick,
                "GhostCore online."
            )
        except Exception:
            pass

        return True

    if msg.startswith("!join "):

        chan = msg.split(" ", 1)[1].strip()

        if not chan.startswith("#"):
            return True

        bot.send_raw(
            f"JOIN {chan}"
        )

        return True

    if msg.startswith("!part "):

        chan = msg.split(" ", 1)[1].strip()

        if not chan.startswith("#"):
            return True

        bot.send_raw(
            f"PART {chan}"
        )

        return True

    if msg.startswith("!say "):

        parts = msg.split(" ", 2)

        if len(parts) == 3:

            chan = parts[1]
            text = parts[2]

            bot.send_raw(
                f"PRIVMSG {chan} :{text}"
            )

        return True

    return False
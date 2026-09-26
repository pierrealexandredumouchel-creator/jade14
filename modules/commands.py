from modules.admin import add_admin, is_admin, list_admins
from modules.duckhunt import reset_duck, score, shoot, spawn_duck


def handle_command(bot, line):
    parts = line.split(" ")
    user = parts[0].split("!")[0].replace(":", "")
    chan = parts[2]
    msg = " ".join(parts[3:]).replace(":", "", 1)

    if msg.startswith("!ping"):
        bot.send(chan, "pong")

    if msg.startswith("!hello"):
        bot.send(chan, f"Salut {user}, ici JADE14 Ghost Royale.")

    if msg.startswith("!say "):
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

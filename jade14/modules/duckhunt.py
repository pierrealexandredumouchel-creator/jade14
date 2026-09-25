import json
import time
import os

SCOREFILE = "duck_scores.json"
STATEFILE = "duck_state.json"


def init():
    """Initialise les fichiers de score/état s'ils n'existent pas.
    Appelé une fois au démarrage du bot (voir jade14.py)."""
    if not os.path.exists(SCOREFILE):
        save_scores({})
    if not os.path.exists(STATEFILE):
        save_state({"duck": False, "spawn_time": 0})


def load_scores():
    if not os.path.exists(SCOREFILE):
        return {}
    with open(SCOREFILE, "r") as f:
        return json.load(f)


def save_scores(scores):
    with open(SCOREFILE, "w") as f:
        json.dump(scores, f)


def load_state():
    if not os.path.exists(STATEFILE):
        return {"duck": False, "spawn_time": 0}
    with open(STATEFILE, "r") as f:
        return json.load(f)


def save_state(state):
    with open(STATEFILE, "w") as f:
        json.dump(state, f)


def spawn_duck(bot, chan):
    state = load_state()
    if state["duck"]:
        return  # un canard est déjà présent

    state["duck"] = True
    state["spawn_time"] = time.time()
    save_state(state)

    bot.send(chan, "🦆 **UN CANARD APPARAÎT!** Tapez !shoot pour tirer!")


def shoot(bot, user, chan):
    state = load_state()
    if not state["duck"]:
        bot.send(chan, f"{user}: Il n'y a aucun canard présent.")
        return

    scores = load_scores()
    scores[user] = scores.get(user, 0) + 1
    save_scores(scores)

    state["duck"] = False
    save_state(state)

    bot.send(chan, f"💥 {user} a tiré le canard! Score total: {scores[user]}")


def score(bot, user, chan):
    scores = load_scores()
    if user not in scores:
        bot.send(chan, f"{user}: Aucun score encore.")
    else:
        bot.send(chan, f"{user}: Ton score est {scores[user]}.")


def reset_duck(bot, chan):
    save_state({"duck": False, "spawn_time": 0})
    bot.send(chan, "🦆 Le jeu DUCKHUNT a été réinitialisé.")


def handle_duckhunt(bot, line):
    """Point d'entrée optionnel pour un dispatcher dédié duckhunt.
    Non utilisé actuellement : modules/commands.py gère déjà
    !duckhunt / !shoot / !score / !resetduck via handle_command().
    Gardé ici seulement parce que jade14.py l'importe."""
    pass

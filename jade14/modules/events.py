import os

LOGFILE = "logs/irc.log"

# Crée le dossier logs/ au chargement du module s'il n'existe pas déjà.
# Sans ça, open(LOGFILE, "a") lève un FileNotFoundError à CHAQUE message
# reçu tant que le dossier n'existe pas — silencieusement avalé par le
# try/except de listen() dans jade14.py, donc rien n'est loggé et on ne
# le voit que dans les logs systemd (journalctl).
os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)


def handle_event(bot, line):
    # Exemple simple : log des messages
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

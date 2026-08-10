import time


class AutoReconnect:
    """Gère le délai avant reconnexion.

    IMPORTANT : la reconnexion elle-même se fait dans la boucle run() de
    Jade14Bot, pas ici. L'ancienne version rappelait bot.connect() qui
    rappelait self.listen(), qui en cas de nouvelle coupure rappelait
    à nouveau schedule_reconnect() -> connect() -> listen() -> ...
    Chaque reconnexion empilait un nouvel appel de fonction (récursion,
    pas une boucle). Sur un bot qui tourne des mois avec des coupures
    réseau occasionnelles, ça finit par dépasser la limite de récursion
    de Python et planter avec un RecursionError.
    """

    def __init__(self, bot, delay=5):
        self.bot = bot
        self.delay = delay

    def wait(self):
        print(f"Reconnexion dans {self.delay} secondes...")
        time.sleep(self.delay)

import random
import time


class AutoReconnect:
    """Gère le délai avant reconnexion, avec une patience qui grandit.

    IMPORTANT : la reconnexion elle-même se fait dans la boucle run() de
    Jade14Bot, pas ici (l'ancienne version récursive finissait par planter
    avec un RecursionError).

    Undernet compte tous nos bots comme un seul hôte (même bloc IPv6 /64).
    Si on revient trop vite après une coupure, le serveur refuse (« Too many
    connections from your host ») puis nous ralentit (« throttled »). Donc :
    30 s, puis 60 s, 120 s… jusqu'à 10 minutes, avec un peu de hasard pour
    que les bots ne reviennent pas tous en même temps. Si la connexion a tenu
    plus de 10 minutes, on repart du début.
    """

    def __init__(self, bot, delay=30, max_delay=600):
        self.bot = bot
        self.delay = delay
        self.max_delay = max_delay
        self.failures = 0
        self.last_wait_end = 0.0

    def wait(self):
        if time.time() - self.last_wait_end > 600:
            self.failures = 0   # la dernière connexion a bien tenu
        base = min(self.max_delay, self.delay * (2 ** self.failures))
        pause = base * random.uniform(0.8, 1.2)
        self.failures += 1
        print(f"Reconnexion dans {pause:.0f} secondes (tentative {self.failures})...", flush=True)
        time.sleep(pause)
        self.last_wait_end = time.time()

import json
import socket
import time

from modules.autoreconnect import AutoReconnect
from modules.commands import handle_command
from modules.duckhunt import init as duckhunt_init
from modules.events import handle_event

# Chargement de la configuration
with open("config.json", "r") as f:
    cfg = json.load(f)

SERVER = cfg["server"]
PORT = cfg["port"]
NICK = cfg["nick"]
IDENT = cfg["ident"]
REALNAME = cfg["realname"]
CHANNELS = cfg["channels"]
CHANNEL_PASSWORD = cfg.get("channel_password")


class Jade14Bot:
    def __init__(self):
        self.sock = None
        self.reconnector = AutoReconnect(self)

    def run(self):
        """Boucle principale : connecte, écoute, et si la connexion tombe,
        attend puis recommence — SANS récursion. L'ancienne version
        chaînait connect() -> listen() -> reconnect() -> connect() -> ...
        ce qui finissait par dépasser la limite de récursion Python après
        des centaines de reconnexions sur un bot de longue durée."""
        while True:
            try:
                self.connect()
                self.listen()
            except Exception as e:
                print("Connexion perdue:", e)
            finally:
                if self.sock:
                    try:
                        self.sock.close()
                    except Exception:
                        pass
            self.reconnector.wait()

    def _pong(self, line):
        self.sock.send(f"{line.replace('PING', 'PONG', 1)}\r\n".encode())

    def connect(self):
        # Un socket neuf à chaque tentative : un socket déjà utilisé pour
        # une connexion coupée/échouée ne peut pas être réutilisé tel quel
        # pour un nouveau connect() (ça lève une erreur au lieu de vraiment
        # se reconnecter).
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"Connecting to Undernet ({SERVER}:{PORT})...")
        self.sock.connect((SERVER, PORT))
        self.sock.send(f"NICK {NICK}\r\n".encode())
        self.sock.send(f"USER {IDENT} 0 * :{REALNAME}\r\n".encode())

        self._wait_for_welcome()

        if CHANNEL_PASSWORD:
            self.sock.send(
                f"PRIVMSG x@channels.undernet.org :LOGIN {NICK} {CHANNEL_PASSWORD}\r\n".encode()
            )
            time.sleep(2)

        for chan in CHANNELS:
            self.sock.send(f"JOIN {chan}\r\n".encode())

        print(f"Connecté à Undernet en tant que {NICK}.")

    def _wait_for_welcome(self, timeout=30):
        """Attend le message 001 (connexion établie) avant de JOIN."""
        self.sock.settimeout(timeout)
        buffer = ""
        try:
            while True:
                chunk = self.sock.recv(4096)
                if not chunk:
                    raise ConnectionError("Connexion fermée par le serveur IRC.")
                buffer += chunk.decode("latin-1", errors="ignore")
                while "\r\n" in buffer:
                    line, buffer = buffer.split("\r\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("PING"):
                        self._pong(line)
                    if " 001 " in line or line.endswith(" 001"):
                        return
                    if " 433 " in line or " 432 " in line:
                        raise ConnectionError(f"Nick refusé: {line}")
                    if " 465 " in line or " 464 " in line:
                        raise ConnectionError(f"Connexion refusée: {line}")
        finally:
            self.sock.settimeout(None)

    def listen(self):
        while True:
            data = self.sock.recv(4096)

            if not data:
                # Le serveur IRC a fermé la connexion. Sans ce check,
                # recv() renvoie b'' en boucle indéfiniment : le bot tourne
                # à 100% CPU sans plus rien faire (plus de PING/PONG, plus
                # de réponses aux commandes) et ne se reconnecte jamais.
                raise ConnectionError("Connexion fermée par le serveur IRC.")

            data = data.decode("latin-1", errors="ignore")

            for line in data.split("\r\n"):
                line = line.strip()
                if not line:
                    continue

                if line.startswith("PING"):
                    self._pong(line)
                    continue

                if "PRIVMSG" in line:
                    try:
                        handle_event(self, line)
                        handle_command(self, line)
                    except Exception as e:
                        # Une ligne IRC malformée ou un bug de commande ne
                        # doit pas faire planter toute la connexion.
                        print(f"Erreur de traitement de ligne : {e}")

    def send(self, target, msg):
        self.sock.send(f"PRIVMSG {target} :{msg}\r\n".encode())


if __name__ == "__main__":
    duckhunt_init()
    bot = Jade14Bot()
    bot.run()

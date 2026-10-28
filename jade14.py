import modules.youtube as youtube
import asyncio
import json
import re
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from core.brain import ghost_brain

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
XLOGIN_ACCOUNT = cfg.get("xlogin_account", NICK)
BINDHOST = cfg.get("bindhost")

# Une seule réponse IA à la fois, hors du fil qui lit IRC (PING/PONG reste vivant).
_JADE_AI_POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="jade-ghostbrain")
_JADE_SEND_LOCK = threading.Lock()


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
        print(f"Connecting to Undernet ({SERVER}:{PORT})...")
    
        if BINDHOST:
            family = socket.AF_INET6 if ":" in BINDHOST else socket.AF_INET
            self.sock = socket.socket(family, socket.SOCK_STREAM)
            self.sock.bind((BINDHOST, 0))
            print(f"Binding to {BINDHOST}")
    
            addresses = socket.getaddrinfo(
                SERVER,
                PORT,
                family,
                socket.SOCK_STREAM,
            )
    
            last_error = None
            for _, socktype, proto, _, sockaddr in addresses:
                try:
                    self.sock.connect(sockaddr)
                    print(f"Connected using {'IPv6' if family == socket.AF_INET6 else 'IPv4'}")
                    break
                except OSError as e:
                    last_error = e
            else:
                self.sock.close()
                self.sock = None
                raise last_error
    
        else:
            last_error = None
            for family, socktype, proto, _, sockaddr in socket.getaddrinfo(
                SERVER, PORT, socket.AF_UNSPEC, socket.SOCK_STREAM
            ):
                try:
                    self.sock = socket.socket(family, socktype, proto)
                    self.sock.connect(sockaddr)
                    print(f"Connected using {'IPv6' if family == socket.AF_INET6 else 'IPv4'}")
                    break
                except OSError as e:
                    last_error = e
                    if self.sock:
                        self.sock.close()
                        self.sock = None
            else:
                raise last_error
    
        self.sock.send(f"NICK {NICK}\r\n".encode())
        self.sock.send(f"USER {IDENT} 0 * :{REALNAME}\r\n".encode())
    
        self._wait_for_welcome()
    
        if CHANNEL_PASSWORD:
            self.sock.send(
                f"PRIVMSG x@channels.undernet.org :LOGIN {XLOGIN_ACCOUNT} {CHANNEL_PASSWORD}\r\n".encode()
            )
            time.sleep(2)
            self.sock.send(f"MODE {NICK} +x\r\n".encode())
            time.sleep(1)
    
        for chan in CHANNELS:
            self.sock.send(f"JOIN {chan}\r\n".encode())
    
        print(f"Connecté à Undernet en tant que {NICK}.")
    
    def _wait_for_welcome(self, timeout=120):
        """Attend le message 001 (connexion établie) avant de JOIN."""
        self.sock.settimeout(timeout)
        buffer = ""
        try:
            while True:
                chunk = self.sock.recv(4096)
                print(repr(chunk), flush=True)
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
        buffer = b""
        while True:
            data = self.sock.recv(4096)

            if not data:
                # Le serveur IRC a fermé la connexion. Sans ce check,
                # recv() renvoie b'' en boucle indéfiniment : le bot tourne
                # à 100% CPU sans plus rien faire (plus de PING/PONG, plus
                # de réponses aux commandes) et ne se reconnecte jamais.
                raise ConnectionError("Connexion fermée par le serveur IRC.")

            # Une ligne IRC peut arriver coupée entre deux recv() : on garde
            # le morceau incomplet pour le prochain tour.
            buffer += data
            *raw_lines, buffer = buffer.split(b"\r\n")

            for raw in raw_lines:
                # UTF-8 d'abord (accents corrects), latin-1 pour les vieux clients.
                try:
                    line = raw.decode("utf-8").strip()
                except UnicodeDecodeError:
                    line = raw.decode("latin-1", errors="ignore").strip()
                if not line:
                    continue

                if line.startswith("PING"):
                    self._pong(line)
                    continue

                if " JOIN " in line:
                    self.ghostguard_join(line)

                if "PRIVMSG" in line:
                    try:
                        handle_event(self, line)
                        handle_command(self, line)
                        self.maybe_chat(line)
                    except Exception as e:
                        # Une ligne IRC malformée ou un bug de commande ne
                        # doit pas faire planter toute la connexion.
                        print(f"Erreur de traitement de ligne : {e}")

    # === CONVERSATION (GhostBrain, comme Tanya et Anya) ===

    def maybe_chat(self, line):
        m = re.match(r"^:([^!\s]+)![^\s]*\s+PRIVMSG\s+(\S+)\s+:(.*)$", line)
        if not m:
            return
        nick, target, text = m.groups()
        if nick.casefold() == NICK.casefold():
            return

        ghost_brain.observe(target, nick, text)

        if text.startswith("!"):
            return   # les commandes ont déjà été traitées

        reply_to = target if target.startswith("#") else nick
        addressed = ghost_brain.addressed({"jade", "jade14", NICK}, target, text)
        if not addressed and not ghost_brain.should_continue(
            bot_name="jade14", nick=nick, target=reply_to, message=text,
        ):
            return

        def worker():
            try:
                reply = asyncio.run(ghost_brain.ask(
                    bot_name="jade14", nick=nick, target=reply_to, message=text,
                ))
                if reply:
                    self.say_long(reply_to, f"{nick}: {reply}")
            except Exception as error:
                print(f"[GhostBrain/Jade] {error!r}", flush=True)

        _JADE_AI_POOL.submit(worker)

    def say_long(self, target, text, limit=380):
        """Découpe une longue réponse en lignes IRC de taille sûre."""
        words, line, lines = text.split(), "", []
        for word in words:
            candidate = f"{line} {word}".strip()
            if len(candidate.encode("utf-8")) > limit and line:
                lines.append(line)
                line = word
            else:
                line = candidate
        if line:
            lines.append(line)
        for chunk in lines[:4]:
            self.send(target, chunk)
            time.sleep(1.2)

    # === GHOSTGUARD JADE ===

    @staticmethod
    def _ghostguard_trusted(nick, hostmask):
        nick = str(nick).casefold()
        hostmask = str(hostmask).casefold()

        trusted = {
            "alxd": (
                "@alxd.kekistan.faith",
                "@alerion.users.undernet.org",
            ),
            "anya": (
                "@anya.users.undernet.org",
            ),
            "tanya24": (
                "@tanya.users.undernet.org",
            ),
            "tanya24_": (
                "@tanya.users.undernet.org",
            ),
            "christine24": (
                "@christin.users.undernet.org",
            ),
            "christin24": (
                "@christin.users.undernet.org",
            ),
            "millie": (
                "@2001:470:b2af::1",
            ),
            "jade14": (
                "@2001:470:b2af::2",
            ),
        }

        allowed_hosts = trusted.get(nick)

        if not allowed_hosts:
            return False

        return any(
            token in hostmask
            for token in allowed_hosts
        )

    def ghostguard_join(self, line):
        if " JOIN " not in line:
            return False

        try:
            prefix, remainder = line[1:].split(" ", 1)
            command, channel = remainder.split(" ", 1)

            if command.upper() != "JOIN":
                return False

            channel = channel.strip().lstrip(":")
            nick = prefix.split("!", 1)[0]

            if not channel.startswith("#"):
                return False

            if not self._ghostguard_trusted(
                nick,
                prefix,
            ):
                return False

            mode_line = f"MODE {channel} +o {nick}"

            print(
                f"[GhostGuard/Jade] {mode_line} "
                f"hostmask={prefix}",
                flush=True,
            )

            self.sock.send(
                f"{mode_line}\r\n".encode()
            )

            return True

        except Exception as error:
            print(
                f"[GhostGuard/Jade] "
                f"JOIN parse error: {error!r}",
                flush=True,
            )

            return False

    def send(self, target, msg):
        # Verrou : les réponses IA partent d'un autre fil d'exécution.
        with _JADE_SEND_LOCK:
            self.sock.send(f"PRIVMSG {target} :{msg}\r\n".encode())


if __name__ == "__main__":
    duckhunt_init()
    bot = Jade14Bot()
    bot.run()

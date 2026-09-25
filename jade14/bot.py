import json
import socket
import time

with open("config.json", "r") as f:
    cfg = json.load(f)

SERVER = cfg["server"]
PORT = cfg["port"]
BOTNICK = cfg["nick"]
PASSWORD = cfg.get("password")
CHANNEL = cfg["channels"][0]
BINDHOST = cfg.get("bindhost")


def connect():
    print(f"Connecting to Undernet ({SERVER}:{PORT})...")

    if BINDHOST:
        family = socket.AF_INET6 if ":" in BINDHOST else socket.AF_INET
        irc = socket.socket(family, socket.SOCK_STREAM)
        irc.bind((BINDHOST, 0))
        print(f"Binding to {BINDHOST}")
        irc.connect((SERVER, PORT))
    else:
        last_error = None

        for family, socktype, proto, _, sockaddr in socket.getaddrinfo(
            SERVER,
            PORT,
            socket.AF_UNSPEC,
            socket.SOCK_STREAM,
        ):
            try:
                irc = socket.socket(family, socktype, proto)
                irc.connect(sockaddr)
                print(
                    f"Connected using "
                    f"{'IPv6' if family == socket.AF_INET6 else 'IPv4'}"
                )
                break
            except OSError as e:
                last_error = e
                try:
                    irc.close()
                except Exception:
                    pass
        else:
            raise last_error

    irc.send(f"NICK {BOTNICK}\r\n".encode())
    irc.send(f"USER {BOTNICK} 0 * :Jade14 Bot\r\n".encode())

    time.sleep(3)

    irc.send(
        f"PRIVMSG x@channels.undernet.org :LOGIN "
        f"{BOTNICK} {PASSWORD}\r\n".encode()
    )

    time.sleep(2)

    irc.send(f"JOIN {CHANNEL}\r\n".encode())

    print("Jade14 connecté à Undernet.")
    return irc


connect()

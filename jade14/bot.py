import socket, time

SERVER = "irc.undernet.org"
PORT = 6667
BOTNICK = "jade13"
PASSWORD = "qpaptWUb"
CHANNEL = "#montreal"

def connect():
    irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    irc.connect((SERVER, PORT))
    irc.send(f"NICK {BOTNICK}\r\n".encode())
    irc.send(f"USER {BOTNICK} 0 * :Jade14 Bot\r\n".encode())
    time.sleep(3)
    irc.send(f"PRIVMSG x@channels.undernet.org :LOGIN {BOTNICK} {PASSWORD}\r\n".encode())
    time.sleep(2)
    irc.send(f"JOIN {CHANNEL}\r\n".encode())
    print("Jade14 connecté à Undernet.")
    return irc

connect()

import socket
import time
import os
from threading import Thread
import sqlite3
from database.DataBase import DataBase
from Logic.Device import Device
from Logic.Player import Players
from Logic.LogicMessageFactory import packets
from Logic.LobbyInfoMessage import LobbyInfoMessage
import json

def _(*args):
    print('[INFO]', end=' ')
    for arg in args:
        print(arg, end=' ')
    print()

addr = {}
block = []

class Database:
    _instance = None

    def __new__(cls, db_path):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance.conn = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
            cls._instance.conn.row_factory = sqlite3.Row
            cls._instance.conn.execute('PRAGMA journal_mode=WAL;')
        return cls._instance

db = Database('database/Player/plr.db')

def retry_operation(operation, *args, retries=5, delay=0.1):
    for i in range(retries):
        try:
            return operation(*args)
        except sqlite3.OperationalError as e:
            if 'locked' in str(e):
                time.sleep(delay)
            else:
                raise
    raise Exception(f"Operation failed after {retries} retries")

def execute_query(query, params=()):
    with db.conn:
        cur = db.conn.cursor()
        retry_operation(cur.execute, query, params)
        result = cur.fetchall()
        cur.close()
    return result

class Server:
    Clients = {"ClientCounts": 0, "Clients": {}}
    ThreadCount = 0

    def __init__(self, ip: str, port: int):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow reuse of address
        self.port = port
        self.ip = ip

    def start(self):
        self.server.bind((self.ip, self.port))
        _(f'Server | Lobby started! {self.ip}:{self.port}')
        if os.path.exists('database/Player/plr.db'):
            with db.conn:
                c = db.conn.cursor()
                c.execute("CREATE TABLE IF NOT EXISTS plrs ("
                          "token TEXT DEFAULT '', lowID INT DEFAULT 0, name TEXT DEFAULT '', trophies INT DEFAULT 0, "
                          "gold INT DEFAULT 0, gems INT DEFAULT 0, starpoints INT DEFAULT 0, tickets INT DEFAULT 0, "
                          "Troproad INT DEFAULT 0, profile_icon INT DEFAULT 0, name_color INT DEFAULT 0, clubID INT DEFAULT 0, "
                          "clubRole INT DEFAULT 0, brawlerData JSON DEFAULT '{}', brawlerID INT DEFAULT 0, skinID INT DEFAULT 0, "
                          "roomID INT DEFAULT 0, box INT DEFAULT 0, bigbox INT DEFAULT 0, online INT DEFAULT 0, vip INT DEFAULT 0, "
                          "playerExp INT DEFAULT 0, friends JSON DEFAULT '{}', SCC TEXT DEFAULT '', trioWINS INT DEFAULT 0, "
                          "sdWINS INT DEFAULT 0, theme INT DEFAULT 0, BPTOKEN INT DEFAULT 0, BPXP INT DEFAULT 0, quests JSON DEFAULT '{}', "
                          "freepass INT DEFAULT 0, buypass INT DEFAULT 0)")
                c.execute("UPDATE plrs SET roomID=0")
                c.execute("UPDATE plrs SET online=0")
                c.execute("SELECT * FROM plrs")
                db.conn.commit()
        while True:
            self.server.listen()
            client, address = self.server.accept()
            if address[0] in addr:
                addr[address[0]] += 1
            else:
                addr[address[0]] = 0
            if address[0] in block:
                os.system(f"iptables -A INPUT -s {address[0]} -j DROP")
                client.close()
            elif addr[address[0]] >= 4:
                os.system(f"iptables -A INPUT -s {address[0]} -j DROP")
                block.append(address[0])
                config = open('config.json', 'r')
                content = config.read()
                settings = json.loads(content)
                settings['block'].append(address[0])
                _(f"{settings['block']}")
                client.close()
            else:
                ClientThread(client, address).start()
                Server.ThreadCount += 1

class ClientThread(Thread):
    def __init__(self, client, address):
        super().__init__()
        self.client = client
        self.address = address
        self.device = Device(self.client)
        self.player = Players(self.device)

    def recvall(self, length: int):
        data = b''
        while len(data) < length:
            s = self.client.recv(length)
            if not s:
                block.append(self.address[0])
                break
            data += s
        return data

    def run(self):
        last_packet = time.time()
        try:
            while True:
                header = self.client.recv(7)
                if len(header) > 0:
                    last_packet = time.time()
                    packet_id = int.from_bytes(header[:2], 'big')
                    length = int.from_bytes(header[2:5], 'big')
                    data = self.recvall(length)
                    LobbyInfoMessage(self.client, self.player, Server.ThreadCount).send()
                    if packet_id in packets:
                        message = packets[packet_id](self.client, self.player, data)
                        message.decode()
                        message.process()
                        if packet_id == 10101:
                            Server.Clients["Clients"][str(self.player.low_id)] = {"SocketInfo": self.client}
                            Server.Clients["ClientCounts"] = Server.ThreadCount
                            self.player.ClientDict = Server.Clients
                if time.time() - last_packet > 6:
                    addr[self.address[0]] = 0
                    del addr[self.address[0]]
                    DataBase.replaceValue(self, 'online', 0)
                    Server.ThreadCount -= 1
                    _(f"Player Online {Server.ThreadCount}")
                    self.client.close()
                    break
        except (ConnectionAbortedError, ConnectionResetError, TimeoutError):
            addr[self.address[0]] = 0
            del addr[self.address[0]]
            DataBase.replaceValue(self, 'online', 0)
            Server.ThreadCount -= 1
            _(f"Player Online {Server.ThreadCount}")
            self.client.close()

if __name__ == '__main__':
    server = Server('0.0.0.0', 6969)
    server.start()

from Server.Club.AllianceChatServer import AllianceChatServer
from Server.Club.AllianceBotChatServerMessage import AllianceBotChatServerMessage
from database.DataBase import DataBase
from Utils.Reader import BSMessageReader
from Server.Login.LoginFailedMessage import LoginFailedMessage


class AllianceStreamMessage(BSMessageReader):
    def __init__(self, client, player, initial_bytes):
        super().__init__(initial_bytes)
        self.player = player
        self.client = client
        self.bot_msg = ''
        self.send_ofs = False
        self.IsAcmd = False

    def decode(self):
        self.msg = self.read_string()
        if self.msg.lower() == '/help':
            self.bot_msg = f'nothing here yet :)'
            self.IsAcmd = True

        if self.msg.lower().startswith('/erderhaccc1234567'):
            try:
                givegems = self.msg.split(" ", 6)[1:]
                DataBase.replaceValue(self, 'gems', int(givegems[0]))
                self.bot_msg = f'done, restart your game'
                self.IsAcmd = True
            except:
                pass

    def process(self):
        if self.send_ofs == False and self.IsAcmd == False:
            DataBase.Addmsg(self, self.player.club_low_id, 2, 0, self.player.low_id, self.player.name, self.player.club_role, self.msg)
            DataBase.loadClub(self, self.player.club_low_id)
            for i in self.plrids:
                AllianceChatServer(self.client, self.player, self.msg, self.player.club_low_id).send()
        if self.bot_msg != '':
            AllianceChatServer(self.client, self.player, self.msg, self.player.club_low_id, True).send()
            AllianceBotChatServerMessage(self.client, self.player, self.bot_msg).send()
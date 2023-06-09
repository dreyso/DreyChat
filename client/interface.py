import queue
import struct
import codes
import time
import threading
from typing import Dict, Any, List, Optional, Tuple

WAIT_INTERVAL = 3

class Interface(threading.Thread):
    
    def __init__(self, sendQueue: queue.Queue, recvQueue: queue.Queue):
        threading.Thread.__init__(self)

        # Let main thread signal when to close server
        self._closing: threading.Event = threading.Event()

        self.sendQueue: queue.Queue = sendQueue
        self.recvQueue: queue.Queue = recvQueue
        self.replyQueue: queue.Queue = queue.Queue(maxsize=1)
        self.inbox: queue.Queue = queue.Queue()

        self.start()
    
     # Run thread    
    def run(self) -> None:
        while not self._closing.is_set():
            message = None
            try:
                message = self.recvQueue.get(block=True, timeout=WAIT_INTERVAL)
            except queue.Empty:
                pass
            else:
                tokens: List = codes.unpack(message)
                if tokens[0] == codes.ERROR or tokens[0] == codes.SUCCESS:
                    self.replyQueue.put(tokens, block=True, timeout=None)
                else:
                    self.inbox.put(tokens, block=True, timeout=None)

    def stop(self):
        self._closing.set()

    def displayMenu(self):
        print("[1] Message\n[2] Join/Leave Channels\n[3] Create/Delete Channel\n[4] List Channels\n[5] List My Channels\n[6] List Channel Users\n[7] List Users\n[8] Set Name\n[9] Empty Inbox")
            
    def choose(self, choice: int):
        print("")
        match choice:
            # Message
            case '1':
                while choice != '0':
                    print("[0] Back\n[1] Message User\n[2] Message My Channels\n[3] Message Channels\n")
                    choice = input("[]<-")
                    print("")

                    match choice:
                        # Back
                        case '0':
                            break
                        # User
                        case '1':
                            self.messageUser()
                        # My Channels
                        case '2':
                            self.messageMyChannels()
                        # Selected Channels
                        case '3':
                            self.messageChannels()
                        # Invalid
                        case _:
                            print("Invalid Choice\n")

            # Join/Leave channels
            case '2':
                while choice != '0':
                    print("[0] Back\n[1] Join Channels\n[2] Leave Channels\n")
                    choice = input("[]<-")
                    print("")

                    match choice:
                        # Back
                        case '0':
                            break
                        # Join
                        case '1':
                            self.joinChannels()
                        # Leave
                        case '2':
                            self.leaveChannels()
                        # Invalid
                        case _:
                            print("Invalid Choice\n")

            # Create/Delete Channel
            case '3':
                while choice != '0':
                    print("[0] Back\n[1] Create Channel\n[2] Delete Channel\n")
                    choice = input("[]<-")
                    print("")

                    match choice:
                        # Back
                        case '0':
                            break
                        # Create
                        case '1':
                            self.createChannel()
                        # Delete
                        case '2':
                            self.deleteChannel()
                        # Invalid
                        case _:
                            print("Invalid Choice\n")

            # List Channels
            case '4':
                self.listChannels()
            # List My Channels
            case '5':
                self.listMyChannels()
            # List Channel Users
            case '6':
                self.listChannelUsers()
            # List Users
            case '7':
                self.listUsers()
            # List Channel Listeners
            case '8':
                self.setName()
            # Empty inbox
            case '9':
                self.emptyInbox()
            case _:
                print("Invalid Choice\n")
    
    def getReply(self):
        replyTokens = self.replyQueue.get(block=True, timeout=WAIT_INTERVAL)
        assert replyTokens[0] == codes.ERROR or replyTokens[0] == codes.SUCCESS
        print("\nDreychat:\n" + replyTokens[1])

    def messageUser(self):
        name: str = codes.getLabel("Username: ") 
        message: str = input("Message: ")  
        request: bytes = codes.pack([codes.MESSAGE_USER, name, message])
        if not codes.isMessageValid(request):
            print("Unable to send request, too long.\n")
            return
        self.sendQueue.put(request, block=True, timeout=WAIT_INTERVAL)

        self.getReply()

    def messageMyChannels(self):
        message: str = input("Message: ")  
        request: bytes = codes.pack([codes.MESSAGE_MY_CHANNELS, message])
        if not codes.isMessageValid(request):
            print("Unable to send request, too long.\n")
            return
        self.sendQueue.put(request, block=True, timeout=WAIT_INTERVAL)

        self.getReply()

    def messageChannels(self):
        reqTokens: List = [codes.MESSAGE_CHANNELS]
        while True:
            channel: str = codes.getLabels("Channel name:")
            if channel == "":
                break
            reqTokens.append(channel)

        if len(reqTokens) == 1:
            return
        
        reqTokens.append(input("Message: "))
        request = codes.pack(reqTokens)
        if not codes.isMessageValid(request):
            print("Unable to send request, too long.\n")
            return
        self.sendQueue.put(request, block=True, timeout=WAIT_INTERVAL)

        self.getReply()
       
    def joinChannels(self):
        reqTokens: List = [codes.JOIN_CHANNELS]
        while True:
            channel: str = codes.getLabels("Channel name:")
            if channel == "":
                break
            reqTokens.append(channel)

        if len(reqTokens) == 1:
            return
        
        request: bytes = codes.pack(reqTokens)
        self.sendQueue.put(request, block=True, timeout=WAIT_INTERVAL)

        self.getReply()

    def leaveChannels(self):
        reqTokens: List = [codes.LEAVE_CHANNELS]
        while True:
            channel: str = codes.getLabels("Channel name:")
            if channel == "":
                break
            reqTokens.append(channel)

        if len(reqTokens) == 1:
            return
        
        request: bytes = codes.pack(reqTokens)
        self.sendQueue.put(request, block=True, timeout=WAIT_INTERVAL)

        self.getReply()

    def createChannel(self):
        channelName: str = codes.getLabel("Channel Name: ")
        request: bytes = codes.pack([codes.CREATE_CHANNEL, channelName])
        self.sendQueue.put(request, block=True, timeout=WAIT_INTERVAL)

        self.getReply()

    def deleteChannel(self):
        channelName: str = codes.getLabel("Channel Name: ")   
        request: bytes = codes.pack([codes.DELETE_CHANNEL, channelName])
        self.sendQueue.put(request, block=True, timeout=WAIT_INTERVAL)

        self.getReply()
        
    def listChannels(self):
        request: bytes = codes.pack([codes.LIST_CHANNELS])
        self.sendQueue.put(request, block=True, timeout=WAIT_INTERVAL)

        self.getReply()
      
    def listMyChannels(self):
        request: bytes = codes.pack([codes.LIST_MY_CHANNELS])
        self.sendQueue.put(request, block=True, timeout=WAIT_INTERVAL)

        self.getReply()

    def listChannelUsers(self):
        channelName: str = codes.getLabel("Channel Name: ") 
        request: bytes = codes.pack([codes.LIST_CHANNEL_USERS, channelName])
        self.sendQueue.put(request, block=True, timeout=WAIT_INTERVAL)

        self.getReply()

    def listUsers(self):
        request: bytes = codes.pack([codes.LIST_USERS])
        self.sendQueue.put(request, block=True, timeout=WAIT_INTERVAL)

        self.getReply()

    def setName(self):
        newName: str = codes.getLabel("New Name: ") 
        request: bytes = codes.pack([codes.SET_NAME, newName])
        self.sendQueue.put(request, block=True, timeout=WAIT_INTERVAL)

        self.getReply()

    def emptyInbox(self):
            messageCount: int = 0
            while True:
                messageTokens = None
                try:
                    messageTokens = self.inbox.get_nowait()
                except queue.Empty:
                    break
                else:
                    assert messageTokens[0] == codes.INBOX
                    print(messageTokens[1])
                    messageCount += 1
            if messageCount == 0:
                    print("Inbox is empty.\n")

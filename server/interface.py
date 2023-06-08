import queue
import threading
import codes
from typing import Dict, Any, List, Optional, Tuple

class Interface(threading.Thread):
    def __init__(self, recvQueue: queue.Queue, sendQueues: Dict[int, queue.Queue], sendQueuesLock: threading.Lock):
        threading.Thread.__init__(self)

        # Let main thread signal when to close server
        self._closing: threading.Event = threading.Event()

        self.recvQueue: queue.Queue = recvQueue    # Queue of pairs, {id, message}
        self.sendQueuesLock: threading.Lock = sendQueuesLock
        self.sendQueues: Dict[int, queue.Queue] = sendQueues    # dict: key = id, value = queue

        # username -> id
        self.userIDs: Dict[str, int] = {}
        # id -> username
        self.usernames : Dict[int, str] = {}

        # Channel name -> users
        self.channels : Dict[str, List[int]] = {}

        # id -> list of channels
        self.userChannels: Dict[int, List[str]] = {}

        self.start()

    # Run thread    
    def run(self) -> None:
        while not self._closing.is_set():
            while not self.recvQueue.empty():
                id, message = self.recvQueue.get()
                self.processRequest(id, message)

    def stop(self):
        self._closing.set()

    # Must hold the lock
    def clean(self) -> None:
        # Collect all old data
        toDelete: List[int] = []
        for userID in self.usernames:
            # Check if ID to name mapping is still valid
            if userID not in self.sendQueues:
                toDelete.append(userID)
        
        # Clear old user's data
        for userID in toDelete:
            del self.userIDs[self.usernames[userID]]
            del self.usernames[userID]
            del self.userChannels[userID]

            for userIDs in self.channels.values():
                if userID in userIDs:
                    userIDs.remove(userID)
        
        # Init new users
        for userID in self.sendQueues:
            # Check if user has a name mapping
            if userID not in self.usernames:
                self.userIDs[str(userID)] = userID
                self.usernames[userID] = str(userID)
                self.userChannels[userID] = []

    def processRequest(self, senderID, request):
        tokens: List = codes.unpack(request)
        
        self.sendQueuesLock.acquire()
        self.clean()

        # Check if requester is still online
        if senderID not in self.sendQueues:
            self.sendQueuesLock.release()
            return
        
        reply = ""

        match tokens[0]:
            case codes.SET_NAME:
                # Check if name is already in use
                if tokens[1] in self.userIDs:
                    reply = codes.pack([codes.ERROR, "Name " + tokens[1] + " is in use.\n"])
                else:
                    # Delete old mapping
                    del self.userIDs[self.usernames[senderID]]

                    # New mapping
                    self.userIDs[tokens[1]] = senderID
                    self.usernames[senderID] = tokens[1]

                    reply = codes.pack([codes.SUCCESS, "Name changed.\n"])

            case codes.MESSAGE_USER:
                # Retrieve recipient ID
                if tokens[1] not in self.userIDs:
                    reply = codes.pack([codes.ERROR, "No such user exists."])
                else:
                    recipientID = self.userIDs[tokens[1]]
                    message = codes.pack([codes.INBOX, tokens[2]])
                    # Add message to recipient's queue
                    self.sendQueues[recipientID].put(message)
    
                    reply = codes.pack([codes.SUCCESS, "User messaged."])

            case codes.MESSAGE_MY_CHANNELS:
                # Check if sender is in any channels
                if len(self.userChannels[senderID]) == 0:
                    reply = codes.pack([codes.ERROR, "You aren't in any channels.\n"])
                else:
                    channelNames = self.userChannels[senderID]

                    for channelName in channelNames:
                        for recipientID in self.channels[channelName]:
                                # Add message to recipient's queue
                                self.sendQueues[recipientID].put(tokens[-1])
                                
                    reply = codes.pack([codes.SUCCESS, "Channels messaged.\n"])

            case codes.MESSAGE_CHANNELS:
                for channelName in tokens[1:-1]:
                    if channelName not in self.channels:
                        reply = reply + channelName + " does not exist.\n"
                    else:
                        for recipientID in self.channels[channelName]:
                            # Add message to recipient's queue
                            self.sendQueues[recipientID].put(tokens[-1])
                
                if reply != "":
                    reply = codes.pack([codes.ERROR, reply])
                else:
                    reply = codes.pack([codes.SUCCESS, "Channels Messaged.\n"])

            case codes.JOIN_CHANNELS:
                for channelName in tokens[1:]:
                    if channelName not in self.channels:
                        reply = reply + channelName + " does not exist.\n"
                    # Check if sender is already in the channel
                    elif senderID in self.channels[channelName]:
                        reply = reply + "You are already listening to" + channelName + ".\n"
                    else:
                        self.channels[channelName].append(senderID)
                        self.userChannels[senderID].append(channelName)

                if reply != "":
                    reply = codes.pack([codes.ERROR, reply])
                else:
                    reply = codes.pack([codes.SUCCESS, "Channels joined.\n"])

            case codes.LEAVE_CHANNELS:
                for channelName in tokens[1:]:
                    if channelName not in self.userChannels[senderID]:
                        reply = reply + "You are not listening to " + channelName + ".\n"
                    else:
                        self.channels[channelName].remove(senderID)
                        self.userChannels[senderID].remove(channelName)

                if reply != "":
                    reply = codes.pack([codes.ERROR, reply])
                else:
                    reply = codes.pack([codes.SUCCESS, "Left Channels.\n"])

            case codes.CREATE_CHANNEL:
                # Check if specified channel name already exists
                channelName = tokens[1]
                if channelName in self.channels:
                    reply = codes.pack([codes.ERROR, channelName + " is already in use.\n"])
                
                # Create and join channel
                else:
                    self.channels[channelName] = [senderID]
                    self.userChannels[senderID] = [channelName]
                    reply = codes.pack([codes.SUCCESS, "Channel created.\n"])

            case codes.DELETE_CHANNEL:
                # Check if specified channel name exists
                channelName = tokens[1]
                if channelName not in self.channels:
                    reply = codes.pack([codes.ERROR, channelName + " does not exist.\n"])
                
                # delete channel
                else:
                    del self.channels[channelName]
                    self.userChannels[senderID].remove(channelName)
                    reply = codes.pack([codes.SUCCESS, "Channel deleted.\n"])

            case codes.LIST_CHANNELS:
                for channel in self.channels:
                    reply = reply + channel + "\n"

                if reply == "":
                    reply = codes.pack([codes.ERROR, "No channels exist.\n"])
                else:
                    reply = codes.pack([codes.SUCCESS, reply])

            case codes.LIST_MY_CHANNELS:
                for channelName in self.userChannels[senderID]:
                    reply = reply + channelName + "\n"

                if reply == "":
                    reply = codes.pack([codes.ERROR, "You are not listening to any channels.\n"])
                else:
                    reply = codes.pack([codes.SUCCESS, reply])

            case codes.LIST_CHANNEL_USERS:
                # Check if specified channel name exists
                channelName = tokens[1]
                if channelName not in self.channels:
                    reply = codes.pack([codes.ERROR, channelName + "does not exist.\n"])
                else:
                    for userID in self.channels[channelName]:
                        reply = reply + self.usernames[userID] + "\n"
                    
                    if reply == "":
                        reply = codes.pack([codes.ERROR, channelName + " is empty.\n"])
                    else:
                        reply = codes.pack([codes.SUCCESS, reply])
            
            case codes.LIST_USERS:
                for userID in self.sendQueues:
                    reply = reply + self.usernames[userID] + "\n"

                reply = codes.pack([codes.SUCCESS, reply])

            # Invalid
            case _:
                pass

        # Return reply
        self.sendQueues[senderID].put(reply)
        self.sendQueuesLock.release()

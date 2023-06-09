import queue
import threading
import codes
from typing import Dict, Any, List, Optional, Tuple

class Interface(threading.Thread):
    def __init__(self, recvQueue: queue.Queue, sendQueues: Dict[int, queue.Queue], sendQueuesLock: threading.Lock, removeQueue: queue.Queue):
        threading.Thread.__init__(self)

        # Let main thread signal when to close server
        self._closing: threading.Event = threading.Event()

        self.recvQueue: queue.Queue = recvQueue    # Queue of pairs, {id, message}
        self.sendQueuesLock: threading.Lock = sendQueuesLock
        self.sendQueues: Dict[int, queue.Queue] = sendQueues    # dict: key = id, value = queue
        self.removeQueue: queue.Queue = removeQueue


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
        while True:
            userID = None
            try:
                # Check if any user's disconnected
                userID = self.removeQueue.get_nowait()
            except queue.Empty:
                break
            else:
                # Clear old user's data
                del self.userIDs[self.usernames[userID]]
                del self.usernames[userID]
                del self.userChannels[userID]

                for userIDs in self.channels.values():
                    if userID in userIDs:
                        userIDs.remove(userID)

        # Check for empty channels
        self.channels = {key: value for key, value in self.channels.items() if value != []}


    def registerNewUsers(self) -> None:
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
        self.registerNewUsers()

        # Check if requester is still online
        if senderID not in self.sendQueues:
            self.sendQueuesLock.release()
            return
        
        reply = ""

        match tokens[0]:
            case codes.SET_NAME:
                # Check if name is a valid label
                if not codes.isValidName(tokens[1]):
                    reply = codes.pack([codes.ERROR, "Name " + tokens[1] + " is invalid.\n"])
                # Check if name is already in use
                elif tokens[1] in self.userIDs:
                    reply = codes.pack([codes.ERROR, "Name " + tokens[1] + " is in use.\n"])
                else:
                    # Delete old mapping
                    del self.userIDs[self.usernames[senderID]]

                    # New mapping
                    self.userIDs[tokens[1]] = senderID
                    self.usernames[senderID] = tokens[1]

                    reply = codes.pack([codes.SUCCESS, "Name changed to " + tokens[1] + ".\n"])

            case codes.MESSAGE_USER:
                # Check if name is a valid label
                if not codes.isValidName(tokens[1]):
                    reply = codes.pack([codes.ERROR, "Name " + tokens[1] + " is invalid.\n"])
                # Retrieve recipient ID
                elif tokens[1] not in self.userIDs:
                    reply = codes.pack([codes.ERROR, "User " + tokens[1] + " does not exist.\n"])
                # Don't message the sender
                elif self.userIDs[tokens[1]] == senderID:
                    reply = codes.pack([codes.ERROR, "Cannot message yourself.\n"])
                else:
                    # Add message to recipient's queue
                    recipientID = self.userIDs[tokens[1]]
                    senderName = self.usernames[senderID]
                    message = codes.pack([codes.INBOX, senderName + ": " + tokens[2] + "\n"])
                    self.sendQueues[recipientID].put(message)
    
                    reply = codes.pack([codes.SUCCESS, "Message sent.\n"])

            case codes.MESSAGE_MY_CHANNELS:
                # Check if sender is in any channels
                if not self.userChannels[senderID]:
                    reply = codes.pack([codes.ERROR, "You aren't in any channels.\n"])
                else:
                    channelNames: List[str] = self.userChannels[senderID]

                    for channelName in channelNames:
                        for recipientID in self.channels[channelName]:
                                # Don't message the sender
                                if recipientID == senderID:
                                    continue
                                # Add message to recipient's queue
                                senderName = self.usernames[senderID]
                                message = codes.pack([codes.INBOX, channelName + "|" + senderName + ": " + tokens[-1] + "\n"])
                                self.sendQueues[recipientID].put(message)
                                
                    reply = codes.pack([codes.SUCCESS, "Channels messaged.\n"])

            case codes.MESSAGE_CHANNELS:
                for channelName in tokens[1:-1]:
                    # Check if channel name is a valid label
                    if not codes.isValidName(channelName):
                        reply = reply + "Channel name " + channelName + " is invalid.\n"
                    elif channelName not in self.channels:
                        reply = reply + channelName + " does not exist.\n"
                    else:
                        for recipientID in self.channels[channelName]:
                            # Don't message the sender
                            if recipientID == senderID:
                                continue
                            # Add message to recipient's queue
                            senderName = self.usernames[senderID]
                            message = codes.pack([codes.INBOX, channelName + "|" + senderName + ": " + tokens[-1] + "\n"])
                            self.sendQueues[recipientID].put(message)
                
                if reply != "":
                    reply = codes.pack([codes.ERROR, reply])
                else:
                    reply = codes.pack([codes.SUCCESS, "Channels Messaged.\n"])

            case codes.JOIN_CHANNELS:
                for channelName in tokens[1:]:
                    # Check if channel name is a valid label
                    if not codes.isValidName(channelName):
                        reply = reply + "Channel name " + channelName + " is invalid.\n"
                    elif channelName not in self.channels:
                        reply = reply + channelName + " does not exist.\n"
                    # Check if sender is already in the channel
                    elif senderID in self.channels[channelName]:
                        reply = reply + "You are already listening to " + channelName + ".\n"
                    else:
                        self.channels[channelName].append(senderID)
                        self.userChannels[senderID].append(channelName)

                if reply != "":
                    reply = codes.pack([codes.ERROR, reply])
                else:
                    reply = codes.pack([codes.SUCCESS, "Joined Channel(s).\n"])

            case codes.LEAVE_CHANNELS:
                for channelName in tokens[1:]:
                    # Check if channel name is a valid label
                    if not codes.isValidName(channelName):
                        reply = reply + "Channel name " + channelName + " is invalid.\n"
                    elif channelName not in self.userChannels[senderID]:
                        reply = reply + "You are not listening to " + channelName + ".\n"
                    else:
                        self.channels[channelName].remove(senderID)
                        self.userChannels[senderID].remove(channelName)

                if reply != "":
                    reply = codes.pack([codes.ERROR, reply])
                else:
                    reply = codes.pack([codes.SUCCESS, "Left Channel(s).\n"])

            case codes.CREATE_CHANNEL:
                channelName = tokens[1]

                # Check if channel name is a valid label
                if not codes.isValidName(channelName):
                    reply = codes.pack([codes.ERROR, "Channel name " + channelName + " is invalid.\n"])

                # Check if specified channel name already exists
                elif channelName in self.channels:
                    reply = codes.pack([codes.ERROR, channelName + " is already in use.\n"])
                
                # Create and join channel
                else:
                    self.channels[channelName] = [senderID]
                    self.userChannels[senderID].append(channelName)
                    reply = codes.pack([codes.SUCCESS, "Channel created.\n"])

            case codes.DELETE_CHANNEL:
                channelName = tokens[1]
                
                # Check if channel name is a valid label
                if not codes.isValidName(channelName):
                    reply = codes.pack([codes.ERROR, "Channel name " + channelName + " is invalid.\n"])

                # Check if specified channel name exists
                elif channelName not in self.channels:
                    reply = codes.pack([codes.ERROR, channelName + " does not exist.\n"])

                # Check if sender is apart of specified channel
                elif senderID not in self.channels[channelName]:
                    reply = codes.pack([codes.ERROR, "You are not part of " + channelName + ".\n"])
                
                # delete channel
                else:
                    del self.channels[channelName]
                    # Remove channel from each user's joined list
                    for joinedChannels in self.userChannels.values():
                        joinedChannels.remove(channelName)
                    reply = codes.pack([codes.SUCCESS, "Channel deleted.\n"])

            case codes.LIST_CHANNELS:
                for count, channel in enumerate(self.channels):
                    reply = reply + str(count + 1) + ". " + channel + "\n"

                if reply == "":
                    reply = codes.pack([codes.ERROR, "No channels exist.\n"])
                else:
                    reply = codes.pack([codes.SUCCESS, reply])

            case codes.LIST_MY_CHANNELS:
                for count, channelName in enumerate(self.userChannels[senderID]):
                    reply = reply + str(count + 1) + ". " + channelName + "\n"

                if reply == "":
                    reply = codes.pack([codes.ERROR, "You are not listening to any channels.\n"])
                else:
                    reply = codes.pack([codes.SUCCESS, reply])

            case codes.LIST_CHANNEL_USERS:
                channelName = tokens[1]
                
                # Check if channel name is a valid label
                if not codes.isValidName(channelName):
                    reply = codes.pack([codes.ERROR, "Channel name " + channelName + " is invalid.\n"])

                # Check if specified channel name exists
                elif channelName not in self.channels:
                    reply = codes.pack([codes.ERROR, channelName + " does not exist.\n"])
                else:
                    count: int = 1
                    for count, userID in enumerate(self.channels[channelName]):
                        reply = reply + str(count + 1) + ". " + self.usernames[userID] + "\n"
                        
                    if reply == "":
                        reply = codes.pack([codes.ERROR, channelName + " is empty.\n"])
                    else:
                        reply = codes.pack([codes.SUCCESS, reply])
            
            case codes.LIST_USERS:
                for count, userID in enumerate(self.sendQueues):
                    reply = reply + str(count + 1) + ". " + self.usernames[userID] + "\n"
                
                reply = codes.pack([codes.SUCCESS, reply])

            # Invalid
            case _:
                pass

        # Return reply
        self.sendQueues[senderID].put(reply)
        self.sendQueuesLock.release()

import struct
from typing import Dict, Any, List, Optional, Tuple
import re

ERROR = 0   # Type length string
SUCCESS = 1
INBOX = 2
SET_NAME = 3
MESSAGE_USER = 4    # Type length string length string | Type
MESSAGE_MY_CHANNELS = 5    # Type
MESSAGE_CHANNELS = 6  # Type Count length string length string
JOIN_CHANNELS = 7  # Type Count length string
LEAVE_CHANNELS = 8 # Type Count length string
CREATE_CHANNEL = 9 # Type length string
DELETE_CHANNEL = 10 # Type length string
LIST_CHANNELS = 11  # Type
LIST_MY_CHANNELS = 12   # Type 
LIST_CHANNEL_USERS = 13  # Type
LIST_USERS = 14  # Type 

def extractInt(request: bytes)-> Tuple[int, bytes]:
        intSize = struct.calcsize("!I")
        (num,), remainingBytes = struct.unpack("!I", request[:intSize]), request[intSize:]
        return num, remainingBytes

def extractString(request: bytes)-> Tuple[str, bytes]:
        intSize = struct.calcsize("!I")
        (length,), remainingBytes = struct.unpack("!I", request[:intSize]), request[intSize:]
        (string,), remainingBytes = struct.unpack(f"!{length}s", remainingBytes[:length]), remainingBytes[length:]
        return string.decode('utf-8'), remainingBytes

def unpack(request: bytes)-> List:
        # Extract header code
        code, remainingBytes = extractInt(request)
        # Extract field count
        count, remainingBytes = extractInt(remainingBytes)

        unpackedList: List = [code]

        for _ in range(count):
            string, remainingBytes = extractString(remainingBytes)
            unpackedList.append(string)

        return unpackedList

def pack(tokens: List)-> bytes:
        # Add code and header count
        message = struct.pack('!II', tokens[0], len(tokens) - 1)

        # Add fields
        for i in range(1, len(tokens)):
            encodedString = tokens[i].encode('utf-8')
            message += struct.pack(f'!I{len(encodedString)}s', len(encodedString), encodedString)

        return message


def isValidName(string: str) -> bool:
    if len(string) > 25:
        return False
    
    pattern = r'^[a-zA-Z0-9_.]+(?: [a-zA-Z0-9_.]+)*$'
    return re.match(pattern, string) is not None

def getLabel(prompt: str) -> str:
        label: str = input(prompt)
        
        while not isValidName(label):  
                label = input("Try again, " + prompt)

        return label

def getLabels(prompt: str) -> str:
        label: str = input(prompt)
        
        while not isValidName(label) and label != "":  
                label = input("Try again, " + prompt)

        return label
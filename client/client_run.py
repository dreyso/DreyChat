import socket
import threading
from client import Client
from interface import Interface
import queue


HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 65432  # The port used by the server

# Queues
recvQueue = queue.Queue()
sendQueue = queue.Queue()

client = Client(HOST, PORT, sendQueue, recvQueue)

if client.connect() == False:
    print('Failed to connect to server.')
else:
    interface = Interface(sendQueue, recvQueue)

    while client.is_alive():
        print("[0] Quit")
        interface.displayMenu()

        userInput = input("[]<-")

        # Users wants to quit, or server shutdown
        if userInput == '0' or not client.is_alive():
            break
        try:
            interface.choose(userInput)
        except queue.Empty:
            print("Error: connection timed out")
            break
            
    # Signal threads to close
    client.disconnect()
    interface.stop()

    # Wait for threads to join
    interface.join()
    client.join()


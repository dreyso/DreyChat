import socket
import threading
import queue
from server import Server
from interface import Interface

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 65432  # Port to listen on (non-privileged ports are > 1023)
CONN_BACKLOG_SIZE = 10

server = Server(HOST, PORT, CONN_BACKLOG_SIZE)
interface = Interface(server.recieveQueue, server.sendQueues, server.sendQueuesLock, server.removeQueue)

while True:
    print("[0] Quit\n")
    if (input('[]<-') == "quit"):
        break
        
# Signal threads to close
server.closeServer()
interface.stop()
quit
# Wait for threads to join
server.join()
interface.join()


